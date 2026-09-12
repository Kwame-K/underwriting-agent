from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field, model_validator


class DecisionReviewStatus(StrEnum):
    PENDING_REVIEW = "PENDING_REVIEW"
    UNDERWRITER_APPROVED = "UNDERWRITER_APPROVED"
    UNDERWRITER_MODIFIED = "UNDERWRITER_MODIFIED"
    UNDERWRITER_DECLINED = "UNDERWRITER_DECLINED"
    UNDERWRITER_REQUESTED_INFORMATION = "UNDERWRITER_REQUESTED_INFORMATION"


class UnderwriterReviewAction(StrEnum):
    APPROVE = "APPROVE"
    MODIFY = "MODIFY"
    DECLINE = "DECLINE"
    REQUEST_INFORMATION = "REQUEST_INFORMATION"


class UnderwriterModifications(BaseModel):
    approved_limit_cad: int | None = Field(
        default=None,
        gt=0,
        description="Replacement coverage limit approved by the underwriter.",
    )
    retention_cad: int | None = Field(
        default=None,
        ge=0,
        description="Replacement retention approved by the underwriter.",
    )
    annual_premium_cad: int | None = Field(
        default=None,
        gt=0,
        description="Replacement annual premium approved by the underwriter.",
    )
    added_conditions: list[str] = Field(default_factory=list)
    removed_conditions: list[str] = Field(default_factory=list)

    @property
    def has_changes(self) -> bool:
        return any(
            [
                self.approved_limit_cad is not None,
                self.retention_cad is not None,
                self.annual_premium_cad is not None,
                bool(self.added_conditions),
                bool(self.removed_conditions),
            ]
        )


class ReviewDecisionCommand(BaseModel):
    action: UnderwriterReviewAction
    reviewer_id: str = Field(min_length=1, max_length=100)
    comment: str = Field(min_length=1, max_length=2_000)
    modifications: UnderwriterModifications | None = None

    @model_validator(mode="after")
    def validate_modifications(self) -> "ReviewDecisionCommand":
        if self.action is UnderwriterReviewAction.MODIFY and (
            self.modifications is None or not self.modifications.has_changes
        ):
            raise ValueError("A MODIFY review requires at least one modification.")

        if (
            self.action is not UnderwriterReviewAction.MODIFY
            and self.modifications is not None
        ):
            raise ValueError("Modifications are only allowed for a MODIFY review.")

        return self

    @property
    def resulting_status(self) -> DecisionReviewStatus:
        statuses = {
            UnderwriterReviewAction.APPROVE: (
                DecisionReviewStatus.UNDERWRITER_APPROVED
            ),
            UnderwriterReviewAction.MODIFY: (DecisionReviewStatus.UNDERWRITER_MODIFIED),
            UnderwriterReviewAction.DECLINE: (
                DecisionReviewStatus.UNDERWRITER_DECLINED
            ),
            UnderwriterReviewAction.REQUEST_INFORMATION: (
                DecisionReviewStatus.UNDERWRITER_REQUESTED_INFORMATION
            ),
        }

        return statuses[self.action]


class DecisionReview(BaseModel):
    decision_id: str
    review_status: DecisionReviewStatus
    reviewer_id: str
    review_comment: str
    reviewed_at: datetime
    review_modifications: UnderwriterModifications | None = None
