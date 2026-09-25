"""Manual / E2E harness for Quanta (Step 9.1 hardening).

What changed compared with the first hardened version
-----------------------------------------------------
Fix A  Nigerian money parser. ``10 boi`` / ``10 thousand`` / ``10 grand`` /
       ``10k`` / ``puku iri`` / ``dubu goma`` ... are resolved by
       ``parse_amount`` in application code, before any numeric fallback.
       The LLM is never responsible for converting slang into an amount.

Fix B  Authoritative TransferContext. The application owns the beneficiary and
       the amount that reach ``prepare_transfer``. A ``TransferGuard`` sits
       between the LLM provider and the orchestrator and rewrites (or blocks)
       any ``prepare_transfer`` call whose arguments disagree with the context.
       A second, independent check in the harness rejects (fails closed) any
       prepared transfer that does not match the context.

Fix C  Conversation history is no longer a source of truth for transaction
       values. Only the latest explicit value in the current turn, or the
       preserved TransferContext, can supply a beneficiary or amount. The
       context is reset after a confirmation, cancellation or expiry so a
       finished transfer can never leak its amount into the next one.
"""

from __future__ import annotations

import argparse
import asyncio
import dataclasses
import functools
import inspect
import json
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any
from uuid import uuid4

from app.clients.ui_pay.mock import MockUIPayClient
from app.core.config import Settings
from app.core.context import RequestContext
from app.orchestration.orchestrator import Orchestrator
from app.providers.llm.base import (
    LLMMessage,
    LLMMessageRole,
    LLMProvider,
    LLMResponse,
    LLMToolCall,
)
from app.providers.llm.claude import ClaudeProvider
from app.providers.llm.groq import GroqProvider
from app.providers.llm.mock import MockLLMProvider
from app.schemas.response import QuantaResponse, ResponseStatus
from app.tools.executor import ToolExecutor
from app.tools.implementations.beneficiaries.beneficiary import SearchBeneficiaryTool
from app.tools.implementations.transfer import PrepareTransferTool
from app.tools.policy import ToolPolicy
from app.tools.registry import ToolRegistry

# ---------------------------------------------------------------------------
# Demo data
# ---------------------------------------------------------------------------

USER_ID = "user_001"

DEMO_BENEFICIARIES = [
    {
        "id": "ben_001",
        "user_id": USER_ID,
        "nickname": "Mum",
        "account_name": "Amaka Okafor",
        "bank_name": "GTBank",
        "account_number": "0123456789",
    },
    {
        "id": "ben_002",
        "user_id": USER_ID,
        "nickname": "Dad",
        "account_name": "Chinedu Okafor",
        "bank_name": "Access Bank",
        "account_number": "0987654321",
    },
]

# Spoken aliases -> demo nickname. In production this is a UI Pay lookup.
BENEFICIARY_ALIASES: dict[str, tuple[str, ...]] = {
    "Mum": ("mum", "mummy", "mama"),
    "Dad": ("dad", "daddy", "papa"),
}

# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

QUANTA_SYSTEM_PROMPT = (
    "You are Quanta, the financial assistant inside UI Pay. "
    "UI Pay is a Nigerian payment application. "
    "All monetary amounts are in Nigerian Naira (NGN). "
    "Never use ₹, $, €, or any other currency symbol. "
    "When referring to money, use ₦ or 'naira'. "
    "The currency is application-controlled and must not be inferred from "
    "the user's wording. "
    "When a user asks to send money to a saved beneficiary, first call "
    "search_beneficiary to find them. "
    "Once you have the beneficiary_id and an amount, call prepare_transfer. "
    "prepare_transfer only prepares the transaction — it never executes it. "
    "A prepared transaction requires explicit user confirmation. "
    "Never claim that money was transferred merely because a transfer was prepared. "
    "Respond in the same language as the user's latest message whenever reasonably possible. "
    "Do not switch to English merely because a tool call or confirmation is being generated. "
    "Treat the latest explicit beneficiary and latest explicit amount as authoritative. "
    "If the user changes the beneficiary, do not restore an older amount associated with that "
    "beneficiary; preserve the current amount unless the user explicitly changes the amount. "
    "If the user changes the amount, preserve the current beneficiary unless the user explicitly "
    "changes the beneficiary. "
    "In Nigerian usage '10k', '10 thousand', '10 grand' and '10 boi' all mean ₦10,000. "
    "Each turn you receive an INTERNAL TRANSFER CONTEXT message with the beneficiary and "
    "amount owned by the application. When calling prepare_transfer, use exactly those values. "
    "The application overwrites any conflicting beneficiary_id or amount, and blocks the "
    "transfer if a value is UNSET; in that case ask the user for the missing value instead "
    "of guessing. Never take an amount from earlier turns of the conversation."
)


# ---------------------------------------------------------------------------
# Fix A — deterministic Nigerian money parsing
# ---------------------------------------------------------------------------
#
# Policy (documented so the tests and the product agree):
#   * A number with a unit word (k / thousand / grand / boi ...) is resolved.
#   * A bare number >= AMBIGUOUS_BARE_MAX (or any number next to ₦ / naira) is
#     taken literally.
#   * A bare number below AMBIGUOUS_BARE_MAX with no currency marker ("15") is
#     ambiguous: it is read as thousands only when the current amount is
#     already a whole number of thousands (INFER_THOUSANDS_FROM_CONTEXT);
#     otherwise Quanta asks instead of guessing.
#   * Long digit strings and numbers with a leading zero are account / phone
#     numbers, never amounts.
#   * If several amounts appear in one message, the last one wins and a note
#     is recorded.
#
# The Yoruba / Hausa / Igbo number-word tables are deliberately small and
# should be reviewed by native speakers before production use. Unrecognised
# wording fails safe: the application asks for the amount in figures.
# ---------------------------------------------------------------------------

INFER_THOUSANDS_FROM_CONTEXT = True
AMBIGUOUS_BARE_MAX = 100
MAX_AMOUNT_DIGITS = 9

# "bob" is intentionally NOT supported: it is ambiguous, so it fails safe.
_SUFFIX_MULTIPLIERS: dict[str, int] = {
    "k": 1_000,
    "thousand": 1_000,
    "thou": 1_000,
    "grand": 1_000,
    "boi": 1_000,
    "hundred": 100,
    "million": 1_000_000,
}

# Igbo / Hausa / Yoruba put the multiplier first: "puku iri", "dubu goma".
# Keys are matched after diacritics are stripped (ẹgbẹ̀rún -> egberun).
_PREFIX_MULTIPLIERS: dict[str, int] = {
    "puku": 1_000,  # Igbo
    "dubu": 1_000,  # Hausa
    "egberun": 1_000,  # Yoruba
}

_NUMBER_WORDS: dict[str, int] = {
    # English / Pidgin
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
    "thirteen": 13,
    "fourteen": 14,
    "fifteen": 15,
    "sixteen": 16,
    "seventeen": 17,
    "eighteen": 18,
    "nineteen": 19,
    "twenty": 20,
    "thirty": 30,
    "forty": 40,
    "fifty": 50,
    "sixty": 60,
    "seventy": 70,
    "eighty": 80,
    "ninety": 90,
    # Igbo
    "otu": 1,
    "abuo": 2,
    "ato": 3,
    "ano": 4,
    "ise": 5,
    "isii": 6,
    "asaa": 7,
    "asato": 8,
    "itoolu": 9,
    "iri": 10,
    # Hausa
    "daya": 1,
    "biyu": 2,
    "uku": 3,
    "hudu": 4,
    "biyar": 5,
    "shida": 6,
    "bakwai": 7,
    "takwas": 8,
    "tara": 9,
    "goma": 10,
    "ashirin": 20,
    "talatin": 30,
    "hamsin": 50,
    # Yoruba
    "okan": 1,
    "meji": 2,
    "meta": 3,
    "merin": 4,
    "marun": 5,
    "mefa": 6,
    "meje": 7,
    "mejo": 8,
    "mesan": 9,
    "mewa": 10,
    "mewaa": 10,
    "ogun": 20,
    "ogbon": 30,
    "aadota": 50,
}

_HYPHEN_FIXES = (("marun-un", "marun"), ("mesan-an", "mesan"))

_NUM = r"(?:\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?)"


def _alternation(words: Any) -> str:
    return "|".join(sorted((re.escape(str(w)) for w in words), key=len, reverse=True))


_WORDS_ALT = _alternation(_NUMBER_WORDS)
_SUFFIX_ALT = _alternation(_SUFFIX_MULTIPLIERS)
_PREFIX_ALT = _alternation(_PREFIX_MULTIPLIERS)

_SUFFIX_RE = re.compile(rf"(?<![\w.,])({_NUM})\s*({_SUFFIX_ALT})\b")
_WORD_SUFFIX_RE = re.compile(rf"\b({_WORDS_ALT})\s+({_SUFFIX_ALT})\b")
_PREFIX_RE = re.compile(rf"\b({_PREFIX_ALT})\s+({_NUM}|{_WORDS_ALT})(?!\w)")
_BARE_RE = re.compile(rf"(?<![\w.,])({_NUM})(?!\w)")
_CURRENCY_RE = re.compile(r"₦|\bnaira\b|\bngn\b")
_ORPHAN_MULTIPLIER_RE = re.compile(r"\b(?:thousand|million|puku|dubu|egberun)\b")


@dataclass(frozen=True)
class AmountParse:
    """Result of parsing one user message for a naira amount."""

    amount: int | None = None  # resolved whole-naira amount
    ambiguous: int | None = None  # bare small number we refuse to guess
    unresolved: bool = False  # amount-like wording we could not read
    note: str | None = None


def _fold(text: str) -> str:
    """Lowercase and strip diacritics so Yoruba/Igbo spellings compare equal."""
    decomposed = unicodedata.normalize("NFKD", text.lower())
    folded = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    for source, target in _HYPHEN_FIXES:
        folded = folded.replace(source, target)
    # "N5000" -> "₦5000"
    return re.sub(r"(?<![a-z0-9])n(?=\d)", "₦", folded)


def _to_decimal(raw: str) -> Decimal | None:
    try:
        return Decimal(raw.replace(",", ""))
    except InvalidOperation:
        return None


def _scan(pattern: re.Pattern[str], text: str, handler: Any) -> str:
    """Run handler on each match, then blank the span so later passes skip it."""
    blanked = list(text)
    for match in pattern.finditer(text):
        handler(match)
        for index in range(match.start(), match.end()):
            blanked[index] = " "
    return "".join(blanked)


def parse_amount(text: str) -> AmountParse:
    """Deterministically extract a naira amount from one user message."""
    folded = _fold(text)
    has_currency = bool(_CURRENCY_RE.search(folded))

    hits: list[tuple[int, int]] = []
    ambiguous: list[tuple[int, int]] = []
    unresolved = False

    def record(position: int, value: Decimal | None) -> None:
        nonlocal unresolved
        if value is None or value <= 0 or value != value.to_integral_value():
            unresolved = True
            return
        hits.append((position, int(value)))

    def suffix_handler(match: re.Match[str]) -> None:
        number = _to_decimal(match.group(1))
        multiplier = _SUFFIX_MULTIPLIERS[match.group(2)]
        record(match.start(), None if number is None else number * multiplier)

    def word_suffix_handler(match: re.Match[str]) -> None:
        number = Decimal(_NUMBER_WORDS[match.group(1)])
        record(match.start(), number * _SUFFIX_MULTIPLIERS[match.group(2)])

    def prefix_handler(match: re.Match[str]) -> None:
        token = match.group(2)
        number = Decimal(_NUMBER_WORDS[token]) if token in _NUMBER_WORDS else _to_decimal(token)
        multiplier = _PREFIX_MULTIPLIERS[match.group(1)]
        record(match.start(), None if number is None else number * multiplier)

    def bare_handler(match: re.Match[str]) -> None:
        nonlocal unresolved
        raw = match.group(1).replace(",", "")
        whole = raw.split(".")[0]
        if len(whole) > 1 and whole.startswith("0"):
            return  # account / phone number
        if len(whole) > MAX_AMOUNT_DIGITS:
            return  # account / phone number
        value = _to_decimal(raw)
        if value is None or value <= 0:
            return
        if value != value.to_integral_value():
            unresolved = True
            return
        number = int(value)
        if number >= AMBIGUOUS_BARE_MAX or has_currency:
            hits.append((match.start(), number))
        else:
            ambiguous.append((match.start(), number))

    masked = _scan(_SUFFIX_RE, folded, suffix_handler)
    masked = _scan(_WORD_SUFFIX_RE, masked, word_suffix_handler)
    masked = _scan(_PREFIX_RE, masked, prefix_handler)
    masked = _scan(_BARE_RE, masked, bare_handler)

    if hits:
        hits.sort()
        values = [value for _, value in hits]
        note = None
        if len(set(values)) > 1:
            note = (
                "multiple amounts mentioned "
                + ", ".join(f"₦{v:,}" for v in values)
                + f"; used the last (₦{values[-1]:,})"
            )
        return AmountParse(amount=values[-1], note=note)

    if unresolved:
        return AmountParse(unresolved=True)

    if ambiguous:
        ambiguous.sort()
        return AmountParse(ambiguous=ambiguous[-1][1])

    if _ORPHAN_MULTIPLIER_RE.search(masked):
        return AmountParse(unresolved=True)

    return AmountParse()


def _extract_amount(text: str) -> int | None:
    """Backwards-compatible wrapper: the resolved amount, or None."""
    return parse_amount(text).amount


# ---------------------------------------------------------------------------
# Beneficiary resolution
# ---------------------------------------------------------------------------


def _beneficiary_mentions(text: str) -> list[str]:
    """Demo nicknames mentioned in the text, ordered by position."""
    lowered = text.lower()
    hits: list[tuple[int, str]] = []
    for nickname, aliases in BENEFICIARY_ALIASES.items():
        for alias in aliases:
            for match in re.finditer(rf"\b{re.escape(alias)}\b", lowered):
                hits.append((match.start(), nickname))
    hits.sort()
    return [nickname for _, nickname in hits]


def _extract_beneficiary_name(text: str) -> str | None:
    """Latest mentioned demo beneficiary ("Kama dad, ziga ya mum" -> Mum)."""
    mentions = _beneficiary_mentions(text)
    return mentions[-1] if mentions else None


def _beneficiary_id_for_name(name: str | None) -> str | None:
    if name is None:
        return None
    for beneficiary in DEMO_BENEFICIARIES:
        if beneficiary["nickname"] == name:
            return beneficiary["id"]
    return None


# ---------------------------------------------------------------------------
# Manual-session state
# ---------------------------------------------------------------------------
#
# Production confirmation and conversation state belong to the authenticated
# UI Pay backend session. These in-memory objects exist only so the local
# interactive script can simulate multiple conversational turns.
# ---------------------------------------------------------------------------


@dataclass
class PendingConfirmation:
    reference: str
    beneficiary_id: str
    amount: int
    currency: str
    created_at: datetime
    expires_at: datetime


@dataclass
class TurnFacts:
    """What the *latest* user turn explicitly said (never carried over)."""

    explicit_beneficiary: str | None = None
    explicit_amount: int | None = None
    ambiguous_amount: int | None = None
    amount_unresolved: bool = False
    notes: list[str] = field(default_factory=list)


@dataclass
class TransferContext:
    """Deterministic transfer fields owned by the application, not the LLM.

    The model interprets language and selects tools. The application decides
    which beneficiary and amount are used for prepare_transfer.
    """

    beneficiary_name: str | None = None
    beneficiary_id: str | None = None
    amount: int | None = None
    facts: TurnFacts = field(default_factory=TurnFacts)
    audit: list[str] = field(default_factory=list)

    def reset(self) -> None:
        """Forget everything (after confirm / cancel / expiry)."""
        self.beneficiary_name = None
        self.beneficiary_id = None
        self.amount = None
        self.facts = TurnFacts()
        self.audit = []

    def update_from_user_input(self, text: str) -> TurnFacts:
        """Apply only the fields explicitly present in the latest user turn."""
        facts = TurnFacts()
        self.audit = []

        mentions = _beneficiary_mentions(text)
        if mentions:
            name = mentions[-1]
            self.beneficiary_name = name
            self.beneficiary_id = _beneficiary_id_for_name(name)
            facts.explicit_beneficiary = name
            if len(set(mentions)) > 1:
                facts.notes.append(
                    f"multiple beneficiaries mentioned ({', '.join(mentions)}); used the last ({name})"
                )

        parsed = parse_amount(text)
        if parsed.amount is not None:
            self.amount = parsed.amount
            facts.explicit_amount = parsed.amount
            if parsed.note:
                facts.notes.append(parsed.note)
        elif parsed.ambiguous is not None:
            inferred = self._infer_thousands(parsed.ambiguous)
            if inferred is not None:
                self.amount = inferred
                facts.explicit_amount = inferred
                facts.notes.append(
                    f"read bare '{parsed.ambiguous}' as ₦{inferred:,} because the current "
                    "amount is already in thousands"
                )
            else:
                # Never keep the old amount when the user changed it to
                # something we cannot read with confidence.
                self.amount = None
                facts.ambiguous_amount = parsed.ambiguous
        elif parsed.unresolved:
            self.amount = None
            facts.amount_unresolved = True

        self.facts = facts
        return facts

    def _infer_thousands(self, bare: int) -> int | None:
        if not INFER_THOUSANDS_FROM_CONTEXT:
            return None
        if self.amount is None or self.amount < 1_000 or self.amount % 1_000 != 0:
            return None
        return bare * 1_000

    def update_from_prepared_transfer(self, pending: PendingConfirmation) -> None:
        """Sync from the controlled prepare_transfer result (already verified)."""
        self.beneficiary_id = pending.beneficiary_id
        self.amount = pending.amount

    def clarification(self) -> str | None:
        """Question to ask when the context cannot support a transfer yet."""
        facts = self.facts

        if facts.amount_unresolved:
            return (
                "I couldn't read that amount clearly. Please write it in figures, "
                "for example 10k or ₦10,000."
            )

        if self.amount is None and facts.ambiguous_amount is not None:
            n = facts.ambiguous_amount
            return (
                f"Just to be sure: do you mean ₦{n:,} or ₦{n * 1_000:,}? "
                f"Please send the full amount, for example {n}k or ₦{n * 1_000:,}."
            )

        if self.beneficiary_id is None:
            names = " and ".join(b["nickname"] for b in DEMO_BENEFICIARIES)
            return (
                f"Who would you like to send this to? I have {names} in your saved beneficiaries."
            )

        if self.amount is None:
            return f"How much would you like to send to {self.beneficiary_name}?"

        return None

    def turn_notes(self) -> list[str]:
        return list(self.facts.notes) + list(self.audit)


@dataclass
class ChatSession:
    """Holds all mutable state for one interactive manual session."""

    session_id: str
    conversation: list[LLMMessage] = field(default_factory=list)
    pending_confirmation: PendingConfirmation | None = None
    transfer_context: TransferContext = field(default_factory=TransferContext)

    def invalidate_confirmation(self) -> None:
        """Discard any pending confirmation when a new request arrives."""
        self.pending_confirmation = None


@dataclass
class TurnResult:
    """Machine-readable result used by the interactive harness and Step 10 tests."""

    handled: bool
    action: str | None = None
    response: QuantaResponse | None = None
    pending: PendingConfirmation | None = None
    error: str | None = None
    notes: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Fix B — application-owned enforcement between the LLM and the orchestrator
# ---------------------------------------------------------------------------


def _arguments_dict(call: Any) -> dict[str, Any]:
    raw = getattr(call, "arguments", None) or {}
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except json.JSONDecodeError:
            raw = {}
    return dict(raw)


def _rebuild_tool_call(call: Any, arguments: dict[str, Any]) -> Any:
    try:
        if dataclasses.is_dataclass(call) and not isinstance(call, type):
            return dataclasses.replace(call, arguments=arguments)
        model_copy = getattr(call, "model_copy", None)
        if callable(model_copy):
            return model_copy(update={"arguments": arguments})
    except Exception:  # noqa: BLE001, S110
        pass
    return LLMToolCall(id=call.id, name=call.name, arguments=arguments)


def _rebuild_response(response: Any, tool_calls: list[Any]) -> Any:
    try:
        if dataclasses.is_dataclass(response) and not isinstance(response, type):
            return dataclasses.replace(response, tool_calls=tool_calls)
        model_copy = getattr(response, "model_copy", None)
        if callable(model_copy):
            return model_copy(update={"tool_calls": tool_calls})
    except Exception:  # noqa: BLE001, S110
        pass
    return LLMResponse(content=getattr(response, "content", None), tool_calls=tool_calls)


def _same_amount(candidate: Any, expected: int) -> bool:
    try:
        return int(Decimal(str(candidate))) == expected
    except (InvalidOperation, ValueError):
        return False


class TransferGuard:
    """Makes the TransferContext authoritative for financial arguments.

    The LLM still decides *that* a transfer should be prepared. The guard
    decides *which* beneficiary and amount are used:

    * prepare_transfer: beneficiary_id / amount are overwritten from the
      context; the call is blocked (and a clarification returned instead) when
      the context is incomplete or the amount is ambiguous.
    * search_beneficiary: when the user explicitly named a saved beneficiary
      this turn, the query is rewritten to the canonical nickname, so "mama"
      finds "Mum".
    """

    def __init__(self, context: TransferContext) -> None:
        self.context = context

    def enforce(self, response: Any) -> Any:
        calls = getattr(response, "tool_calls", None)
        if not calls or not isinstance(calls, (list, tuple)):
            return response

        ctx = self.context
        rewritten: list[Any] = []
        prepared = False
        changed = False

        for call in calls:
            name = getattr(call, "name", None)

            if name == "search_beneficiary":
                new_call = self._enforce_search(call)
            elif name == "prepare_transfer":
                clarification = ctx.clarification()
                if clarification is not None:
                    ctx.audit.append(
                        f"blocked prepare_transfer (incomplete or ambiguous fields): {clarification}"
                    )
                    return LLMResponse(content=clarification)
                if prepared:
                    ctx.audit.append("dropped duplicate prepare_transfer call")
                    changed = True
                    continue
                prepared = True
                new_call = self._enforce_prepare(call)
            else:
                new_call = call

            changed = changed or new_call is not call
            rewritten.append(new_call)

        return _rebuild_response(response, rewritten) if changed else response

    def _enforce_search(self, call: Any) -> Any:
        explicit = self.context.facts.explicit_beneficiary
        arguments = _arguments_dict(call)
        query = arguments.get("query")
        if explicit is None or query is None:
            return call
        if str(query).strip().lower() == explicit.lower():
            return call
        self.context.audit.append(f"rewrote search_beneficiary query {query!r} -> {explicit!r}")
        arguments["query"] = explicit
        return _rebuild_tool_call(call, arguments)

    def _enforce_prepare(self, call: Any) -> Any:
        ctx = self.context
        original = _arguments_dict(call)
        arguments = dict(original)

        if original.get("beneficiary_id") != ctx.beneficiary_id:
            ctx.audit.append(
                f"overrode LLM beneficiary_id {original.get('beneficiary_id')!r} -> {ctx.beneficiary_id!r}"
            )
        arguments["beneficiary_id"] = ctx.beneficiary_id

        assert ctx.amount is not None  # guaranteed by clarification() == None
        if not _same_amount(original.get("amount"), ctx.amount):
            ctx.audit.append(f"overrode LLM amount {original.get('amount')!r} -> {ctx.amount!r}")
        arguments["amount"] = ctx.amount

        if "currency" in arguments:
            arguments["currency"] = "NGN"

        if arguments == original:
            return call
        return _rebuild_tool_call(call, arguments)


class AuthoritativeProvider:
    """Transparent LLM-provider proxy that applies a TransferGuard.

    Every method of the wrapped provider is forwarded unchanged; whatever
    result carries ``tool_calls`` is passed through the guard first, so the
    orchestrator only ever sees guarded responses. Streaming (async generator)
    methods are forwarded untouched; the harness still verifies the prepared
    transfer afterwards and fails closed.
    """

    def __init__(self, inner: Any, guard: TransferGuard) -> None:
        self._inner = inner
        self._guard = guard

    def __getattr__(self, name: str) -> Any:
        if name in {"_inner", "_guard"}:
            raise AttributeError(name)

        attribute = getattr(self._inner, name)
        if not callable(attribute) or inspect.isasyncgenfunction(attribute):
            return attribute

        if inspect.iscoroutinefunction(attribute):

            @functools.wraps(attribute)
            async def guarded_async(*args: Any, **kwargs: Any) -> Any:
                return self._guard.enforce(await attribute(*args, **kwargs))

            return guarded_async

        @functools.wraps(attribute)
        def guarded(*args: Any, **kwargs: Any) -> Any:
            result = attribute(*args, **kwargs)
            if inspect.isawaitable(result):

                async def finish() -> Any:
                    return self._guard.enforce(await result)

                return finish()
            return self._guard.enforce(result)

        return guarded


# ---------------------------------------------------------------------------
# Mock LLM
# ---------------------------------------------------------------------------
#
# A deterministic, well-behaved stand-in for the model. It reads the latest
# user turn and the application's INTERNAL TRANSFER CONTEXT message. It never
# scans older conversation turns for amounts or beneficiaries (Fix C).
# ---------------------------------------------------------------------------

_CONTEXT_MARKER = "[INTERNAL TRANSFER CONTEXT"


def _latest_user_message(messages: list[LLMMessage]) -> str:
    """Return the most recent user message from the conversation."""

    for message in reversed(messages):
        if message.role == LLMMessageRole.USER and message.content:
            return message.content

    return ""


def _context_fields_from_messages(
    messages: list[LLMMessage],
) -> tuple[bool, str | None, int | None]:
    """Read the application's internal transfer-context message, if present."""

    for message in reversed(messages):
        content = message.content or ""
        if message.role == LLMMessageRole.ASSISTANT and content.startswith(_CONTEXT_MARKER):
            name_match = re.search(r"beneficiary_name=(\w+)", content)
            amount_match = re.search(r"amount_ngn=(\d+)", content)
            name = name_match.group(1) if name_match else None
            if name == "UNSET":
                name = None
            amount = int(amount_match.group(1)) if amount_match else None
            return True, name, amount

    return False, None, None


def _tool_results(messages: list[LLMMessage]) -> list[dict[str, Any]]:
    """Decoded tool-result payloads present in the current LLM turn."""

    results: list[dict[str, Any]] = []
    for message in messages:
        if message.role != LLMMessageRole.TOOL:
            continue
        try:
            payload = json.loads(message.content or "")
        except (json.JSONDecodeError, TypeError):
            continue
        if isinstance(payload, dict):
            results.append(payload)
    return results


def _conversation_has_tool_result(messages: list[LLMMessage]) -> bool:
    """Determine whether the current LLM turn already contains a tool result."""

    return any(message.role == LLMMessageRole.TOOL for message in messages)


def _conversation_has_beneficiary_result(messages: list[LLMMessage]) -> bool:
    """Determine whether a successful search_beneficiary result is present."""

    return any(
        payload.get("tool_name") == "search_beneficiary" and payload.get("success")
        for payload in _tool_results(messages)
    )


def _conversation_has_prepare_result(messages: list[LLMMessage]) -> bool:
    return any(
        payload.get("tool_name") == "prepare_transfer" for payload in _tool_results(messages)
    )


def create_mock_provider() -> MockLLMProvider:
    """
    Create a deterministic conversational mock provider.

    The mock recognises the demo beneficiary names and simple transfer
    amounts. It does not attempt to reproduce natural-language reasoning; its
    purpose is to exercise Quanta's orchestration deterministically.
    """

    def responder(
        messages: list[LLMMessage],
        system_prompt: str | None,
        tools: list[dict[str, Any]] | None,
    ) -> LLMResponse:
        user_input = _latest_user_message(messages)
        normalized_input = user_input.lower()

        has_context, context_name, context_amount = _context_fields_from_messages(messages)
        if has_context:
            beneficiary_name = context_name
            amount = context_amount
        else:
            beneficiary_name = _extract_beneficiary_name(user_input)
            amount = _extract_amount(user_input)

        is_transfer_intent = any(
            keyword in normalized_input for keyword in ("send", "transfer", "pay", "run")
        )

        # A transfer has already been prepared this turn: stop looping.
        if _conversation_has_prepare_result(messages):
            return LLMResponse(content="Please review and confirm the transfer.")

        # search_beneficiary has returned.
        if _conversation_has_beneficiary_result(messages):
            if beneficiary_name and amount is not None:
                beneficiary_id = _beneficiary_id_for_name(beneficiary_name)
                return LLMResponse(
                    tool_calls=[
                        LLMToolCall(
                            id=f"mock_prepare_{uuid4().hex[:8]}",
                            name="prepare_transfer",
                            arguments={"beneficiary_id": beneficiary_id, "amount": amount},
                        )
                    ]
                )
            if beneficiary_name:
                return LLMResponse(
                    content=(
                        f"I found {beneficiary_name} in your saved beneficiaries. "
                        "How much would you like to send?"
                    )
                )
            return LLMResponse(
                content="I found a saved beneficiary. How much would you like to send?"
            )

        # Any other tool result (e.g. a failed search): do not loop.
        if _conversation_has_tool_result(messages):
            return LLMResponse(content="I couldn't complete that lookup. Could you rephrase?")

        # Transfer requests first search for the beneficiary.
        if beneficiary_name and (is_transfer_intent or amount is not None):
            if amount is None:
                return LLMResponse(
                    content=f"How much would you like to send to {beneficiary_name}?"
                )
            return LLMResponse(
                tool_calls=[
                    LLMToolCall(
                        id=f"mock_search_{uuid4().hex[:8]}",
                        name="search_beneficiary",
                        arguments={"query": beneficiary_name},
                    )
                ]
            )

        # Simple beneficiary lookup ("find mum", "search dad", etc.)
        if beneficiary_name and any(
            keyword in normalized_input for keyword in ("find", "search", "look", "who", "show")
        ):
            return LLMResponse(
                tool_calls=[
                    LLMToolCall(
                        id=f"mock_search_{uuid4().hex[:8]}",
                        name="search_beneficiary",
                        arguments={"query": beneficiary_name},
                    )
                ]
            )

        # Amount-only clarification
        if amount is not None and not beneficiary_name:
            return LLMResponse(
                content=(
                    "Who would you like to send that to? "
                    "I have Mum and Dad in your saved beneficiaries."
                )
            )

        # Beneficiary-only clarification
        if beneficiary_name and amount is None:
            return LLMResponse(content=f"How much would you like to send to {beneficiary_name}?")

        return LLMResponse(
            content=(
                "I can help you find a saved beneficiary or prepare "
                "a transfer. Try 'send 5,000 to Mum' or 'find Dad'."
            )
        )

    return MockLLMProvider(
        responder=responder,
    )


# ---------------------------------------------------------------------------
# Provider selection
# ---------------------------------------------------------------------------


def create_provider(
    *,
    provider_name: str,
    settings: Settings,
) -> LLMProvider:
    """
    Select the concrete LLM provider for the manual session.

    The provider is injected into the Orchestrator rather than selected
    inside orchestration logic. This preserves the provider abstraction.
    """

    normalized = provider_name.lower()

    if normalized == "mock":
        return create_mock_provider()

    if normalized == "groq":
        return GroqProvider(settings=settings)

    if normalized == "claude":
        return ClaudeProvider(settings=settings)

    raise ValueError(f"Unsupported provider: {provider_name}")


# ---------------------------------------------------------------------------
# Quanta application wiring
# ---------------------------------------------------------------------------


def create_orchestrator(
    *,
    provider: LLMProvider,
) -> tuple[Orchestrator, MockUIPayClient]:
    """
    Build the Quanta dependency graph used by this manual harness.

    The UI Pay client remains mocked so no real financial system is touched.
    """

    ui_pay = MockUIPayClient(
        beneficiaries=DEMO_BENEFICIARIES,
    )

    registry = ToolRegistry()

    registry.register(
        SearchBeneficiaryTool(
            client=ui_pay,
        )
    )

    registry.register(PrepareTransferTool())

    executor = ToolExecutor(
        registry=registry,
        policy=ToolPolicy(),
    )

    orchestrator = Orchestrator(
        llm_provider=provider,
        tool_registry=registry,
        tool_executor=executor,
        system_prompt=QUANTA_SYSTEM_PROMPT,
    )

    return orchestrator, ui_pay


# ---------------------------------------------------------------------------
# Confirmation helpers
# ---------------------------------------------------------------------------


def _nfc(phrases: set[str]) -> set[str]:
    """Normalise phrase sets so composed / decomposed diacritics both match."""
    return {unicodedata.normalize("NFC", phrase) for phrase in phrases}


CONFIRMATION_PHRASES = _nfc(
    {
        # English
        "yes",
        "yes send it",
        "yes send it please",
        "confirm",
        "confirmed",
        "proceed",
        "go ahead",
        "goahead",
        "approve",
        "approved",
        "okay",
        "ok",
        "do it",
        "that's correct",
        "that is correct",
        # Nigerian Pidgin
        "yes send am",
        "oya send am",
        "make you send am",
        "sharp send am",
        # Yoruba
        "bẹẹni",
        "bẹ́ẹ̀ni",
        "bẹẹni tẹsiwaju",
        "bẹ́ẹ̀ni tẹ́síwájú",
        "tẹsiwaju",
        "tẹ́síwájú",
        # Hausa
        "eh",
        "eh ci gaba",
        "ci gaba",
        # Igbo
        "ee",
        "ee gaa n'ihu",
        "gaa n'ihu",
    }
)

CANCELLATION_PHRASES = _nfc(
    {
        # English
        "no",
        "no cancel",
        "cancel",
        "cancel it",
        "stop",
        "abort",
        "don't",
        "dont",
        "don't send it",
        "do not send it",
        # Nigerian Pidgin
        "abeg no send am",
        "no send am",
        "cancel am",
        "make you stop",
        "stop am",
        # Yoruba
        "rárá",
        "rara",
        "rárá fagilee rẹ̀",
        "rara fagilee re",
        "fagilee",
        "fagilee rẹ̀",
        "ma ṣe ránṣẹ́",
        "ma se ranse",
        # Hausa
        "a'a",
        "aa",
        "a'a soke shi",
        "aa soke shi",
        "soke",
        "soke shi",
        "kar a aika",
        # Igbo
        "mba",
        "mba kagbuo ya",
        "kagbuo",
        "kagbuo ya",
        "ezipụla ya",
        "ezipula ya",
    }
)


def _normalize_confirmation_input(text: str) -> str:
    """Normalize confirmation/cancellation text for deterministic matching."""
    normalized = unicodedata.normalize("NFC", text.lower().strip())
    normalized = normalized.replace("’", "'").replace("`", "'")
    normalized = re.sub(r"[.!?,;:]+", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.strip()


def is_confirmation(text: str) -> bool:
    """Return True only for explicitly allow-listed confirmation phrases."""
    return _normalize_confirmation_input(text) in CONFIRMATION_PHRASES


def is_cancellation(text: str) -> bool:
    """Return True only for explicitly allow-listed cancellation phrases."""
    return _normalize_confirmation_input(text) in CANCELLATION_PHRASES


def classify_confirmation_input(text: str) -> str | None:
    """Classify a pending-transfer response without invoking the LLM."""
    if is_confirmation(text):
        return "confirm"
    if is_cancellation(text):
        return "cancel"
    return None


def _build_internal_transfer_context_message(
    transfer_context: TransferContext,
) -> LLMMessage | None:
    """Give the LLM the application-owned transfer fields for this turn.

    This is an internal assistant-role message and is never displayed to the
    user. It is not authorization and cannot execute a transaction. The
    TransferGuard enforces these values regardless of what the model does.
    """
    if (
        transfer_context.beneficiary_name is None
        and transfer_context.beneficiary_id is None
        and transfer_context.amount is None
    ):
        return None

    name = transfer_context.beneficiary_name or "UNSET"
    beneficiary_id = transfer_context.beneficiary_id or "UNSET"
    amount = str(transfer_context.amount) if transfer_context.amount is not None else "UNSET"

    return LLMMessage(
        role=LLMMessageRole.ASSISTANT,
        content=(
            f"{_CONTEXT_MARKER} — application-managed, not user text] "
            f"beneficiary_name={name}; beneficiary_id={beneficiary_id}; amount_ngn={amount}. "
            "Use exactly these values when calling prepare_transfer; the application "
            "overwrites conflicting arguments. If a value is UNSET, ask the user for it "
            "instead of guessing. Never take an amount from earlier turns."
        ),
    )


def _find_beneficiary(
    *,
    ui_pay: MockUIPayClient,
    beneficiary_id: str,
) -> dict[str, Any] | None:
    """
    Retrieve the trusted demo beneficiary associated with a prepared transfer.

    The lookup is local to this development harness. In production, this
    information would come from the authoritative UI Pay backend.
    """

    for beneficiary in DEMO_BENEFICIARIES:
        if beneficiary["id"] == beneficiary_id:
            return beneficiary

    return None


def _build_confirmation_data(
    *,
    response: QuantaResponse,
    ui_pay: MockUIPayClient,
) -> PendingConfirmation | None:
    """
    Convert trusted prepare_transfer output into manual-session state.

    Only data returned by the controlled tool is used. The LLM's natural
    language response is never treated as authoritative transaction data.
    """

    if response.data is None:
        return None

    reference = response.data.get("reference")
    beneficiary_id = response.data.get("beneficiary_id")
    amount = response.data.get("amount")
    # currency is always NGN from the tool, but we read it back to verify
    currency = response.data.get("currency", "NGN")

    if not reference or not beneficiary_id or amount is None:
        return None

    beneficiary = _find_beneficiary(
        ui_pay=ui_pay,
        beneficiary_id=beneficiary_id,
    )

    if beneficiary is None:
        return None

    now = datetime.now(UTC)

    return PendingConfirmation(
        reference=str(reference),
        beneficiary_id=str(beneficiary_id),
        amount=int(amount),
        currency=str(currency),
        created_at=now,
        expires_at=now + timedelta(minutes=5),
    )


def display_confirmation_details(
    *,
    pending: PendingConfirmation,
    ui_pay: MockUIPayClient,
) -> None:
    """Display trusted confirmation information for the manual session."""

    beneficiary = _find_beneficiary(
        ui_pay=ui_pay,
        beneficiary_id=pending.beneficiary_id,
    )

    if beneficiary is None:
        return

    print()
    print("Confirmation details:")
    print(f"  Recipient: {beneficiary['account_name']}")
    print(f"  Nickname: {beneficiary['nickname']}")
    print(f"  Bank: {beneficiary['bank_name']}")
    print(f"  Account: {beneficiary['account_number']}")
    print(f"  Amount: ₦{pending.amount:,} ({pending.currency})")
    print(f"  Reference: {pending.reference}")
    print()
    print(
        "  Confirmation examples: confirm / yes, send it / Bẹ́ẹ̀ni, tẹ́síwájú / Eh, ci gaba / Ee, gaa n'ihu"
    )
    print(
        "  Cancellation examples: cancel / no, send am / Rárá, fagilee rẹ̀ / A'a, soke shi / Mba, kagbuo ya"
    )


# ---------------------------------------------------------------------------
# Response display
# ---------------------------------------------------------------------------


def display_response(
    response: QuantaResponse,
) -> None:
    """Display the normalized Quanta response in a human-readable format."""

    print()
    print("Quanta:")

    if response.speech:
        print(response.speech.text)

    if response.ui:
        print(f"\nUI state: {response.ui.type.value}")

    if response.data:
        print("\nData:")
        for key, value in response.data.items():
            print(f"  {key}: {value}")

    if response.error:
        print("\nError:")
        print(f"  Code: {response.error.code}")
        print(f"  Message: {response.error.message}")

    print(f"\nStatus: {response.status.value}")


def display_notes(notes: list[str]) -> None:
    """Show what the application parser / guard did this turn (diagnostics)."""

    if not notes:
        return

    print()
    print("Guard notes:")
    for note in notes:
        print(f"  - {note}")


# ---------------------------------------------------------------------------
# Pending-confirmation handling
# ---------------------------------------------------------------------------


async def handle_pending_confirmation(
    *,
    user_input: str,
    pending: PendingConfirmation,
    ui_pay: MockUIPayClient,
) -> TurnResult:
    """Handle a pending confirmation deterministically.

    No LLM call is made while a prepared financial operation is awaiting
    confirmation/cancellation. This is the authorization boundary.
    """
    if datetime.now(UTC) >= pending.expires_at:
        return TurnResult(handled=True, action="expired", pending=None)

    action = classify_confirmation_input(user_input)

    if action == "cancel":
        return TurnResult(handled=True, action="cancelled", pending=None)

    if action != "confirm":
        return TurnResult(handled=False, pending=pending)

    beneficiary = _find_beneficiary(
        ui_pay=ui_pay,
        beneficiary_id=pending.beneficiary_id,
    )

    if beneficiary is None:
        return TurnResult(
            handled=True,
            action="error",
            pending=None,
            error="The prepared beneficiary could no longer be verified.",
        )

    # This prototype stops here. Production UI Pay authorization/PIN must be
    # the next boundary; Quanta never executes the financial transfer.
    return TurnResult(
        handled=True,
        action="authorization_required",
        pending=None,
    )


# Outcomes that end a transfer flow: the context must not leak into the next one.
_TERMINAL_ACTIONS = {"cancelled", "expired", "authorization_required", "error"}


# ---------------------------------------------------------------------------
# Interactive session
# ---------------------------------------------------------------------------


class QuantaChatHarness:
    """Reusable manual/E2E harness around the same Quanta wiring.

    Step 10 imports this class so systematic tests exercise the same provider,
    orchestrator, tool registry, policy and mock UI Pay path as manual testing.

    ``provider`` lets a test inject its own LLM (for example an adversarial
    one). ``enforce_guard=False`` removes the TransferGuard so the harness's
    fail-closed verification can be tested on its own.
    """

    def __init__(
        self,
        *,
        provider_name: str,
        settings: Settings | None = None,
        provider: Any | None = None,
        enforce_guard: bool = True,
    ) -> None:
        self.settings = settings or Settings()
        self.provider_name = provider_name
        self.session = ChatSession(
            session_id=f"test-{uuid4().hex[:8]}",
        )

        inner = provider or create_provider(
            provider_name=provider_name,
            settings=self.settings,
        )
        self.raw_provider = inner
        self.guard = TransferGuard(self.session.transfer_context)
        self.provider = AuthoritativeProvider(inner, self.guard) if enforce_guard else inner
        self.enforce_guard = enforce_guard

        self.orchestrator, self.ui_pay = create_orchestrator(
            provider=self.provider,  # type: ignore[arg-type]  # AuthoritativeProvider is a transparent proxy
        )

    def _transfer_mismatch(self, pending: PendingConfirmation) -> str | None:
        """Independent backstop: a prepared transfer must equal the context."""
        ctx = self.session.transfer_context
        problems: list[str] = []

        if ctx.beneficiary_id is None or pending.beneficiary_id != ctx.beneficiary_id:
            problems.append(
                f"beneficiary {pending.beneficiary_id} != application context {ctx.beneficiary_id}"
            )
        if ctx.amount is None or pending.amount != ctx.amount:
            problems.append(f"amount {pending.amount} != application context {ctx.amount}")
        if pending.currency != "NGN":
            problems.append(f"currency {pending.currency} != NGN")

        if not problems:
            return None
        return "Prepared transfer rejected (fail closed): " + "; ".join(problems)

    def _remember_assistant_reply(self, response: QuantaResponse) -> None:
        if response.speech:
            self.session.conversation.append(
                LLMMessage(
                    role=LLMMessageRole.ASSISTANT,
                    content=response.speech.text,
                )
            )

    async def process_input(self, user_input: str) -> TurnResult:
        """Process one user turn through deterministic boundaries and Quanta."""
        user_input = user_input.strip()
        if not user_input:
            return TurnResult(handled=True, action="empty")

        ctx = self.session.transfer_context

        if self.session.pending_confirmation is not None:
            pending_result = await handle_pending_confirmation(
                user_input=user_input,
                pending=self.session.pending_confirmation,
                ui_pay=self.ui_pay,
            )

            if pending_result.handled:
                self.session.pending_confirmation = pending_result.pending
                if pending_result.action in _TERMINAL_ACTIONS:
                    ctx.reset()
                return pending_result

            # Any non-confirmation input is treated as a correction/new request.
            # The previous prepared transaction is therefore no longer active.
            self.session.pending_confirmation = None

        # Latest explicit beneficiary and amount are resolved by the
        # application, never by the LLM and never from conversation history.
        ctx.update_from_user_input(user_input)

        context_message = _build_internal_transfer_context_message(ctx)

        messages = list(self.session.conversation)
        if context_message is not None:
            messages.append(context_message)

        messages.append(
            LLMMessage(
                role=LLMMessageRole.USER,
                content=user_input,
            )
        )

        request_context = RequestContext.create(
            user_id=USER_ID,
            session_id=self.session.session_id,
            operation="manual_chat",
        )

        try:
            response = await self.orchestrator.process(
                context=request_context,
                user_input=user_input,
                messages=messages,
            )
        except Exception as exc:  # noqa: BLE001
            return TurnResult(
                handled=True,
                action="error",
                error=f"{type(exc).__name__}: {exc}",
                notes=ctx.turn_notes(),
            )

        # Conversation prose is kept only for language continuity. It is not
        # a source of transaction values.
        self.session.conversation.append(
            LLMMessage(
                role=LLMMessageRole.USER,
                content=user_input,
            )
        )

        notes = ctx.turn_notes()

        if response.status == ResponseStatus.CONFIRMATION_REQUIRED:
            pending = _build_confirmation_data(
                response=response,
                ui_pay=self.ui_pay,
            )

            if pending is None:
                return TurnResult(
                    handled=True,
                    action="error",
                    response=response,
                    error=(
                        "Confirmation was requested, but trusted prepared "
                        "transfer data could not be reconstructed."
                    ),
                    notes=notes,
                )

            mismatch = self._transfer_mismatch(pending)
            if mismatch is not None:
                self.session.pending_confirmation = None
                return TurnResult(
                    handled=True,
                    action="error",
                    response=response,
                    error=mismatch,
                    notes=notes,
                )

            self._remember_assistant_reply(response)
            self.session.pending_confirmation = pending
            ctx.update_from_prepared_transfer(pending)

            return TurnResult(
                handled=True,
                action="confirmation_required",
                response=response,
                pending=pending,
                notes=notes,
            )

        self._remember_assistant_reply(response)

        return TurnResult(
            handled=True,
            action="response",
            response=response,
            pending=self.session.pending_confirmation,
            notes=notes,
        )


def render_result(result: TurnResult, ui_pay: MockUIPayClient) -> None:
    """Print one TurnResult for the interactive session."""

    if result.action == "confirmation_required" and result.response is not None:
        display_response(result.response)
        if result.pending is not None:
            display_confirmation_details(pending=result.pending, ui_pay=ui_pay)

    elif result.action == "authorization_required":
        print()
        print("Quanta:")
        print("Confirmation received.")
        print(
            "The transfer is prepared, but this manual Quanta prototype "
            "does not execute financial transactions."
        )
        print("The next production boundary is UI Pay authorization/PIN before execution.")
        print("Status: authorization_required")

    elif result.action == "cancelled":
        print()
        print("Quanta:")
        print("The prepared transfer has been cancelled.")
        print()
        print("Status: cancelled")

    elif result.action == "expired":
        print()
        print("Quanta:")
        print("The pending transfer confirmation has expired.")
        print()
        print("Status: expired")

    elif result.action == "error":
        print()
        print("Quanta error:")
        print(f"  {result.error}")

    elif result.response is not None:
        display_response(result.response)

    display_notes(result.notes)
    print()


async def run_chat(
    *,
    provider_name: str,
) -> None:
    harness = QuantaChatHarness(provider_name=provider_name)
    session = harness.session
    ui_pay = harness.ui_pay

    print()
    print("--- Quanta Interactive Chat ---")
    print(f"Provider: {provider_name}")
    print(f"Session: {session.session_id}")
    print()
    print("Available demo beneficiaries:")
    print("  Mum → Amaka Okafor, GTBank, 0123456789")
    print("  Dad → Chinedu Okafor, Access Bank, 0987654321")
    print()
    print("Example inputs:")
    print("  find mum")
    print("  find dad")
    print("  send 5k to mum")
    print("  transfer ₦10,000 to dad")
    print("  run mama 10 boi for me")
    print()
    print("Confirmation examples:")
    print("  confirm")
    print("  yes, send it")
    print("  Bẹ́ẹ̀ni, tẹ́síwájú")
    print("  Eh, ci gaba")
    print("  Ee, gaa n'ihu")
    print()
    print("Cancellation examples:")
    print("  cancel")
    print("  no, send am")
    print("  Rárá, fagilee rẹ̀")
    print("  A'a, soke shi")
    print("  Mba, kagbuo ya")
    print()
    print("Type 'exit' or 'quit' to exit.")
    print()

    while True:
        try:
            user_input = await asyncio.to_thread(input, "You: ")
        except (EOFError, KeyboardInterrupt):
            print("\nExiting.")
            return

        user_input = user_input.strip()

        if not user_input:
            continue

        if user_input.lower() in {"exit", "quit"}:
            print("Exiting.")
            return

        result = await harness.process_input(user_input)
        render_result(result, ui_pay)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=("Interact with the Quanta orchestration layer using a selected LLM provider.")
    )

    parser.add_argument(
        "provider",
        choices=["mock", "groq", "claude"],
        help="LLM provider to use for the manual session.",
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    asyncio.run(
        run_chat(
            provider_name=args.provider,
        )
    )


if __name__ == "__main__":
    main()
