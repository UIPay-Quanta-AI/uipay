from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any

INFER_THOUSANDS_FROM_CONTEXT = True
AMBIGUOUS_BARE_MAX = 100
MAX_AMOUNT_DIGITS = 9

_SUFFIX_MULTIPLIERS: dict[str, int] = {
    "k": 1_000,
    "thousand": 1_000,
    "thou": 1_000,
    "grand": 1_000,
    "boi": 1_000,
    "hundred": 100,
    "million": 1_000_000,
}

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
