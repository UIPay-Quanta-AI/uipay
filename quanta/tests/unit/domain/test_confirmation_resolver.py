from __future__ import annotations

import pytest

from app.domain.confirmation.resolver import (
    CONTEXTUAL_CONFIRM_PHRASES,
    EXPLICIT_CANCEL_PHRASES,
    EXPLICIT_CONFIRM_PHRASES,
    ConfirmationIntent,
    ConfirmationResolver,
)


@pytest.fixture
def resolver() -> ConfirmationResolver:
    return ConfirmationResolver()


# ---------------------------------------------------------------------------
# Normalisation
# ---------------------------------------------------------------------------


def test_normalize_lowercases_and_strips(resolver: ConfirmationResolver) -> None:
    assert resolver.normalize("  YES  ") == "yes"


def test_normalize_collapses_punctuation(resolver: ConfirmationResolver) -> None:
    # "bẹẹni, tẹsiwaju" → "bẹẹni tẹsiwaju" (comma becomes space)
    result = resolver.normalize("bẹẹni, tẹsiwaju")
    assert "," not in result
    assert "bẹẹni" in result


def test_normalize_curly_apostrophe(resolver: ConfirmationResolver) -> None:
    # Right single quotation mark → ASCII apostrophe
    assert resolver.normalize("don\u2019t") == "don't"


# ---------------------------------------------------------------------------
# Explicit confirm (always, context-independent)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "phrase",
    [
        # English
        "yes",
        "confirm",
        "confirmed",
        "proceed",
        "go ahead",
        "okay",
        "ok",
        "yes send it",
        "do it",
        "that's correct",
        "i confirm",
        # Nigerian Pidgin
        "sharp",
        "sharp sharp",
        "fire down",
        "fire down abeg",
        "correct no dulling",
        "no wahala",
        "no wahala run am",
        "e correct",
        "na correct",
        "run am now",
        "run am sharp sharp",
        "yes na",
        "yes abeg",
        "oya go",
        "make e go",
        # Yoruba
        "bẹẹni",
        "bẹ́ẹ̀ni",
        "bẹẹni tẹsiwaju",
        "bẹ́ẹ̀ni tẹ́síwájú",
        "tẹsiwaju",
        "tẹ́síwájú",
        "ránṣẹ́",
        "o tọ",
        "ó dáa",
        "ko si wahala",
        "lọ siwaju",
        # Hausa
        "eh",
        "eh ci gaba",
        "ci gaba",
        "ci gaba da shi",
        "yi shi",
        "ka yi shi",
        "to",
        "da kyau",
        "babu matsala",
        "mu ci gaba",
        # Igbo
        "ee",
        "ee gaa n'ihu",
        "gaa n'ihu",
        "mee ya",
        "zipụ ya",
        "ọ dị mma",
        "o di mma",
        "enweghị nsogbu",
        "ka anyị gaa",
    ],
)
def test_explicit_confirm_phrases(resolver: ConfirmationResolver, phrase: str) -> None:
    assert resolver.resolve(phrase) == ConfirmationIntent.CONFIRM
    # Must also work when context flag is False (they are ALWAYS-confirm phrases)
    assert resolver.resolve(phrase, in_confirmation_context=False) == ConfirmationIntent.CONFIRM


# ---------------------------------------------------------------------------
# Contextual confirm phrases (only valid inside a confirmation)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "phrase",
    [
        "run am",
        "run am for me",
        "run am for me abeg",
        "abeg run am",
        "yes send am",
        "oya send am",
        "send am",
        "send am abeg",
        "do am",
        "oya do am",
        "fire am",
        "fire am down",
        "you fit send am",
        "send am make e go",
    ],
)
def test_contextual_confirm_inside_confirmation(
    resolver: ConfirmationResolver, phrase: str
) -> None:
    assert resolver.resolve(phrase, in_confirmation_context=True) == ConfirmationIntent.CONFIRM


@pytest.mark.parametrize(
    "phrase",
    [
        "run am",
        "send am",
        "do am",
        "fire am",
    ],
)
def test_contextual_confirm_outside_confirmation_returns_other(
    resolver: ConfirmationResolver, phrase: str
) -> None:
    # Outside a confirmation these look like new instructions, not confirmations.
    assert resolver.resolve(phrase, in_confirmation_context=False) == ConfirmationIntent.OTHER


# ---------------------------------------------------------------------------
# Cancellation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "phrase",
    [
        # English
        "no",
        "cancel",
        "cancel it",
        "stop",
        "abort",
        "don't send it",
        "do not send it",
        "wait",
        "hold on",
        "i change my mind",
        "i don change my mind",
        # Nigerian Pidgin
        "no send am",
        "no run am",
        "abeg no send am",
        "no do am",
        "leave am",
        "forget am",
        "make you cancel am",
        "cancel am abeg",
        "abeg stop",
        "don't run am",
        "dont run am",
        # Yoruba
        "rárá",
        "rara",
        "fagilé",
        "rara fagilee re",
        "rárá fagilee rẹ̀",
        "ma ṣe ránṣẹ́",
        "má ṣe ránṣẹ́",
        "da duro",
        "mo ti yi okan mi pada",
        "má tẹsiwaju",
        # Hausa
        "a'a",
        "kar a aika",
        "kar ka aika",
        "daina",
        "bar shi",
        "mu dakata",
        "kar a ci gaba",
        "na canza raayi",
        "soke",
        # Igbo
        "mba",
        "mba kagbuo ya",
        "kagbuo",
        "ezipụla ya",
        "ezipula ya",
        "akwusi",
        "kwụsị ya",
        "ka ayi kwusi",
        "achoghi m ya",
    ],
)
def test_resolver_cancellation(resolver: ConfirmationResolver, phrase: str) -> None:
    assert resolver.resolve(phrase) == ConfirmationIntent.CANCEL


# ---------------------------------------------------------------------------
# Modification wins — including critical "yes + change" cases
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "phrase",
    [
        # Mixed confirm + modify → MODIFY must win
        "yes, make it 20k",
        "yes make it 20k",
        "run am for me, but make it 20k",
        "send it to Mum instead",
        "make it 15k",
        "change the beneficiary",
        "run am but make it 50k",
        # Cancel signal + modify signal → MODIFY wins
        "no, send to Mum instead",
        "no actually make it 5k",
        "cancel that, change it to 30k",
    ],
)
def test_resolver_modification_wins(resolver: ConfirmationResolver, phrase: str) -> None:
    assert resolver.resolve(phrase) == ConfirmationIntent.MODIFY


# ---------------------------------------------------------------------------
# Cancellation wins over plain confirmation keywords
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "phrase",
    [
        "don't run am",
        "no, don't send it",
        "wait, don't fire down",
        "don't fire down yet",
        "make you no send am",
        "make you stop am",
        "leave am like that",
        "forget about am",
    ],
)
def test_resolver_cancellation_wins_over_confirm(
    resolver: ConfirmationResolver, phrase: str
) -> None:
    assert resolver.resolve(phrase) == ConfirmationIntent.CANCEL


# ---------------------------------------------------------------------------
# Ambiguous
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "phrase",
    [
        # Question mark makes it always ambiguous
        "run am?",
        "should I run am?",
        "confirm?",
        "send it?",
        # Uncertainty vocabulary
        "hmm",
        "hmmmm",
        "maybe",
        "not sure",
    ],
)
def test_resolver_ambiguous(resolver: ConfirmationResolver, phrase: str) -> None:
    assert resolver.resolve(phrase) == ConfirmationIntent.AMBIGUOUS


# ---------------------------------------------------------------------------
# Other (unrecognised inputs)
# ---------------------------------------------------------------------------


def test_resolver_empty_input(resolver: ConfirmationResolver) -> None:
    assert resolver.resolve("") == ConfirmationIntent.OTHER
    assert resolver.resolve("   ") == ConfirmationIntent.OTHER


def test_resolver_unrelated_input(resolver: ConfirmationResolver) -> None:
    assert resolver.resolve("what is my balance") == ConfirmationIntent.OTHER
    assert resolver.resolve("hello") == ConfirmationIntent.OTHER


# ---------------------------------------------------------------------------
# Phrase-set completeness sanity checks
# ---------------------------------------------------------------------------


def test_explicit_confirm_and_cancel_sets_are_disjoint() -> None:
    overlap = EXPLICIT_CONFIRM_PHRASES & EXPLICIT_CANCEL_PHRASES
    assert not overlap, f"Phrases in both confirm and cancel sets: {overlap}"


def test_contextual_confirm_not_in_explicit_cancel() -> None:
    overlap = CONTEXTUAL_CONFIRM_PHRASES & EXPLICIT_CANCEL_PHRASES
    assert not overlap, f"Contextual phrases also in cancel set: {overlap}"


def test_contextual_and_explicit_confirm_disjoint() -> None:
    overlap = CONTEXTUAL_CONFIRM_PHRASES & EXPLICIT_CONFIRM_PHRASES
    assert not overlap, f"Phrases in both contextual and explicit confirm sets: {overlap}"
