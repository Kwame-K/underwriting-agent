from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from underwriting_agent.api.app import app
from underwriting_agent.api.dependencies import (
    get_decision_repository,
    get_underwriting_service,
)
from underwriting_agent.application.underwriting_service import (
    UnderwritingService,
)
from underwriting_agent.domain.audit import AuditEvent, AuditEventType
from underwriting_agent.domain.decision import UnderwritingDecision
from underwriting_agent.domain.enums import DecisionType
from underwriting_agent.domain.review import (
    DecisionReview,
    DecisionReviewStatus,
    ReviewDecisionCommand,
    UnderwriterReviewAction,
)
from underwriting_agent.domain.submission import InsuranceSubmission


class FakeDecisionRepository:
    def __init__(self) -> None:
        self.saved_submissions: list[InsuranceSubmission] = []
        self.saved_decisions: list[UnderwritingDecision] = []
        self.decisions_by_id: dict[str, UnderwritingDecision] = {}
        self.audit_events_by_decision_id: dict[str, list[AuditEvent]] = {}
        self.review_status_by_decision_id: dict[
            str,
            DecisionReviewStatus | None,
        ] = {}

    def clear(self) -> None:
        self.saved_submissions.clear()
        self.saved_decisions.clear()
        self.decisions_by_id.clear()
        self.audit_events_by_decision_id.clear()
        self.review_status_by_decision_id.clear()

    def save_submission_and_decision(
        self,
        submission: InsuranceSubmission,
        decision: UnderwritingDecision,
    ) -> None:
        self.saved_submissions.append(submission)
        self.saved_decisions.append(decision)
        self.decisions_by_id[decision.decision_id] = decision

        review_status = (
            DecisionReviewStatus.PENDING_REVIEW
            if decision.human_review_required
            else None
        )

        self.review_status_by_decision_id[decision.decision_id] = review_status

        audit_events = [
            AuditEvent(
                decision_id=decision.decision_id,
                event_type=AuditEventType.SUBMISSION_PERSISTED,
                event_payload={
                    "submission_id": submission.submission_id,
                },
            ),
            AuditEvent(
                decision_id=decision.decision_id,
                event_type=AuditEventType.DECISION_CREATED,
                event_payload={
                    "decision": decision.decision.value,
                },
            ),
        ]

        if review_status is not None:
            audit_events.append(
                AuditEvent(
                    decision_id=decision.decision_id,
                    event_type=(AuditEventType.DECISION_REVIEW_REQUESTED),
                    event_payload={
                        "review_status": review_status.value,
                    },
                )
            )

        self.audit_events_by_decision_id[decision.decision_id] = audit_events

    def get_decision(
        self,
        decision_id: str,
    ) -> UnderwritingDecision | None:
        return self.decisions_by_id.get(decision_id)

    def list_decisions_by_review_status(
        self,
        review_status: DecisionReviewStatus,
    ) -> list[UnderwritingDecision]:
        return [
            decision
            for decision_id, decision in self.decisions_by_id.items()
            if self.review_status_by_decision_id[decision_id] == review_status
        ]

    def review_decision(
        self,
        decision_id: str,
        command: ReviewDecisionCommand,
    ) -> DecisionReview:
        decision = self.decisions_by_id.get(decision_id)

        if decision is None:
            raise LookupError(f"Decision '{decision_id}' was not found.")

        if (
            self.review_status_by_decision_id[decision_id]
            != DecisionReviewStatus.PENDING_REVIEW
        ):
            raise ValueError(f"Decision '{decision_id}' is not pending review.")

        event_types = {
            UnderwriterReviewAction.APPROVE: (AuditEventType.UNDERWRITER_APPROVED),
            UnderwriterReviewAction.MODIFY: (AuditEventType.UNDERWRITER_MODIFIED),
            UnderwriterReviewAction.DECLINE: (AuditEventType.UNDERWRITER_DECLINED),
            UnderwriterReviewAction.REQUEST_INFORMATION: (
                AuditEventType.INFORMATION_REQUESTED
            ),
        }

        now = datetime.now(UTC)
        modifications = command.modifications

        self.review_status_by_decision_id[decision_id] = command.resulting_status

        self.audit_events_by_decision_id[decision_id].append(
            AuditEvent(
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
        )

        return DecisionReview(
            decision_id=decision_id,
            review_status=command.resulting_status,
            reviewer_id=command.reviewer_id,
            review_comment=command.comment,
            reviewed_at=now,
            review_modifications=modifications,
        )

    def list_audit_events(
        self,
        decision_id: str,
    ) -> list[AuditEvent]:
        return self.audit_events_by_decision_id.get(decision_id, [])


test_repository = FakeDecisionRepository()


def get_test_underwriting_service() -> UnderwritingService:
    return UnderwritingService()


def get_test_decision_repository() -> FakeDecisionRepository:
    return test_repository


app.dependency_overrides[get_underwriting_service] = get_test_underwriting_service

app.dependency_overrides[get_decision_repository] = get_test_decision_repository


client = TestClient(app)


@pytest.fixture(autouse=True)
def clear_test_repository() -> None:
    test_repository.clear()


def test_health_check_returns_ok() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_underwrite_returns_need_more_information_for_incomplete_submission() -> None:
    response = client.post(
        "/underwrite",
        json={
            "submission_id": "SUB-API-001",
            "applicant_name": "NorthStar Retail Inc.",
            "country": "Canada",
            "industry": "Retail",
            "requested_limit_cad": 1_000_000,
            "requested_retention_cad": 25_000,
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["decision"] == "NEED_MORE_INFORMATION"
    assert body["missing_information"] == [
        "annual_revenue_cad",
        "employee_count",
        "mfa_enabled",
        "prior_cyber_claims",
    ]


def test_underwrite_returns_pending_for_complete_submission() -> None:
    response = client.post(
        "/underwrite",
        json={
            "submission_id": "SUB-API-002",
            "applicant_name": "Acme Distribution Inc.",
            "country": "Canada",
            "industry": "Wholesale distribution",
            "annual_revenue_cad": 12_500_000,
            "employee_count": 85,
            "mfa_enabled": True,
            "prior_cyber_claims": 0,
            "requested_limit_cad": 1_000_000,
            "requested_retention_cad": 25_000,
        },
    )

    assert response.status_code == 200
    assert response.json()["decision"] == "PENDING_UNDERWRITING"


def test_underwrite_persists_submission_and_decision() -> None:
    initial_submission_count = len(test_repository.saved_submissions)
    initial_decision_count = len(test_repository.saved_decisions)

    response = client.post(
        "/underwrite",
        json={
            "submission_id": "SUB-API-PERSIST-001",
            "applicant_name": "Acme Distribution Inc.",
            "country": "Canada",
            "industry": "Wholesale distribution",
            "annual_revenue_cad": 8_000_000,
            "employee_count": 45,
            "mfa_enabled": True,
            "prior_cyber_claims": 0,
            "requested_limit_cad": 1_000_000,
            "requested_retention_cad": 25_000,
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["decision_id"].startswith("DEC-")
    assert len(test_repository.saved_submissions) == (initial_submission_count + 1)
    assert len(test_repository.saved_decisions) == (initial_decision_count + 1)

    persisted_submission = test_repository.saved_submissions[-1]
    persisted_decision = test_repository.saved_decisions[-1]

    assert persisted_submission.submission_id == "SUB-API-PERSIST-001"
    assert persisted_decision.decision_id == body["decision_id"]


def test_get_decision_returns_persisted_decision() -> None:
    create_response = client.post(
        "/underwrite",
        json={
            "submission_id": "SUB-GET-DECISION-001",
            "applicant_name": "Acme Distribution Inc.",
            "country": "Canada",
            "industry": "Wholesale distribution",
            "annual_revenue_cad": 8_000_000,
            "employee_count": 45,
            "mfa_enabled": True,
            "prior_cyber_claims": 0,
            "requested_limit_cad": 1_000_000,
            "requested_retention_cad": 25_000,
        },
    )

    assert create_response.status_code == 200

    decision_id = create_response.json()["decision_id"]

    response = client.get(f"/decisions/{decision_id}")

    assert response.status_code == 200
    assert response.json()["decision_id"] == decision_id
    assert response.json()["submission_id"] == "SUB-GET-DECISION-001"


def test_get_decision_returns_404_for_unknown_decision() -> None:
    response = client.get("/decisions/DEC-DOES-NOT-EXIST")

    assert response.status_code == 404
    assert response.json() == {"detail": "Decision 'DEC-DOES-NOT-EXIST' was not found."}


def test_get_audit_trail_returns_persisted_events() -> None:
    create_response = client.post(
        "/underwrite",
        json={
            "submission_id": "SUB-GET-AUDIT-001",
            "applicant_name": "Acme Distribution Inc.",
            "country": "Canada",
            "industry": "Wholesale distribution",
            "annual_revenue_cad": 8_000_000,
            "employee_count": 45,
            "mfa_enabled": True,
            "prior_cyber_claims": 0,
            "requested_limit_cad": 1_000_000,
            "requested_retention_cad": 25_000,
        },
    )

    assert create_response.status_code == 200

    decision_id = create_response.json()["decision_id"]

    response = client.get(f"/decisions/{decision_id}/audit-trail")

    assert response.status_code == 200

    audit_events = response.json()

    assert [event["event_type"] for event in audit_events] == [
        "SUBMISSION_PERSISTED",
        "DECISION_CREATED",
    ]

    assert audit_events[0]["decision_id"] == decision_id
    assert audit_events[0]["event_payload"] == {
        "submission_id": "SUB-GET-AUDIT-001",
    }


def test_get_audit_trail_returns_404_for_unknown_decision() -> None:
    response = client.get("/decisions/DEC-DOES-NOT-EXIST/audit-trail")

    assert response.status_code == 404
    assert response.json() == {"detail": "Decision 'DEC-DOES-NOT-EXIST' was not found."}


def create_pending_review_decision() -> UnderwritingDecision:
    submission = InsuranceSubmission(
        submission_id="SUB-API-REVIEW-001",
        applicant_name="Acme Distribution Inc.",
        country="Canada",
        industry="Wholesale distribution",
        annual_revenue_cad=8_000_000,
        employee_count=45,
        mfa_enabled=False,
        prior_cyber_claims=1,
        requested_limit_cad=1_000_000,
        requested_retention_cad=25_000,
    )

    decision = UnderwritingDecision(
        submission_id=submission.submission_id,
        decision=DecisionType.REFER,
        human_review_required=True,
        reasons=["MFA is not enabled."],
        policy_version="0.5.0",
    )

    test_repository.save_submission_and_decision(
        submission=submission,
        decision=decision,
    )

    return decision


def test_list_pending_review_decisions() -> None:
    decision = create_pending_review_decision()

    response = client.get(
        "/decisions?status=PENDING_REVIEW",
    )

    assert response.status_code == 200

    body = response.json()

    assert len(body) == 1
    assert body[0]["decision_id"] == decision.decision_id
    assert body[0]["decision"] == "REFER"
    assert body[0]["human_review_required"] is True


@pytest.mark.parametrize(
    (
        "action",
        "modifications",
        "expected_status",
        "expected_event_type",
    ),
    [
        (
            "APPROVE",
            None,
            "UNDERWRITER_APPROVED",
            "UNDERWRITER_APPROVED",
        ),
        (
            "MODIFY",
            {
                "approved_limit_cad": 750_000,
                "annual_premium_cad": 18_500,
                "added_conditions": ["MFA must be enabled before policy inception."],
            },
            "UNDERWRITER_MODIFIED",
            "UNDERWRITER_MODIFIED",
        ),
        (
            "DECLINE",
            None,
            "UNDERWRITER_DECLINED",
            "UNDERWRITER_DECLINED",
        ),
        (
            "REQUEST_INFORMATION",
            None,
            "UNDERWRITER_REQUESTED_INFORMATION",
            "INFORMATION_REQUESTED",
        ),
    ],
)
def test_review_decision_records_each_human_action(
    action: str,
    modifications: dict[str, object] | None,
    expected_status: str,
    expected_event_type: str,
) -> None:
    decision = create_pending_review_decision()

    payload: dict[str, object] = {
        "action": action,
        "reviewer_id": "underwriter-001",
        "comment": f"Review completed with action {action}.",
    }

    if modifications is not None:
        payload["modifications"] = modifications

    response = client.post(
        f"/decisions/{decision.decision_id}/review",
        json=payload,
    )

    assert response.status_code == 200

    body = response.json()

    assert body["decision_id"] == decision.decision_id
    assert body["review_status"] == expected_status
    assert body["reviewer_id"] == "underwriter-001"

    if action == "MODIFY":
        assert body["review_modifications"] == {
            "approved_limit_cad": 750_000,
            "retention_cad": None,
            "annual_premium_cad": 18_500,
            "added_conditions": ["MFA must be enabled before policy inception."],
            "removed_conditions": [],
        }
    else:
        assert body["review_modifications"] is None

    pending_response = client.get(
        "/decisions?status=PENDING_REVIEW",
    )

    assert pending_response.status_code == 200
    assert pending_response.json() == []

    audit_response = client.get(
        f"/decisions/{decision.decision_id}/audit-trail",
    )

    assert audit_response.status_code == 200
    assert audit_response.json()[-1]["event_type"] == (expected_event_type)


def test_review_decision_returns_404_for_unknown_decision() -> None:
    response = client.post(
        "/decisions/DEC-DOES-NOT-EXIST/review",
        json={
            "action": "APPROVE",
            "reviewer_id": "underwriter-001",
            "comment": "Risk accepted.",
        },
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Decision 'DEC-DOES-NOT-EXIST' was not found."}


def test_review_decision_returns_409_after_first_review() -> None:
    decision = create_pending_review_decision()

    first_response = client.post(
        f"/decisions/{decision.decision_id}/review",
        json={
            "action": "APPROVE",
            "reviewer_id": "underwriter-001",
            "comment": "Risk accepted.",
        },
    )

    assert first_response.status_code == 200

    second_response = client.post(
        f"/decisions/{decision.decision_id}/review",
        json={
            "action": "DECLINE",
            "reviewer_id": "underwriter-002",
            "comment": "A second review must fail.",
        },
    )

    assert second_response.status_code == 409
    assert second_response.json() == {
        "detail": (f"Decision '{decision.decision_id}' is not pending review.")
    }
