from typing import Dict, Any, Optional

from fastmcp.elicitation.forms import ValidationError
from fastmcp.elicitation.forms import Field


class NumberField(Field):
    """
    Number field with optional min/max validation.
    Accepts "1" and "1.1"
    """

    def __init__(
        self,
        minimum: Optional[float] = None,
        maximum: Optional[float] = None,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.minimum = minimum
        self.maximum = maximum

    def to_schema(self) -> Dict[str, Any]:
        schema = {"type": "number"}

        if self.minimum is not None:
            schema["minimum"] = str(self.minimum)
        if self.maximum is not None:
            schema["maximum"] = str(self.maximum)

        return schema

    def validate(self, value: Any) -> None:
        super().validate(value)

        if value is None:
            return

        if not isinstance(value, (int, float)):
            raise ValidationError(f"{self.name} must be a number")

        if self.minimum is not None and value < self.minimum:
            raise ValidationError(f"{self.name} must be at least {self.minimum}")

        if self.maximum is not None and value > self.maximum:
            raise ValidationError(f"{self.name} must be at most {self.maximum}")
