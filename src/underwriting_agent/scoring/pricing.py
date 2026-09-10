from math import sqrt

from underwriting_agent.domain.policy import PricingPolicy
from underwriting_agent.domain.pricing import PricingFactor, PricingIndication
from underwriting_agent.domain.risk_score import RiskScore
from underwriting_agent.domain.submission import InsuranceSubmission


class CyberPricingIndicationService:
    def __init__(self, pricing_policy: PricingPolicy) -> None:
        self.pricing_policy = pricing_policy

    def calculate(
        self,
        submission: InsuranceSubmission,
        risk_score: RiskScore,
    ) -> PricingIndication:
        annual_revenue_cad = submission.annual_revenue_cad or 0
        requested_limit_cad = submission.requested_limit_cad or 0
        requested_retention_cad = submission.requested_retention_cad or 0

        base_exposure_premium_cad = max(
            self.pricing_policy.minimum_premium_cad,
            annual_revenue_cad * self.pricing_policy.base_rate,
        )

        limit_factor = requested_limit_cad / self.pricing_policy.reference_limit_cad
        retention_factor = self._calculate_retention_factor(
            requested_retention_cad=requested_retention_cad,
        )
        risk_band_multiplier = self.pricing_policy.risk_band_multipliers[
            risk_score.risk_band
        ]

        raw_indicated_premium_cad = (
            base_exposure_premium_cad
            * limit_factor
            * retention_factor
            * risk_band_multiplier
        )

        indicated_premium_cad = max(
            self.pricing_policy.minimum_premium_cad,
            round(raw_indicated_premium_cad, 2),
        )

        factors = [
            self._base_exposure_factor(
                annual_revenue_cad=annual_revenue_cad,
                base_exposure_premium_cad=base_exposure_premium_cad,
            ),
            self._limit_factor(
                requested_limit_cad=requested_limit_cad,
                limit_factor=limit_factor,
            ),
            self._risk_band_factor(
                risk_band=risk_score.risk_band.value,
                risk_band_multiplier=risk_band_multiplier,
            ),
            self._retention_factor(
                requested_retention_cad=requested_retention_cad,
                retention_factor=retention_factor,
            ),
        ]

        return PricingIndication(
            base_exposure_premium_cad=round(base_exposure_premium_cad, 2),
            indicated_premium_cad=indicated_premium_cad,
            requested_limit_cad=requested_limit_cad,
            requested_retention_cad=requested_retention_cad,
            risk_band=risk_score.risk_band,
            factors=factors,
            pricing_model_version=self.pricing_policy.pricing_model_version,
        )

    def _calculate_retention_factor(
        self,
        requested_retention_cad: float,
    ) -> float:
        raw_factor = sqrt(
            self.pricing_policy.reference_retention_cad / requested_retention_cad
        )

        bounded_factor = min(
            max(
                raw_factor,
                self.pricing_policy.minimum_retention_factor,
            ),
            self.pricing_policy.maximum_retention_factor,
        )

        return round(bounded_factor, 4)

    def _base_exposure_factor(
        self,
        annual_revenue_cad: float,
        base_exposure_premium_cad: float,
    ) -> PricingFactor:
        return PricingFactor(
            factor_id="PRC-001",
            factor_name="Base exposure premium",
            multiplier=1.0,
            message=(
                f"Annual revenue of {annual_revenue_cad:,.0f} CAD produces a base "
                f"exposure premium of {base_exposure_premium_cad:,.2f} CAD."
            ),
        )

    def _limit_factor(
        self,
        requested_limit_cad: float,
        limit_factor: float,
    ) -> PricingFactor:
        return PricingFactor(
            factor_id="PRC-002",
            factor_name="Requested limit factor",
            multiplier=round(limit_factor, 4),
            message=(
                f"Requested limit of {requested_limit_cad:,.0f} CAD applies a "
                f"{limit_factor:.4f} limit multiplier."
            ),
        )

    def _risk_band_factor(
        self,
        risk_band: str,
        risk_band_multiplier: float,
    ) -> PricingFactor:
        return PricingFactor(
            factor_id="PRC-003",
            factor_name="Risk band multiplier",
            multiplier=risk_band_multiplier,
            message=(
                f"Risk band {risk_band} applies a "
                f"{risk_band_multiplier:.4f} pricing multiplier."
            ),
        )

    def _retention_factor(
        self,
        requested_retention_cad: float,
        retention_factor: float,
    ) -> PricingFactor:
        return PricingFactor(
            factor_id="PRC-004",
            factor_name="Retention factor",
            multiplier=retention_factor,
            message=(
                f"Requested retention of {requested_retention_cad:,.0f} CAD applies "
                f"a {retention_factor:.4f} retention multiplier."
            ),
        )
