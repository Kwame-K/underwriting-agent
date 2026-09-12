from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class UnderwritingSubmissionRecord(Base):
    __tablename__ = "underwriting_submissions"

    submission_id: Mapped[str] = mapped_column(
        String(128),
        primary_key=True,
    )
    submission_payload: Mapped[dict[str, object]] = mapped_column(
        JSON,
        nullable=False,
    )
    prior_submission_id: Mapped[str | None] = mapped_column(
        ForeignKey("underwriting_submissions.submission_id"),
        nullable=True,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )


class UnderwritingDecisionRecord(Base):
    __tablename__ = "underwriting_decisions"

    decision_id: Mapped[str] = mapped_column(
        String(128),
        primary_key=True,
    )
    submission_id: Mapped[str] = mapped_column(
        ForeignKey("underwriting_submissions.submission_id"),
        nullable=False,
        index=True,
    )
    decision: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
    )
    policy_version: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    decision_payload: Mapped[dict[str, object]] = mapped_column(
        JSON,
        nullable=False,
    )
    review_status: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        index=True,
    )

    reviewer_id: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    review_comment: Mapped[str | None] = mapped_column(
        String(2_000),
        nullable=True,
    )

    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    review_modifications: Mapped[dict[str, object] | None] = mapped_column(
        JSON,
        nullable=True,
    )
    prior_decision_id: Mapped[str | None] = mapped_column(
        ForeignKey("underwriting_decisions.decision_id"),
        nullable=True,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )


class UnderwritingAuditEventRecord(Base):
    __tablename__ = "underwriting_audit_events"

    event_id: Mapped[str] = mapped_column(
        String(128),
        primary_key=True,
    )
    decision_id: Mapped[str] = mapped_column(
        ForeignKey("underwriting_decisions.decision_id"),
        nullable=False,
        index=True,
    )
    event_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
    )
    event_payload: Mapped[dict[str, object]] = mapped_column(
        JSON,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
