"""Systematic multilingual E2E diagnostics for Quanta (Step 10).

Run this against the hardened chat_quanta harness (Step 9.1). The tests use the
real LLM provider when requested and the real Quanta orchestration/tool path,
while Mock UI Pay prevents any real financial transaction.

Groups
------
parser      Deterministic money-parser table (no LLM, no orchestrator).
direct      Direct transfer request + confirmation, all four languages.
search      Search beneficiary first, amount second, then confirmation.
cancel      Deterministic cancellation (no LLM inference).
context     Beneficiary/amount replacement sequences per language.
regression  Replays of the bugs seen in the manual session:
            "10 boi" -> 10k, and the stale ₦15,000 resurfacing.
guard       Adversarial LLM (always proposes ben_002 / ₦99,999) proving the
            application owns beneficiary + amount, and that the harness fails
            closed if the guard is removed. Always uses a scripted mock LLM.

Examples:
    python scripts/test_multilingual_quanta.py groq
    python scripts/test_multilingual_quanta.py mock
    python scripts/test_multilingual_quanta.py groq --scenario regression -v
"""

from __future__ import annotations

import argparse
import asyncio
import json
from dataclasses import dataclass, field
from typing import Any

from chat_quanta import DEMO_BENEFICIARIES, QuantaChatHarness, TurnResult, parse_amount

from app.providers.llm.base import (
    LLMMessage,
    LLMMessageRole,
    LLMResponse,
    LLMToolCall,
)
from app.providers.llm.mock import MockLLMProvider

BENEFICIARY_IDS: dict[str, str] = {b["nickname"]: b["id"] for b in DEMO_BENEFICIARIES}

# Harness modes
MODE_PROVIDER = "provider"  # the provider chosen on the command line
MODE_ADVERSARY_GUARDED = "adversary_guarded"
MODE_ADVERSARY_UNGUARDED = "adversary_unguarded"


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Turn:
    """One user turn and what must be true afterwards.

    Context expectations (beneficiary / amount / cleared / unset) describe the
    application-owned TransferContext, which is deterministic. ``action`` is
    what the harness reported; with ``soft=True`` an unexpected action is
    downgraded to REVIEW because it reflects LLM behaviour, not a safety rule.
    """

    text: str
    action: str | tuple[str, ...] | None = None
    beneficiary: str | None = None
    amount: int | None = None
    amount_unset: bool = False
    context_cleared: bool = False
    no_pending: bool = False
    notes_contain: str | None = None
    soft: bool = False


@dataclass(frozen=True)
class Scenario:
    name: str
    language: str
    turns: tuple[Turn, ...]
    mode: str = MODE_PROVIDER


@dataclass
class CaseResult:
    language: str
    name: str
    passed: bool = True
    review: bool = False
    details: list[str] = field(default_factory=list)


def _request(text: str, beneficiary: str, amount: int, *, soft: bool = False) -> Turn:
    return Turn(
        text,
        action="confirmation_required",
        beneficiary=beneficiary,
        amount=amount,
        soft=soft,
    )


def _confirm(text: str, *, soft: bool = False) -> Turn:
    return Turn(
        text, action="authorization_required", context_cleared=True, no_pending=True, soft=soft
    )


def _cancel(text: str) -> Turn:
    return Turn(text, action="cancelled", context_cleared=True, no_pending=True)


# ---------------------------------------------------------------------------
# Parser table (Fix A)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AmountCase:
    text: str
    amount: int | None = None
    ambiguous: int | None = None
    unresolved: bool = False


def parser_cases() -> list[AmountCase]:
    return [
        # Table from the review: expected ₦10,000 / ₦5,000 / ₦15,000
        AmountCase("10k", amount=10_000),
        AmountCase("10 k", amount=10_000),
        AmountCase("10K", amount=10_000),
        AmountCase("10 thousand", amount=10_000),
        AmountCase("10 thousand naira", amount=10_000),
        AmountCase("10 boi", amount=10_000),
        AmountCase("10 boi naira", amount=10_000),
        AmountCase("5 boi", amount=5_000),
        AmountCase("15 boi", amount=15_000),
        AmountCase("2 boi", amount=2_000),
        AmountCase("₦10,000", amount=10_000),
        # Other Nigerian / common forms
        AmountCase("10 grand", amount=10_000),
        AmountCase("10 thou", amount=10_000),
        AmountCase("N5000", amount=5_000),
        AmountCase("5,000", amount=5_000),
        AmountCase("5000", amount=5_000),
        AmountCase("1.5k", amount=1_500),
        AmountCase("2.5 thousand", amount=2_500),
        AmountCase("ten thousand", amount=10_000),
        AmountCase("five boi", amount=5_000),
        AmountCase("5 hundred", amount=500),
        AmountCase("500 naira", amount=500),
        AmountCase("500", amount=500),
        # Whole sentences from the manual session
        AmountCase("you fit run mama 10 boi for me?", amount=10_000),
        AmountCase("oya run mum 10 boi for me", amount=10_000),
        AmountCase("no na, 10 boi na 10k", amount=10_000),
        AmountCase("send 5k to mum", amount=5_000),
        AmountCase("transfer ₦10,000 to dad", amount=10_000),
        AmountCase("increase am from 10k to 15k", amount=15_000),
        # Yoruba / Hausa / Igbo
        AmountCase("Fi 10000 ranṣẹ si Mum", amount=10_000),
        AmountCase("Gbanwee ego ka ọ bụrụ 15k", amount=15_000),
        AmountCase("Achọrọ m iziga dad puku iri naira", amount=10_000),
        AmountCase("puku ise", amount=5_000),
        AmountCase("dubu goma", amount=10_000),
        AmountCase("dubu biyar", amount=5_000),
        AmountCase("ẹgbẹ̀rún mẹ́wàá", amount=10_000),
        # Ambiguous bare numbers are never guessed by the parser
        AmountCase("make am 15", ambiguous=15),
        AmountCase("send 5 to mum", ambiguous=5),
        # No amount at all
        AmountCase("Kama dad, ziga ya mum"),
        AmountCase("find mum"),
        AmountCase("yes, send it"),
        AmountCase("send to mum 0123456789"),  # account number, not an amount
        AmountCase("call me on 08012345678"),  # phone number, not an amount
        # Wording we cannot read must fail safe
        AmountCase("send mum thousand", unresolved=True),
        AmountCase("puku", unresolved=True),
        AmountCase("1.2345k", unresolved=True),
    ]


def _describe_parse(amount: int | None, ambiguous: int | None, unresolved: bool) -> str:
    if amount is not None:
        return f"₦{amount:,}"
    if ambiguous is not None:
        return f"ambiguous({ambiguous})"
    if unresolved:
        return "unresolved"
    return "no amount"


def run_parser_cases() -> list[CaseResult]:
    results: list[CaseResult] = []

    for case in parser_cases():
        parsed = parse_amount(case.text)
        actual = _describe_parse(parsed.amount, parsed.ambiguous, parsed.unresolved)
        expected = _describe_parse(case.amount, case.ambiguous, case.unresolved)

        result = CaseResult(language="-", name="parser", passed=actual == expected)
        if result.passed:
            result.details.append(f"{case.text!r} -> {actual}")
        else:
            result.details.append(f"{case.text!r}: expected {expected}, got {actual}")
        results.append(result)

    return results


# ---------------------------------------------------------------------------
# Scenario builders
# ---------------------------------------------------------------------------


def direct_cases() -> list[Scenario]:
    """Basic direct-transfer coverage in all four target languages."""
    return [
        Scenario(
            "direct transfer",
            "Pidgin",
            (_request("Run mama 10k for me", "Mum", 10_000), _confirm("yes, send am")),
        ),
        Scenario(
            "direct transfer",
            "Yoruba",
            (_request("Fi 10000 ranṣẹ si Mum", "Mum", 10_000), _confirm("Bẹ́ẹ̀ni, tẹ́síwájú")),
        ),
        Scenario(
            "direct transfer",
            "Hausa",
            (_request("Aika 10k zuwa Mum", "Mum", 10_000), _confirm("Eh, ci gaba")),
        ),
        Scenario(
            "direct transfer",
            "Igbo",
            (_request("Zipu 10k nye Mum", "Mum", 10_000), _confirm("Ee, gaa n'ihu")),
        ),
    ]


def search_then_amount_cases() -> list[Scenario]:
    """Search beneficiary first, then supply the amount separately."""
    return [
        Scenario(
            "search then amount",
            "Pidgin",
            (
                Turn("Find Mum", beneficiary="Mum", amount_unset=True),
                _request("10k", "Mum", 10_000),
                _confirm("yes, send am"),
            ),
        ),
        Scenario(
            "search then amount",
            "Yoruba",
            (
                Turn("Wa Mum", beneficiary="Mum", amount_unset=True),
                _request("10000", "Mum", 10_000),
                _confirm("Bẹ́ẹ̀ni, tẹ́síwájú"),
            ),
        ),
        Scenario(
            "search then amount",
            "Hausa",
            (
                Turn("Nemo Mum", beneficiary="Mum", amount_unset=True),
                _request("10k", "Mum", 10_000),
                _confirm("Eh, ci gaba"),
            ),
        ),
        Scenario(
            "search then amount",
            "Igbo",
            (
                Turn("Chọọ Mum", beneficiary="Mum", amount_unset=True),
                _request("10k", "Mum", 10_000),
                _confirm("Ee, gaa n'ihu"),
            ),
        ),
    ]


def cancellation_cases() -> list[Scenario]:
    """Verify that cancellation is handled locally, without LLM inference."""
    return [
        Scenario(
            "cancellation",
            "Pidgin",
            (_request("Run mama 10k for me", "Mum", 10_000), _cancel("no send am")),
        ),
        Scenario(
            "cancellation",
            "Yoruba",
            (_request("Fi 10000 ranṣẹ si Mum", "Mum", 10_000), _cancel("Rárá, fagilee rẹ̀")),
        ),
        Scenario(
            "cancellation",
            "Hausa",
            (_request("Aika 10k zuwa Mum", "Mum", 10_000), _cancel("A'a, soke shi")),
        ),
        Scenario(
            "cancellation",
            "Igbo",
            (_request("Zipu 10k nye Mum", "Mum", 10_000), _cancel("Mba, kagbuo ya")),
        ),
    ]


def _correction_turns(
    first: str, raise_amount: str, switch: str, final_amount: str
) -> tuple[Turn, ...]:
    """Mum 10k -> Mum 15k -> Dad 15k (amount preserved) -> Dad 12k.

    The context expectations are hard (deterministic). Whether the LLM
    prepares a transfer on each turn is soft (REVIEW when it asks instead).
    """
    return (
        _request(first, "Mum", 10_000, soft=True),
        _request(raise_amount, "Mum", 15_000, soft=True),
        _request(switch, "Dad", 15_000, soft=True),
        _request(final_amount, "Dad", 12_000, soft=True),
    )


def context_correction_cases() -> list[Scenario]:
    """Exercise the bug-prone beneficiary/amount replacement sequence."""
    return [
        Scenario(
            "context correction",
            "Pidgin",
            _correction_turns(
                "Run mama 10k for me",
                "increase am to 15k",
                "send am give my papa",
                "make am 12k",
            ),
        ),
        Scenario(
            "context correction",
            "Yoruba",
            _correction_turns(
                "Fi 10000 ranṣẹ si Mum",
                "Yi iye pada si 15000",
                "Ránṣẹ́ sí Dad",
                "Yi iye pada si 12000",
            ),
        ),
        Scenario(
            "context correction",
            "Hausa",
            _correction_turns(
                "Aika 10k zuwa Mum",
                "Canja adadin zuwa 15k",
                "Aika zuwa Dad",
                "Canja adadin zuwa 12k",
            ),
        ),
        Scenario(
            "context correction",
            "Igbo",
            _correction_turns(
                "Zipu 10k nye Mum",
                "Gbanwee ego ka ọ bụrụ 15k",
                "Zipu ya nye Dad",
                "Gbanwee ya ka ọ bụrụ 12k",
            ),
        ),
    ]


def regression_cases() -> list[Scenario]:
    """Replays of the defects found in the manual Groq session."""
    return [
        # "10 boi" was read as ₦10.
        Scenario(
            "'10 boi' means ₦10,000",
            "Pidgin",
            (_request("you fit run mama 10 boi for me?", "Mum", 10_000),),
        ),
        # The old ₦15,000 came back after a confirmation and a language switch.
        Scenario(
            "stale ₦15,000 must not resurface",
            "Mixed",
            (
                _request("oya run mum 10 boi for me", "Mum", 10_000, soft=True),
                _request("oya send am give my dad", "Dad", 10_000, soft=True),
                # Amount is already in thousands, so a bare "15" is read as 15k.
                _request("make am 15", "Dad", 15_000, soft=True),
                # "send am" is not a confirmation phrase: it prepares again.
                _request("send am", "Dad", 15_000, soft=True),
                _confirm("oya send am", soft=True),
                _request("Achọrọ m iziga dad puku iri naira", "Dad", 10_000, soft=True),
                # Beneficiary changes; amount must stay ₦10,000, never ₦15,000.
                _request("Kama dad, ziga ya mum", "Mum", 10_000, soft=True),
            ),
        ),
        # A cold, bare small number is never guessed.
        Scenario(
            "bare '15' with no context is not guessed",
            "Pidgin",
            (
                Turn(
                    "send 15 to mum",
                    action="response",
                    beneficiary="Mum",
                    amount_unset=True,
                    no_pending=True,
                ),
                _request("15k", "Mum", 15_000),
            ),
        ),
        # Account numbers are not amounts.
        Scenario(
            "account number is not an amount",
            "English",
            (
                Turn(
                    "send to mum 0123456789",
                    action="response",
                    beneficiary="Mum",
                    amount_unset=True,
                    no_pending=True,
                ),
            ),
        ),
    ]


def guard_cases() -> list[Scenario]:
    """Adversarial-LLM checks for Fix B (application-owned fields)."""
    return [
        Scenario(
            "LLM arguments are overwritten",
            "Pidgin",
            (
                Turn(
                    "Run mama 10k for me",
                    action="confirmation_required",
                    beneficiary="Mum",
                    amount=10_000,
                    notes_contain="overrode",
                ),
            ),
            mode=MODE_ADVERSARY_GUARDED,
        ),
        Scenario(
            "LLM search query 'mama' is canonicalised",
            "Pidgin",
            (
                Turn(
                    "you fit run mama 10 boi for me?",
                    action="confirmation_required",
                    beneficiary="Mum",
                    amount=10_000,
                    notes_contain="rewrote search_beneficiary",
                ),
            ),
            mode=MODE_ADVERSARY_GUARDED,
        ),
        Scenario(
            "LLM cannot prepare an ambiguous amount",
            "Pidgin",
            (
                Turn(
                    "send 15 to mum",
                    action="response",
                    amount_unset=True,
                    no_pending=True,
                    notes_contain="blocked prepare_transfer",
                ),
            ),
            mode=MODE_ADVERSARY_GUARDED,
        ),
        Scenario(
            "LLM cannot prepare without a beneficiary",
            "Pidgin",
            (
                Turn(
                    "send 10k",
                    action="response",
                    no_pending=True,
                    notes_contain="blocked prepare_transfer",
                ),
            ),
            mode=MODE_ADVERSARY_GUARDED,
        ),
        Scenario(
            "guard removed: contaminated transfer fails closed",
            "Pidgin",
            (
                Turn(
                    "Run mama 10k for me",
                    action=("error", "response"),
                    no_pending=True,
                ),
            ),
            mode=MODE_ADVERSARY_UNGUARDED,
        ),
    ]


# ---------------------------------------------------------------------------
# Adversarial LLM
# ---------------------------------------------------------------------------


def build_adversarial_provider() -> MockLLMProvider:
    """A scripted LLM that always proposes the wrong beneficiary and amount.

    It searches for "mama" (which Mock UI Pay cannot find), then tries to
    prepare a ₦99,999 transfer to ben_002 whatever the user asked for.
    """

    def responder(
        messages: list[LLMMessage],
        system_prompt: str | None,
        tools: list[dict[str, Any]] | None,
    ) -> LLMResponse:
        seen: list[str] = []
        for message in messages:
            if message.role != LLMMessageRole.TOOL:
                continue
            try:
                seen.append(str(json.loads(message.content or "").get("tool_name")))
            except (json.JSONDecodeError, TypeError, AttributeError):
                continue

        if "prepare_transfer" in seen:
            return LLMResponse(content="Please review and confirm the transfer.")

        if "search_beneficiary" in seen:
            return LLMResponse(
                tool_calls=[
                    LLMToolCall(
                        id="adv_prepare",
                        name="prepare_transfer",
                        arguments={"beneficiary_id": "ben_002", "amount": 99_999},
                    )
                ]
            )

        return LLMResponse(
            tool_calls=[
                LLMToolCall(
                    id="adv_search",
                    name="search_beneficiary",
                    arguments={"query": "mama"},
                )
            ]
        )

    return MockLLMProvider(responder=responder)


def _build_harness(provider: str, mode: str) -> QuantaChatHarness:
    if mode == MODE_PROVIDER:
        return QuantaChatHarness(provider_name=provider)
    if mode == MODE_ADVERSARY_GUARDED:
        return QuantaChatHarness(
            provider_name="mock", provider=build_adversarial_provider(), enforce_guard=True
        )
    if mode == MODE_ADVERSARY_UNGUARDED:
        return QuantaChatHarness(
            provider_name="mock", provider=build_adversarial_provider(), enforce_guard=False
        )
    raise ValueError(f"Unknown harness mode: {mode}")


# ---------------------------------------------------------------------------
# Checking
# ---------------------------------------------------------------------------


def _fmt_amount(amount: int | None) -> str:
    return "unset" if amount is None else f"₦{amount:,}"


def _as_tuple(action: str | tuple[str, ...] | None) -> tuple[str, ...]:
    if action is None:
        return ()
    if isinstance(action, str):
        return (action,)
    return action


def _check_turn(
    harness: QuantaChatHarness,
    turn: Turn,
    result: TurnResult,
    number: int,
) -> tuple[list[str], list[str], list[str]]:
    """Return (failures, reviews, info) for one turn."""
    failures: list[str] = []
    reviews: list[str] = []
    info: list[str] = []

    ctx = harness.session.transfer_context
    expected_actions = _as_tuple(turn.action)

    if result.action == "error" and "error" not in expected_actions:
        failures.append(f"turn {number}: ERROR - {result.error}")
        return failures, reviews, info

    action_ok = not expected_actions or result.action in expected_actions
    if not action_ok:
        message = f"turn {number}: expected {'/'.join(expected_actions)}, got {result.action}"
        (reviews if turn.soft else failures).append(message)

    # ---- Application-owned context (deterministic, always hard) ----
    if turn.beneficiary is not None and ctx.beneficiary_name != turn.beneficiary:
        failures.append(
            f"turn {number}: context beneficiary expected {turn.beneficiary}, "
            f"got {ctx.beneficiary_name}"
        )

    if turn.amount is not None and ctx.amount != turn.amount:
        failures.append(
            f"turn {number}: context amount expected {_fmt_amount(turn.amount)}, "
            f"got {_fmt_amount(ctx.amount)}"
        )

    if turn.amount_unset and ctx.amount is not None:
        failures.append(f"turn {number}: amount should be unset, got {_fmt_amount(ctx.amount)}")

    if turn.context_cleared and action_ok:
        leftovers = (ctx.beneficiary_name, ctx.beneficiary_id, ctx.amount)
        if any(value is not None for value in leftovers):
            failures.append(f"turn {number}: context not cleared: {leftovers}")

    if turn.no_pending and action_ok and harness.session.pending_confirmation is not None:
        failures.append(f"turn {number}: a pending confirmation still exists")

    # ---- Any prepared transfer must equal the application context ----
    if result.action == "confirmation_required":
        pending = result.pending
        if pending is None:
            failures.append(f"turn {number}: confirmation_required without pending data")
        else:
            expected_id = BENEFICIARY_IDS.get(ctx.beneficiary_name or "")
            if pending.beneficiary_id != expected_id:
                failures.append(
                    f"turn {number}: prepared beneficiary {pending.beneficiary_id} "
                    f"!= context {expected_id}"
                )
            if pending.amount != ctx.amount:
                failures.append(
                    f"turn {number}: prepared {_fmt_amount(pending.amount)} "
                    f"!= context {_fmt_amount(ctx.amount)}"
                )
            if pending.currency != "NGN":
                failures.append(f"turn {number}: wrong currency {pending.currency}")
            info.append(
                f"t{number} prepared {pending.beneficiary_id} / "
                f"{_fmt_amount(pending.amount)} / {pending.currency}"
            )
    elif result.action == "cancelled":
        info.append(f"t{number} cancelled locally")
    elif result.action == "authorization_required":
        info.append(f"t{number} confirmed locally")
    else:
        info.append(f"t{number} {result.action}")

    if turn.notes_contain is not None and not any(
        turn.notes_contain in note for note in result.notes
    ):
        failures.append(
            f"turn {number}: expected a guard note containing {turn.notes_contain!r}; "
            f"notes were {result.notes}"
        )

    return failures, reviews, info


async def _run_scenario(
    *,
    provider: str,
    scenario: Scenario,
    verbose: bool,
) -> CaseResult:
    harness = _build_harness(provider, scenario.mode)
    case = CaseResult(language=scenario.language, name=scenario.name)

    for index, turn in enumerate(scenario.turns, start=1):
        result = await harness.process_input(turn.text)
        failures, reviews, info = _check_turn(harness, turn, result, index)

        if verbose:
            ctx = harness.session.transfer_context
            print(
                f"    t{index} You: {turn.text!r} -> {result.action} | "
                f"context=({ctx.beneficiary_name}, {_fmt_amount(ctx.amount)})"
            )
            for note in result.notes:
                print(f"         note: {note}")

        case.details.extend(info)
        case.details.extend(failures)
        case.details.extend(reviews)

        if failures:
            case.passed = False
            return case

        if reviews:
            case.review = True

    return case


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------


def _status(case: CaseResult) -> str:
    if not case.passed:
        return "FAIL"
    if case.review:
        return "REVIEW"
    return "PASS"


def _print_case(case: CaseResult) -> None:
    print(f"[{_status(case):6}] {case.language:7} | {case.name:44} | " + " ; ".join(case.details))


SCENARIO_BUILDERS = {
    "direct": direct_cases,
    "search": search_then_amount_cases,
    "cancel": cancellation_cases,
    "context": context_correction_cases,
    "regression": regression_cases,
    "guard": guard_cases,
}


async def run_all(provider: str, selected: str, verbose: bool) -> list[CaseResult]:
    results: list[CaseResult] = []

    if selected in {"all", "parser"}:
        for case in run_parser_cases():
            results.append(case)
            _print_case(case)

    groups = list(SCENARIO_BUILDERS) if selected == "all" else [selected]

    for group in groups:
        if group == "parser":
            continue
        for scenario in SCENARIO_BUILDERS[group]():
            case = await _run_scenario(provider=provider, scenario=scenario, verbose=verbose)
            results.append(case)
            _print_case(case)

    return results


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run Quanta's systematic multilingual E2E diagnostics."
    )
    parser.add_argument(
        "provider",
        choices=["mock", "groq", "claude"],
        help="LLM provider to test (the guard group always uses a scripted mock LLM).",
    )
    parser.add_argument(
        "--scenario",
        choices=["all", "parser", "direct", "search", "cancel", "context", "regression", "guard"],
        default="all",
        help="Subset of scenarios to run.",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Print every turn with the application-owned context.",
    )
    return parser.parse_args()


async def main() -> None:
    args = parse_args()

    results = await run_all(
        provider=args.provider,
        selected=args.scenario,
        verbose=args.verbose,
    )

    passed = sum(1 for r in results if r.passed and not r.review)
    review = sum(1 for r in results if r.passed and r.review)
    failed = sum(1 for r in results if not r.passed)

    print()
    print("========== MULTILINGUAL E2E SUMMARY ==========")
    print(f"Provider: {args.provider}")
    print(f"Cases: {len(results)}")
    print(f"PASS: {passed}")
    print(f"FAIL: {failed}")
    print(f"REVIEW: {review}")
    print("===============================================")

    # REVIEW is non-fatal because LLM language quality and tool-calling choices
    # can vary. Deterministic parser, context, guard and boundary failures are fatal.
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())
