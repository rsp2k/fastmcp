from typing import Any, Dict, Optional


class Field:
    """Base field class for elicitation form fields."""

    def __init__(
        self,
        title: str = "",
        description: Optional[str] = None,
        required: bool = False,
    ):
        self.name = None  # Set by the form metaclass
        self.title = title
        self.description = description
        self.required = required

    def to_schema(self) -> Dict[str, Any]:
        """Convert field to JSON Schema representation."""
        raise NotImplementedError("Subclasses must implement to_schema()")

    def validate(self, value: Any) -> None:
        """Validate the field value, or raise ValidationError."""
        return

    def clean(self, value: Any) -> Any:
        """Clean and validate the value."""
        self.validate(value)
        return value
