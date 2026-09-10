from pydantic import BaseModel


class CompletenessResult(BaseModel):
    is_complete: bool
    critical_missing_fields: list[str]
    non_critical_missing_fields: list[str]

    @property
    def all_missing_fields(self) -> list[str]:
        return [
            *self.critical_missing_fields,
            *self.non_critical_missing_fields,
        ]
