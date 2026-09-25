from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from app.core.amount_parser import INFER_THOUSANDS_FROM_CONTEXT, parse_amount
from app.schemas.confirmation import PendingConfirmation


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
    account_name: str | None = None
    account_number: str | None = None
    bank_code: str | None = None
    bank_name: str | None = None
    amount: int | None = None
    currency: str = "NGN"
    validated_account: bool = False
    prepared_reference: str | None = None
    facts: TurnFacts = field(default_factory=TurnFacts)
    audit: list[str] = field(default_factory=list)

    def reset(self) -> None:
        """Forget everything (after confirm / cancel / expiry)."""
        self.beneficiary_name = None
        self.beneficiary_id = None
        self.account_name = None
        self.account_number = None
        self.bank_code = None
        self.bank_name = None
        self.amount = None
        self.currency = "NGN"
        self.validated_account = False
        self.prepared_reference = None
        self.facts = TurnFacts()
        self.audit = []

    def update_from_user_input(
        self,
        text: str,
        *,
        beneficiary_aliases: dict[str, tuple[str, ...]] | None = None,
        beneficiaries_list: list[dict[str, Any]] | None = None,
    ) -> TurnFacts:
        """Apply only the fields explicitly present in the latest user turn."""
        facts = TurnFacts()
        self.audit = []

        aliases = beneficiary_aliases or {
            "Mum": ("mum", "mummy", "mama"),
            "Dad": ("dad", "daddy", "papa"),
        }
        b_list = beneficiaries_list or [
            {"id": "ben_001", "nickname": "Mum"},
            {"id": "ben_002", "nickname": "Dad"},
        ]

        mentions = self._find_mentions(text, aliases)
        if mentions:
            name = mentions[-1]
            self.beneficiary_name = name
            self.beneficiary_id = self._find_id_for_name(name, b_list)
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
                self.amount = None
                facts.ambiguous_amount = parsed.ambiguous
        elif parsed.unresolved:
            self.amount = None
            facts.amount_unresolved = True

        self.facts = facts
        return facts

    @staticmethod
    def _find_mentions(text: str, aliases: dict[str, tuple[str, ...]]) -> list[str]:
        lowered = text.lower()
        hits: list[tuple[int, str]] = []
        for nickname, alias_list in aliases.items():
            for alias in alias_list:
                for match in re.finditer(rf"\b{re.escape(alias)}\b", lowered):
                    hits.append((match.start(), nickname))
        hits.sort()
        return [nickname for _, nickname in hits]

    @staticmethod
    def _find_id_for_name(name: str, beneficiaries: list[dict[str, Any]]) -> str | None:
        for b in beneficiaries:
            if b.get("nickname") == name or b.get("account_name") == name:
                return b.get("id")
        return None

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
        self.prepared_reference = pending.reference

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
            return "Who would you like to send this to? Please specify a saved beneficiary."

        if self.amount is None:
            name_str = f" to {self.beneficiary_name}" if self.beneficiary_name else ""
            return f"How much would you like to send{name_str}?"

        return None

    def turn_notes(self) -> list[str]:
        return list(self.facts.notes) + list(self.audit)
