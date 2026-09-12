from collections.abc import Callable
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from underwriting_agent.domain.audit import AuditEvent, AuditEventType
from underwriting_agent.domain.decision import UnderwritingDecision
from underwriting_agent.domain.review import (
    DecisionReview,
    DecisionReviewStatus,
    ReviewDecisionCommand,
    UnderwriterReviewAction,
)
from underwriting_agent.domain.submission import InsuranceSubmission
from underwriting_agent.infrastructure.persistence.models import (
    UnderwritingAuditEventRecord,
    UnderwritingDecisionRecord,
    UnderwritingSubmissionRecord,
)


class UnderwritingDecisionRepository:
    def __init__(
        self,
        session_factory: Callable[[], Session],
    ) -> None:
        self.session_factory = session_factory

    def save_submission_and_decision(
        self,
        submission: InsuranceSubmission,
        decision: UnderwritingDecision,
    ) -> None:
        now = datetime.now(UTC)

        review_status = (
            DecisionReviewStatus.PENDING_REVIEW
            if decision.human_review_required
            else None
        )

        with self.session_factory() as session:
            submission_record = session.get(
                UnderwritingSubmissionRecord,
                submission.submission_id,
            )

            if submission_record is None:
                submission_record = UnderwritingSubmissionRecord(
                    submission_id=submission.submission_id,
                    submission_payload=submission.model_dump(mode="json"),
                    created_at=now,
                    updated_at=now,
                )
                session.add(submission_record)
            else:
                submission_record.submission_payload = submission.model_dump(
                    mode="json",
                )
                submission_record.updated_at = now

            decision_record = UnderwritingDecisionRecord(
                decision_id=decision.decision_id,
                submission_id=submission.submission_id,
                decision=decision.decision.value,
                policy_version=decision.policy_version,
                decision_payload=decision.model_dump(mode="json"),
                review_status=(
                    review_status.value if review_status is not None else None
                ),
                reviewer_id=None,
                review_comment=None,
                reviewed_at=None,
                review_modifications=None,
                created_at=decision.created_at,
            )
            session.add(decision_record)

            submission_event = AuditEvent(
                decision_id=decision.decision_id,
                event_type=AuditEventType.SUBMISSION_PERSISTED,
                event_payload={
                    "submission_id": submission.submission_id,
                },
            )

            decision_event = AuditEvent(
                decision_id=decision.decision_id,
                event_type=AuditEventType.DECISION_CREATED,
                event_payload={
                    "decision": decision.decision.value,
                    "human_review_required": (decision.human_review_required),
                    "policy_version": decision.policy_version,
                    "evidence_retrieval_status": (
                        decision.evidence_retrieval_status.value
                    ),
                },
            )

            audit_events = [
                submission_event,
                decision_event,
            ]

            if review_status is not None:
                audit_events.append(
                    AuditEvent(
                        decision_id=decision.decision_id,
                        event_type=(AuditEventType.DECISION_REVIEW_REQUESTED),
                        event_payload={
                            "review_status": review_status.value,
                            "reason": ("human_review_required was set to true."),
                        },
                    )
                )

            session.add_all(
                [
                    UnderwritingAuditEventRecord(
                        event_id=event.event_id,
                        decision_id=event.decision_id,
                        event_type=event.event_type.value,
                        event_payload=event.event_payload,
                        created_at=event.created_at,
                    )
                    for event in audit_events
                ]
            )

            session.commit()

    def get_decision(
        self,
        decision_id: str,
    ) -> UnderwritingDecision | None:
        with self.session_factory() as session:
            decision_record = session.get(
                UnderwritingDecisionRecord,
                decision_id,
            )

            if decision_record is None:
                return None

            return UnderwritingDecision.model_validate(
                decision_record.decision_payload,
            )

    def list_decisions_by_review_status(
        self,
        review_status: DecisionReviewStatus,
    ) -> list[UnderwritingDecision]:
        with self.session_factory() as session:
            decision_records = (
                session.query(UnderwritingDecisionRecord)
                .filter(UnderwritingDecisionRecord.review_status == review_status.value)
                .order_by(UnderwritingDecisionRecord.created_at.desc())
                .all()
            )

            return [
                UnderwritingDecision.model_validate(
                    decision_record.decision_payload,
                )
                for decision_record in decision_records
            ]

    def review_decision(
        self,
        decision_id: str,
        command: ReviewDecisionCommand,
    ) -> DecisionReview:
        event_types = {
            UnderwriterReviewAction.APPROVE: (AuditEventType.UNDERWRITER_APPROVED),
            UnderwriterReviewAction.MODIFY: (AuditEventType.UNDERWRITER_MODIFIED),
            UnderwriterReviewAction.DECLINE: (AuditEventType.UNDERWRITER_DECLINED),
            UnderwriterReviewAction.REQUEST_INFORMATION: (
                AuditEventType.INFORMATION_REQUESTED
            ),
        }

        with self.session_factory() as session:
            decision_record = session.get(
                UnderwritingDecisionRecord,
                decision_id,
            )

            if decision_record is None:
                raise LookupError(f"Decision '{decision_id}' was not found.")

            if (
                decision_record.review_status
                != DecisionReviewStatus.PENDING_REVIEW.value
            ):
                raise ValueError(f"Decision '{decision_id}' is not pending review.")

            now = datetime.now(UTC)
            modifications = command.modifications

            decision_record.review_status = command.resulting_status.value
            decision_record.reviewer_id = command.reviewer_id
            decision_record.review_comment = command.comment
            decision_record.reviewed_at = now
            decision_record.review_modifications = (
                modifications.model_dump(mode="json")
                if modifications is not None
                else None
            )

            review_event = AuditEvent(
                decision_id=decision_id,
                event_type=event_types[command.action],
                event_payload={
                    "reviewer_id": command.reviewer_id,
                    "comment": command.comment,
                    "review_status": command.resulting_status.value,
                    "modifications": (
                        modifications.model_dump(mode="json")
                        if modifications is not None
                        else None
                    ),
                },
                created_at=now,
            )

            session.add(
                UnderwritingAuditEventRecord(
                    event_id=review_event.event_id,
                    decision_id=review_event.decision_id,
                    event_type=review_event.event_type.value,
                    event_payload=review_event.event_payload,
                    created_at=review_event.created_at,
                )
            )

            review = DecisionReview(
                decision_id=decision_id,
                review_status=command.resulting_status,
                reviewer_id=command.reviewer_id,
                review_comment=command.comment,
                reviewed_at=now,
                review_modifications=modifications,
            )

            session.commit()

            return review

    def list_audit_events(
        self,
        decision_id: str,
    ) -> list[AuditEvent]:
        with self.session_factory() as session:
            event_records = (
                session.query(UnderwritingAuditEventRecord)
                .filter(UnderwritingAuditEventRecord.decision_id == decision_id)
                .order_by(UnderwritingAuditEventRecord.created_at)
                .all()
            )

            return [
                AuditEvent(
                    event_id=event_record.event_id,
                    decision_id=event_record.decision_id,
                    event_type=AuditEventType(event_record.event_type),
                    event_payload=event_record.event_payload,
                    created_at=event_record.created_at,
                )
                for event_record in event_records
            ]
