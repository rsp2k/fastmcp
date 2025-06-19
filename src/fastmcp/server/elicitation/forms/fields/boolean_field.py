from typing import Dict, Any

from fastmcp.elicitation.forms import ValidationError
from fastmcp.elicitation.forms.fields import Field


class BooleanField(Field):
    """Boolean field."""

    def __init__(
        self,
        title:str | None,
        description: str | None,
        default: bool | None = None,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.default = default

    def to_schema(self) -> Dict[str, Any]:
        schema = {
            "type": "boolean",
            "description": self.description,
            "default": self.default,
        }

        return schema

    def validate(self, value: Any) -> None:
        value = super().validate(value)

        if value is None:
            return

        if not isinstance(value, bool):
            raise ValidationError(f"{self.name} must be a boolean")

    def clean(self, value: Any) -> Any:
        self.validate(value)
        return value
