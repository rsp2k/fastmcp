from typing import Dict, Any, Optional

from fastmcp.elicitation import ValidationError
from fastmcp.elicitation.forms.fields import NumberField


class IntegerField(NumberField):
    """
    Integer field with optional min/max validation.

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
        schema = super().to_schema()
        schema["type"] = "integer"
        return schema

    def validate(self, value: Any) -> None:
        if not isinstance(value, int):
            raise ValidationError(f"{self.name} must be a integer")

        super().validate(value)
