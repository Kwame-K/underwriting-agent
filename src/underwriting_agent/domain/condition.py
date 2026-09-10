from pydantic import BaseModel, Field

from underwriting_agent.domain.enums import ConditionCategory


class UnderwritingCondition(BaseModel):
    condition_id: str = Field(min_length=1)
    category: ConditionCategory
    message: str = Field(min_length=1)
