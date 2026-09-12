import pytest
from pydantic import ValidationError

from underwriting_agent.domain.review import (
    DecisionReviewStatus,
    ReviewDecisionCommand,
    UnderwriterReviewAction,
)


def test_approve_review_maps_to_approved_status() -> None:
    command = ReviewDecisionCommand(
        action=UnderwriterReviewAction.APPROVE,
        reviewer_id="underwriter-001",
        comment="Risk accepted as quoted.",
    )

    assert command.resulting_status is (DecisionReviewStatus.UNDERWRITER_APPROVED)


def test_modify_review_requires_modifications() -> None:
    with pytest.raises(ValidationError, match="requires at least one"):
        ReviewDecisionCommand(
            action=UnderwriterReviewAction.MODIFY,
            reviewer_id="underwriter-001",
            comment="Limit adjusted.",
        )


def test_modify_review_accepts_modified_terms() -> None:
    command = ReviewDecisionCommand(
        action=UnderwriterReviewAction.MODIFY,
        reviewer_id="underwriter-001",
        comment="Limit and premium adjusted after review.",
        modifications={
            "approved_limit_cad": 750_000,
            "annual_premium_cad": 18_500,
            "added_conditions": ["MFA must be enabled before policy inception."],
        },
    )

    assert command.resulting_status is (DecisionReviewStatus.UNDERWRITER_MODIFIED)
    assert command.modifications is not None
    assert command.modifications.approved_limit_cad == 750_000


def test_non_modify_review_cannot_include_modifications() -> None:
    with pytest.raises(ValidationError, match="only allowed for a MODIFY"):
        ReviewDecisionCommand(
            action=UnderwriterReviewAction.APPROVE,
            reviewer_id="underwriter-001",
            comment="Approved.",
            modifications={
                "approved_limit_cad": 750_000,
            },
        )
