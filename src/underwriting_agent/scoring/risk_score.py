from underwriting_agent.domain.enums import RiskBand
from underwriting_agent.domain.risk_score import RiskFactor, RiskScore
from underwriting_agent.domain.submission import InsuranceSubmission


class CyberRiskScoringService:
    model_version = "0.1.0"

    def score(self, submission: InsuranceSubmission) -> RiskScore:
        factors = [
            self._base_exposure_factor(),
            self._revenue_factor(submission),
            self._employee_count_factor(submission),
            self._personal_data_factor(submission),
            self._payment_card_data_factor(submission),
            self._mfa_factor(submission),
            self._edr_factor(submission),
            self._backup_factor(submission),
            self._prior_claims_factor(submission),
            self._requested_limit_factor(submission),
        ]

        raw_score = sum(factor.points for factor in factors)
        score = min(max(raw_score, 0), 100)

        return RiskScore(
            score=score,
            risk_band=self._determine_risk_band(score),
            factors=factors,
            scoring_model_version=self.model_version,
        )

    @staticmethod
    def _base_exposure_factor() -> RiskFactor:
        return RiskFactor(
            factor_id="RSK-001",
            factor_name="Base cyber exposure",
            points=15,
            message="Base score applied to every eligible cyber SME submission.",
        )

    @staticmethod
    def _revenue_factor(submission: InsuranceSubmission) -> RiskFactor:
        revenue = submission.annual_revenue_cad or 0

        if revenue <= 1_000_000:
            points = 0
        elif revenue <= 5_000_000:
            points = 5
        elif revenue <= 20_000_000:
            points = 10
        elif revenue <= 50_000_000:
            points = 15
        else:
            points = 25

        return RiskFactor(
            factor_id="RSK-002",
            factor_name="Annual revenue exposure",
            points=points,
            message=(
                f"Annual revenue of {revenue:,.0f} CAD contributes {points} risk points."
            ),
        )

    @staticmethod
    def _employee_count_factor(
        submission: InsuranceSubmission,
    ) -> RiskFactor:
        employee_count = submission.employee_count or 0

        if employee_count <= 10:
            points = 0
        elif employee_count <= 50:
            points = 3
        elif employee_count <= 250:
            points = 5
        else:
            points = 8

        return RiskFactor(
            factor_id="RSK-003",
            factor_name="Employee count exposure",
            points=points,
            message=(
                f"Employee count of {employee_count} contributes {points} risk points."
            ),
        )

    @staticmethod
    def _personal_data_factor(
        submission: InsuranceSubmission,
    ) -> RiskFactor:
        handles_personal_data = submission.handles_personal_data is True
        points = 8 if handles_personal_data else 0

        return RiskFactor(
            factor_id="RSK-004",
            factor_name="Personal data exposure",
            points=points,
            message=(
                "The applicant handles personal data, increasing privacy and breach exposure."
                if handles_personal_data
                else "No personal data exposure was declared."
            ),
        )

    @staticmethod
    def _payment_card_data_factor(
        submission: InsuranceSubmission,
    ) -> RiskFactor:
        handles_payment_card_data = submission.handles_payment_card_data is True
        points = 12 if handles_payment_card_data else 0

        return RiskFactor(
            factor_id="RSK-005",
            factor_name="Payment card data exposure",
            points=points,
            message=(
                "The applicant handles payment card data, increasing breach exposure."
                if handles_payment_card_data
                else "No payment card data exposure was declared."
            ),
        )

    @staticmethod
    def _mfa_factor(submission: InsuranceSubmission) -> RiskFactor:
        mfa_enabled = submission.mfa_enabled is True
        points = 0 if mfa_enabled else 30

        return RiskFactor(
            factor_id="RSK-006",
            factor_name="Multi-factor authentication",
            points=points,
            message=(
                "Multi-factor authentication is enabled."
                if mfa_enabled
                else (
                    "Multi-factor authentication is not enabled, materially increasing "
                    "account takeover risk."
                )
            ),
        )

    @staticmethod
    def _edr_factor(submission: InsuranceSubmission) -> RiskFactor:
        edr_enabled = submission.endpoint_detection_response is True
        points = 0 if edr_enabled else 8

        return RiskFactor(
            factor_id="RSK-007",
            factor_name="Endpoint detection and response",
            points=points,
            message=(
                "Endpoint detection and response is deployed."
                if edr_enabled
                else "Endpoint detection and response is not confirmed or not deployed."
            ),
        )

    @staticmethod
    def _backup_factor(submission: InsuranceSubmission) -> RiskFactor:
        offline_backups = submission.offline_backups is True
        points = 0 if offline_backups else 10

        return RiskFactor(
            factor_id="RSK-008",
            factor_name="Offline backup controls",
            points=points,
            message=(
                "Offline or immutable backup controls are available."
                if offline_backups
                else "Offline or immutable backup controls are not confirmed."
            ),
        )

    @staticmethod
    def _prior_claims_factor(submission: InsuranceSubmission) -> RiskFactor:
        prior_claims = submission.prior_cyber_claims or 0
        points = min(prior_claims * 15, 30)

        return RiskFactor(
            factor_id="RSK-009",
            factor_name="Prior cyber claims",
            points=points,
            message=(
                f"{prior_claims} prior cyber claim(s) contribute {points} risk points."
            ),
        )

    @staticmethod
    def _requested_limit_factor(
        submission: InsuranceSubmission,
    ) -> RiskFactor:
        requested_limit = submission.requested_limit_cad or 0

        if requested_limit <= 500_000:
            points = 0
        elif requested_limit <= 1_000_000:
            points = 3
        elif requested_limit <= 2_000_000:
            points = 7
        else:
            points = 12

        return RiskFactor(
            factor_id="RSK-010",
            factor_name="Requested insurance limit",
            points=points,
            message=(
                f"Requested limit of {requested_limit:,.0f} CAD contributes "
                f"{points} risk points."
            ),
        )

    @staticmethod
    def _determine_risk_band(score: float) -> RiskBand:
        if score < 30:
            return RiskBand.LOW
        if score < 50:
            return RiskBand.MEDIUM
        if score < 70:
            return RiskBand.HIGH

        return RiskBand.SEVERE
