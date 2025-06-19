from enum import Enum, StrEnum, unique
from typing import List, Union, Any, Dict, Type

from fastmcp.elicitation import TextChoices
from fastmcp.elicitation.forms import ValidationError
from fastmcp.elicitation.forms.fields import Field


@unique
class EnumFieldChoices(TextChoices):
    pass


class EnumField(Field):
    """
    Enum field with predefined choices.

    Note that complex nested structures, arrays of objects, and other advanced JSON Schema features
      are intentionally not supported to simplify client implementation.

    """

    def __init__(self, choices: Type[EnumFieldChoices], **kwargs):
        super().__init__(**kwargs)
        self.choices = choices

    def to_schema(self) -> Dict[str, Any]:
        enum = {member.value: member.name for member in self.choices}
        names = {member.name: member.value for member in self.choices}

        schema = {
            "type": "enum",
            "title": self.title,
            "description": self.description,
            "enum": enum,
            "enumNames": names,
        }

        return schema

    def validate(self, value: Any) -> None:
        super().validate(value)

        if value is None and not self.required:
            return

        if value not in self.choices:
            raise ValidationError(f"{self.name} must be one of {self.choices}")
