from __future__ import annotations

import re
import unicodedata
from enum import Enum


class ConfirmationIntent(str, Enum):
    """Structured intent classification for a confirmation turn."""

    CONFIRM = "confirm"
    CANCEL = "cancel"
    MODIFY = "modify"
    AMBIGUOUS = "ambiguous"
    OTHER = "other"


def _nfc(phrases: set[str]) -> set[str]:
    return {unicodedata.normalize("NFC", phrase) for phrase in phrases}


# ---------------------------------------------------------------------------
# Confirmation phrase sets
# ---------------------------------------------------------------------------

# Phrases that unambiguously mean "proceed" regardless of context.
EXPLICIT_CONFIRM_PHRASES: set[str] = _nfc(
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
        "i confirm",
        # Nigerian Pidgin — clear affirmatives
        "yes na",
        "yes abeg",
        "oya go",
        "sharp",
        "sharp sharp",
        "sharp send am",
        "sharp confam",
        "make e go",
        "make e run",
        "make we run am",
        "no wahala",
        "no wahala run am",
        "e correct",
        "na correct",
        "na so",
        "na so send am",
        "run am now",
        "run am sharp sharp",
        "fire down",
        "fire down abeg",
        "you too much fire down",
        "correct",
        "correct no dulling",
        # Yoruba — confirmation
        "bẹẹni",
        "bẹ́ẹ̀ni",
        "bẹẹni tẹsiwaju",
        "bẹ́ẹ̀ni tẹ́síwájú",
        "tẹsiwaju",
        "tẹ́síwájú",
        "ṣe e",
        "ṣe bẹ́ẹ̀",
        "ránṣẹ́",
        "rán an lọ",
        "jẹ́ kó lọ",
        "jẹ́ kí o lọ",
        "o tọ",
        "o tọ́",
        "ó dáa",
        "dáadáa",
        "ko si wahala",
        "ko si iṣoro",
        "lọ siwaju",
        "lọ síwájú",
        # Hausa — confirmation
        "eh",
        "eh ci gaba",
        "ci gaba",
        "ci gaba da shi",
        "ci gaba da aika",
        "eh aika",
        "eh aika shi",
        "yi hakan",
        "yi shi",
        "ka yi shi",
        "ki yi shi",
        "to",
        "to ci gaba",
        "da kyau",
        "shikenan",
        "babu matsala",
        "mu ci gaba",
        # Igbo — confirmation
        "ee",
        "ee gaa n'ihu",
        "gaa n'ihu",
        "gaa n'ihu na ya",
        "mee ya",
        "mee nke a",
        "zipụ ya",
        "zipu ya",
        "ka zipụ ya",
        "ka zipu ya",
        "ọ dị mma",
        "o di mma",
        "ọ dị mma gaa n'ihu",
        "o di mma gaa n'ihu",
        "enweghị nsogbu",
        "enweghi nsogbu",
        "ka anyị gaa",
        "ka ayi gaa",
    }
)

# Phrases that mean "proceed" ONLY when the user is replying to an active
# confirmation prompt.  Outside that context these phrases can carry different
# meanings (e.g. "send am" as a brand-new transfer instruction).
CONTEXTUAL_CONFIRM_PHRASES: set[str] = _nfc(
    {
        # Nigerian Pidgin
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
    }
)

# ---------------------------------------------------------------------------
# Cancellation phrase sets
# ---------------------------------------------------------------------------

EXPLICIT_CANCEL_PHRASES: set[str] = _nfc(
    {
        # English
        "no",
        "no cancel",
        "no cancel am",
        "cancel",
        "cancel it",
        "stop",
        "abort",
        "don't",
        "dont",
        "don't send it",
        "do not send it",
        "don't send",
        "wait stop",
        "don't fire down",
        "don't fire down yet",
        "hold on",
        "wait first",
        "wait",
        "no be this one",
        "no be this",
        "i don change my mind",
        "i change my mind",
        # Nigerian Pidgin
        "abeg no",
        "abeg no send am",
        "cancel am",
        "stop am",
        "no send am",
        "no run am",
        "no do am",
        "make you no send am",
        "make you stop am",
        "stop am there",
        "leave am",
        "leave am like that",
        "forget am",
        "forget about am",
        "make we leave am",
        "abeg stop",
        "cancel am abeg",
        "make you cancel am",
        "dont run am",
        "don't run am",
        # Yoruba — cancellation
        "rárá",
        "rara",
        "fagilé",
        "fagilé e",
        "fagilé rẹ̀",
        "fagilee",
        "fagilee rẹ̀",
        "fagilee re",
        "rárá fagilee rẹ̀",
        "rara fagilee re",
        "ma ṣe ránṣẹ́",
        "má ṣe ránṣẹ́",
        "má ṣe rán an",
        "ma ran an",
        "ma ṣe",
        "da duro",
        "dá dúró",
        "jẹ́ kí a dúró",
        "má ṣe tẹsiwaju",
        "má tẹsiwaju",
        "ma ranse",
        "má ránṣẹ́",
        "mo ti yí ọkàn mi padà",
        "mo ti yi okan mi pada",
        # Hausa — cancellation
        "a'a",
        "aa",
        "a'a kar ka aika",
        "a'a kar ki aika",
        "kar a aika",
        "kar ka aika",
        "kar ki aika",
        "kar a tura",
        "kar ka tura",
        "kar ki tura",
        "daina",
        "daina shi",
        "bar shi",
        "bar wannan",
        "ka dakata",
        "ki dakata",
        "mu dakata",
        "kar a ci gaba",
        "kar ka ci gaba",
        "kar ki ci gaba",
        "na canza ra'ayi",
        "na canza raayi",
        "a'a soke shi",
        "aa soke shi",
        "soke",
        "soke shi",
        # Igbo — cancellation
        "mba",
        "mba kagbuo ya",
        "kagbuo",
        "kagbuo ya",
        "akagbula",
        "akagbula ya",
        "ezipụla ya",
        "ezipula ya",
        "ezipụla ya ugbu a",
        "akwụsịla",
        "akwusi",
        "kwụsị",
        "kwusi",
        "kwụsị ya",
        "kwusi ya",
        "ka anyị kwụsị",
        "ka ayi kwusi",
        "emela ya",
        "emela nke a",
        "achọghị m ya",
        "achoghi m ya",
    }
)

# ---------------------------------------------------------------------------
# Regex patterns
# ---------------------------------------------------------------------------

# Modification signals.  Checked BEFORE cancellation so that inputs like
# "no, send to Mum instead" → MODIFY rather than CANCEL.
MODIFICATION_PATTERNS: list[str] = [
    # Explicit redirection / substitution keywords
    r"\b(?:instead|switch|rather)\b",
    # "change" only when directed at the transfer (not "change my mind")
    r"\bchange\s+(?:it|the|to|beneficiary|amount|recipient|address)\b",
    # "make it / make am [something]"
    r"\bmake\s+(?:it|am)\b",
    # "send to [word]" — redirecting recipient
    r"\bsend\s+to\s+\w",
    # Explicit amount with slang denomination — strong modification signal
    r"\b\d+\s*(?:k|thousand|grand|boi|naira|hundred|million|puku|dubu|egberun)\b",
]

# Cancellation patterns — tightened to avoid false positives from short words.
# These run AFTER exact-phrase matching and AFTER modification checks.
# Single-word cancel signals ("no", "mba", "a'a", etc.) live exclusively in
# EXPLICIT_CANCEL_PHRASES where exact matching prevents partial-word ambiguity.
CANCELLATION_PATTERNS: list[str] = [
    # "don't / do not / never" immediately followed by a transfer action verb
    r"\b(?:don't|dont|do\s+not|never)\s+(?:send|run|do|fire|transfer)\b",
    # Hausa "kar" prohibitive construction: kar a/ka/ki + verb
    r"\bkar\s+(?:a|ka|ki)\s+\w+\b",
    # Igbo negative-perfective / imperative stop forms
    r"\b(?:ezipụla|ezipula|akwụsịla|akwusịla|kwụsị|kwusi)\b",
    # Yoruba prohibitive (má ṣe) or halt (da duro)
    r"\b(?:má?\s*ṣe|da\s*duro|dá\s*dúró)\b",
    # Pidgin "make you no/stop/cancel" constructions
    r"\bmake\s+you\s+(?:no|stop|cancel)\b",
    # "leave am" / "forget am" — explicit abandonment
    r"\b(?:leave|forget)\s+am\b",
]

# Ambiguous signals — checked before modification or cancellation.
AMBIGUOUS_PATTERNS: list[str] = [
    r"\b(?:maybe|hmm+|not\s+sure|should\s+i)\b",
]


class ConfirmationResolver:
    """
    Structured, layered intent resolver for a user response during a pending
    transfer confirmation.

    Security rules
    --------------
    * Modification signals beat confirmation signals.
    * Cancellation does **not** automatically beat modification when the user
      is clearly redirecting (e.g. "no, send to Mum instead" → MODIFY).
    * Contextual phrases (e.g. "send am") are only treated as CONFIRM when
      ``in_confirmation_context=True``.
    * No ``assert`` statements are used in production code.
    """

    @staticmethod
    def normalize(text: str) -> str:
        """Lowercase, NFC-normalise, collapse punctuation and whitespace."""
        normalized = unicodedata.normalize("NFC", text.lower().strip())
        # Normalise curly apostrophes / backticks to plain ASCII apostrophe
        normalized = normalized.replace("\u2019", "'").replace("`", "'")
        # Replace punctuation runs with a single space
        normalized = re.sub(r"[.!?,;:]+", " ", normalized)
        normalized = re.sub(r"\s+", " ", normalized)
        return normalized.strip()

    def resolve(
        self,
        text: str,
        *,
        in_confirmation_context: bool = True,
    ) -> ConfirmationIntent:
        """
        Classify a user utterance into a ``ConfirmationIntent``.

        Parameters
        ----------
        text:
            Raw user input.
        in_confirmation_context:
            Set to ``False`` when there is no active pending confirmation so
            that contextual phrases like "send am" are not misclassified as
            CONFIRM (they would instead return OTHER).
        """
        raw = text.strip()
        if not raw:
            return ConfirmationIntent.OTHER

        normalized = self.normalize(raw)

        # 1. Literal question mark in raw input → always ambiguous.
        if "?" in raw:
            return ConfirmationIntent.AMBIGUOUS

        # 2. Vocabulary ambiguity patterns.
        if any(re.search(p, normalized) for p in AMBIGUOUS_PATTERNS):
            return ConfirmationIntent.AMBIGUOUS

        # 3. Modification signals win — must be checked before cancellation
        #    so that mixed signals like "no, send to Mum instead" → MODIFY.
        if any(re.search(p, normalized) for p in MODIFICATION_PATTERNS):
            return ConfirmationIntent.MODIFY

        # 4. Exact-match cancellation phrases.
        if normalized in EXPLICIT_CANCEL_PHRASES:
            return ConfirmationIntent.CANCEL

        # 5. Exact-match confirmation phrases (always valid).
        if normalized in EXPLICIT_CONFIRM_PHRASES:
            return ConfirmationIntent.CONFIRM

        # 6. Contextual confirmation phrases (only valid inside a confirmation).
        if in_confirmation_context and normalized in CONTEXTUAL_CONFIRM_PHRASES:
            return ConfirmationIntent.CONFIRM

        # 7. Structured cancellation patterns (multi-word; lower false-positive risk).
        if any(re.search(p, normalized) for p in CANCELLATION_PATTERNS):
            return ConfirmationIntent.CANCEL

        # 8. Short-token confirmation fallback for terse but unambiguous words.
        tokens = normalized.split()
        if len(tokens) <= 3 and any(
            t in {"confirm", "proceed", "sharp", "correct"} for t in tokens
        ):
            return ConfirmationIntent.CONFIRM

        return ConfirmationIntent.OTHER
