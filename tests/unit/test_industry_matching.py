from underwriting_agent.rules.industry_matching import (
    contains_term,
    normalize_text,
)


def test_normalize_text_removes_accents_case_and_punctuation() -> None:
    assert (
        normalize_text("  Fabrication d'ARMES à feu! ") == "fabrication d armes a feu"
    )


def test_contains_term_requires_whole_words() -> None:
    assert contains_term(normalize_text("a poker club"), "poker") is True
    assert contains_term(normalize_text("pokerface agency"), "poker") is False


def test_contains_term_accepts_simple_plurals() -> None:
    assert contains_term(normalize_text("three casinos"), "casino") is True
