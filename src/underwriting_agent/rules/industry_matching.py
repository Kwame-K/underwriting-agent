"""Accent- and punctuation-insensitive whole-word phrase matching."""

import re
import unicodedata


def normalize_text(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value.casefold())
    without_accents = "".join(
        char for char in decomposed if not unicodedata.combining(char)
    )
    return " ".join(re.sub(r"[^a-z0-9]+", " ", without_accents).split())


def contains_term(normalized_text: str, term: str) -> bool:
    """Return True if the term appears as whole words (optional plural)."""
    normalized_term = normalize_text(term)
    if not normalized_term:
        return False

    pattern = rf"(?<![a-z0-9]){re.escape(normalized_term)}(?:s|es)?(?![a-z0-9])"

    return re.search(pattern, normalized_text) is not None
