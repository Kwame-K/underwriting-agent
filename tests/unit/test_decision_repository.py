import pytest
from sqlalchemy import create_engine

from underwriting_agent.domain.audit import AuditEventType
from underwriting_agent.domain.decision import UnderwritingDecision
from underwriting_agent.domain.enums import DecisionType
from underwriting_agent.domain.review import (
    DecisionReviewStatus,
    ReviewDecisionCommand,
    UnderwriterReviewAction,
)
from underwriting_agent.domain.submission import InsuranceSubmission
from underwriting_agent.infrastructure.persistence.database import (
    create_session_factory,
)
from underwriting_agent.infrastructure.persistence.models import Base
from underwriting_agent.infrastructure.repositories.decision_repository import (
    UnderwritingDecisionRepository,
)


def create_repository(
    tmp_path,
) -> UnderwritingDecisionRepository:
    database_path = tmp_path / "underwriting_test.db"

    engine = create_engine(
        f"sqlite:///{database_path}",
        connect_args={"check_same_thread": False},
    )

    Base.metadata.create_all(bind=engine)

    return UnderwritingDecisionRepository(
        session_factory=create_session_factory(engine),
    )


def create_submission(
    submission_id: str,
) -> InsuranceSubmission:
    return InsuranceSubmission(
        submission_id=submission_id,
        applicant_name="Acme Distribution Inc.",
        country="Canada",
        industry="Wholesale distribution",
        annual_revenue_cad=8_000_000,
        employee_count=45,
        mfa_enabled=False,
        prior_cyber_claims=0,
        requested_limit_cad=1_000_000,
        requested_retention_cad=25_000,
    )


def create_referred_decision(
    submission_id: str,
) -> UnderwritingDecision:
    return UnderwritingDecision(
        submission_id=submission_id,
        decision=DecisionType.REFER,
        human_review_required=True,
        reasons=["MFA is not enabled."],
        policy_version="0.5.0",
    )


def test_repository_persists_referred_decision_and_review_request(
    tmp_path,
) -> None:
    repository = create_repository(tmp_path)

    submission = create_submission("SUB-PERSIST-001")
    decision = create_referred_decision(submission.submission_id)

    repository.save_submission_and_decision(
        submission=submission,
        decision=decision,
    )

    stored_decision = repository.get_decision(
        decision_id=decision.decision_id,
    )

    audit_events = repository.list_audit_events(
        decision_id=decision.decision_id,
    )

    pending_decisions = repository.list_decisions_by_review_status(
        DecisionReviewStatus.PENDING_REVIEW,
    )

    assert stored_decision is not None
    assert stored_decision.decision_id == decision.decision_id
    assert stored_decision.decision == DecisionType.REFER

    assert [event.event_type for event in audit_events] == [
        AuditEventType.SUBMISSION_PERSISTED,
        AuditEventType.DECISION_CREATED,
        AuditEventType.DECISION_REVIEW_REQUESTED,
    ]

    assert [item.decision_id for item in pending_decisions] == [
        decision.decision_id,
    ]


@pytest.mark.parametrize(
    (
        "action",
        "modifications",
        "expected_status",
        "expected_event_type",
    ),
    [
        (
            UnderwriterReviewAction.APPROVE,
            None,
            DecisionReviewStatus.UNDERWRITER_APPROVED,
            AuditEventType.UNDERWRITER_APPROVED,
        ),
        (
            UnderwriterReviewAction.MODIFY,
            {
                "approved_limit_cad": 750_000,
                "annual_premium_cad": 18_500,
                "added_conditions": ["MFA must be enabled before policy inception."],
            },
            DecisionReviewStatus.UNDERWRITER_MODIFIED,
            AuditEventType.UNDERWRITER_MODIFIED,
        ),
        (
            UnderwriterReviewAction.DECLINE,
            None,
            DecisionReviewStatus.UNDERWRITER_DECLINED,
            AuditEventType.UNDERWRITER_DECLINED,
        ),
        (
            UnderwriterReviewAction.REQUEST_INFORMATION,
            None,
            DecisionReviewStatus.UNDERWRITER_REQUESTED_INFORMATION,
            AuditEventType.INFORMATION_REQUESTED,
        ),
    ],
)
def test_repository_records_each_review_transition(
    tmp_path,
    action: UnderwriterReviewAction,
    modifications: dict[str, object] | None,
    expected_status: DecisionReviewStatus,
    expected_event_type: AuditEventType,
) -> None:
    repository = create_repository(tmp_path)

    submission = create_submission(f"SUB-REVIEW-{action.value}")
    decision = create_referred_decision(submission.submission_id)

    repository.save_submission_and_decision(
        submission=submission,
        decision=decision,
    )

    command = ReviewDecisionCommand(
        action=action,
        reviewer_id="underwriter-001",
        comment=f"Review completed with action {action.value}.",
        modifications=modifications,
    )

    review = repository.review_decision(
        decision_id=decision.decision_id,
        command=command,
    )

    audit_events = repository.list_audit_events(
        decision_id=decision.decision_id,
    )

    pending_decisions = repository.list_decisions_by_review_status(
        DecisionReviewStatus.PENDING_REVIEW,
    )

    assert review.decision_id == decision.decision_id
    assert review.review_status == expected_status
    assert review.reviewer_id == "underwriter-001"
    assert review.review_comment == (f"Review completed with action {action.value}.")

    if action is UnderwriterReviewAction.MODIFY:
        assert review.review_modifications is not None
        assert review.review_modifications.approved_limit_cad == 750_000
        assert review.review_modifications.annual_premium_cad == 18_500
    else:
        assert review.review_modifications is None

    assert audit_events[-1].event_type == expected_event_type
    assert audit_events[-1].event_payload["reviewer_id"] == ("underwriter-001")
    assert audit_events[-1].event_payload["review_status"] == (expected_status.value)

    assert decision.decision_id not in [item.decision_id for item in pending_decisions]


def test_repository_rejects_second_review(
    tmp_path,
) -> None:
    repository = create_repository(tmp_path)

    submission = create_submission("SUB-SECOND-REVIEW-001")
    decision = create_referred_decision(submission.submission_id)

    repository.save_submission_and_decision(
        submission=submission,
        decision=decision,
    )

    approval = ReviewDecisionCommand(
        action=UnderwriterReviewAction.APPROVE,
        reviewer_id="underwriter-001",
        comment="Risk accepted as quoted.",
    )

    repository.review_decision(
        decision_id=decision.decision_id,
        command=approval,
    )

    second_review = ReviewDecisionCommand(
        action=UnderwriterReviewAction.DECLINE,
        reviewer_id="underwriter-002",
        comment="A second review must not be accepted.",
    )

    with pytest.raises(ValueError, match="is not pending review"):
        repository.review_decision(
            decision_id=decision.decision_id,
            command=second_review,
        )


def test_repository_rejects_review_for_unknown_decision(
    tmp_path,
) -> None:
    repository = create_repository(tmp_path)

    command = ReviewDecisionCommand(
        action=UnderwriterReviewAction.APPROVE,
        reviewer_id="underwriter-001",
        comment="This decision does not exist.",
    )

    with pytest.raises(LookupError, match="was not found"):
        repository.review_decision(
            decision_id="DEC-DOES-NOT-EXIST",
            command=command,
        )
