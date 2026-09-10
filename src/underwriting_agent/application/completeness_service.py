from underwriting_agent.domain.completeness import CompletenessResult
from underwriting_agent.domain.submission import InsuranceSubmission


class CompletenessChecker:
    critical_fields = (
        "applicant_name",
        "country",
        "industry",
        "annual_revenue_cad",
        "employee_count",
        "mfa_enabled",
        "prior_cyber_claims",
        "requested_limit_cad",
        "requested_retention_cad",
    )

    non_critical_fields = (
        "province",
        "handles_personal_data",
        "handles_payment_card_data",
        "endpoint_detection_response",
        "offline_backups",
    )

    def check(self, submission: InsuranceSubmission) -> CompletenessResult:
        critical_missing_fields = self._get_missing_fields(
            submission=submission,
            field_names=self.critical_fields,
        )
        non_critical_missing_fields = self._get_missing_fields(
            submission=submission,
            field_names=self.non_critical_fields,
        )

        return CompletenessResult(
            is_complete=not critical_missing_fields,
            critical_missing_fields=critical_missing_fields,
            non_critical_missing_fields=non_critical_missing_fields,
        )

    @staticmethod
    def _get_missing_fields(
        submission: InsuranceSubmission,
        field_names: tuple[str, ...],
    ) -> list[str]:
        return [
            field_name
            for field_name in field_names
            if getattr(submission, field_name) is None
        ]
