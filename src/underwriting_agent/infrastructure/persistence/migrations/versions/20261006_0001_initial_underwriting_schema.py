"""Create the underwriting persistence schema.

Revision ID: 20261006_0001
Revises:
Create Date: 2026-10-06
"""

import sqlalchemy as sa
from alembic import op

revision = "20261006_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "underwriting_submissions",
        sa.Column("submission_id", sa.String(length=128), primary_key=True),
        sa.Column("submission_payload", sa.JSON(), nullable=False),
        sa.Column("prior_submission_id", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["prior_submission_id"], ["underwriting_submissions.submission_id"]
        ),
    )
    op.create_index(
        "ix_underwriting_submissions_prior_submission_id",
        "underwriting_submissions",
        ["prior_submission_id"],
    )
    op.create_table(
        "underwriting_decisions",
        sa.Column("decision_id", sa.String(length=128), primary_key=True),
        sa.Column("submission_id", sa.String(length=128), nullable=False),
        sa.Column("decision", sa.String(length=64), nullable=False),
        sa.Column("policy_version", sa.String(length=64), nullable=False),
        sa.Column("decision_payload", sa.JSON(), nullable=False),
        sa.Column("review_status", sa.String(length=64), nullable=True),
        sa.Column("reviewer_id", sa.String(length=100), nullable=True),
        sa.Column("review_comment", sa.String(length=2000), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("review_modifications", sa.JSON(), nullable=True),
        sa.Column("prior_decision_id", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["submission_id"], ["underwriting_submissions.submission_id"]
        ),
        sa.ForeignKeyConstraint(
            ["prior_decision_id"], ["underwriting_decisions.decision_id"]
        ),
    )
    op.create_index(
        "ix_underwriting_decisions_submission_id",
        "underwriting_decisions",
        ["submission_id"],
    )
    op.create_index(
        "ix_underwriting_decisions_decision", "underwriting_decisions", ["decision"]
    )
    op.create_index(
        "ix_underwriting_decisions_review_status",
        "underwriting_decisions",
        ["review_status"],
    )
    op.create_index(
        "ix_underwriting_decisions_prior_decision_id",
        "underwriting_decisions",
        ["prior_decision_id"],
    )
    op.create_table(
        "underwriting_audit_events",
        sa.Column("event_id", sa.String(length=128), primary_key=True),
        sa.Column("decision_id", sa.String(length=128), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("event_payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["decision_id"], ["underwriting_decisions.decision_id"]
        ),
    )
    op.create_index(
        "ix_underwriting_audit_events_decision_id",
        "underwriting_audit_events",
        ["decision_id"],
    )
    op.create_index(
        "ix_underwriting_audit_events_event_type",
        "underwriting_audit_events",
        ["event_type"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_underwriting_audit_events_event_type",
        table_name="underwriting_audit_events",
    )
    op.drop_index(
        "ix_underwriting_audit_events_decision_id",
        table_name="underwriting_audit_events",
    )
    op.drop_table("underwriting_audit_events")
    op.drop_index(
        "ix_underwriting_decisions_prior_decision_id",
        table_name="underwriting_decisions",
    )
    op.drop_index(
        "ix_underwriting_decisions_review_status", table_name="underwriting_decisions"
    )
    op.drop_index(
        "ix_underwriting_decisions_decision", table_name="underwriting_decisions"
    )
    op.drop_index(
        "ix_underwriting_decisions_submission_id", table_name="underwriting_decisions"
    )
    op.drop_table("underwriting_decisions")
    op.drop_index(
        "ix_underwriting_submissions_prior_submission_id",
        table_name="underwriting_submissions",
    )
    op.drop_table("underwriting_submissions")
