from enum import StrEnum

from pydantic import BaseModel


class RuleSeverity(StrEnum):
    INFO = "INFO"
    REFERRAL = "REFERRAL"
    DECLINE = "DECLINE"


class RuleResult(BaseModel):
    rule_id: str
    rule_name: str
    passed: bool
    severity: RuleSeverity
    message: str
