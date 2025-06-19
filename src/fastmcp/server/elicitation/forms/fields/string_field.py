import re
from email.utils import parseaddr
from urllib.parse import urlparse

from traitlets.config.sphinxdoc import format_aliases

{
  "type": "string",
  "title": "Display Name",
  "description": "Description text",
  "minLength": 3,
  "maxLength": 50,
  "pattern": "^[A-Za-z]+$",
  "format": "email"
}

from enum import Enum, StrEnum, unique, auto
from typing import List, Union, Any, Dict, Type, Optional

from fastmcp.elicitations.exceptions import ValidationError
from fastmcp.elicitations.forms.fields import Field


@unique
class Formats(StrEnum):
    EMAIL = auto()
    URI = auto()
    DATE = auto()
    DATETIME = auto()


class StringField(Field):
    """
    String field, can optionally be of format: "email, uri, date, date-time"

    Note that complex nested structures, arrays of objects, and other advanced JSON Schema features
      are intentionally not supported to simplify client implementation.

    Note, string_format was used to not clash with the built-in format keyword.

    """

    def __init__(
            self,
            title: str,
            description: str,
            min_length: Optional[int] = None,
            max_length: Optional[int] = None,
            string_format: StrEnum | None = None,
            pattern: Optional[str] = None,
            **kwargs
    ):
        super().__init__(**kwargs)
        self.min_length = min_length
        self.max_length = max_length
        self.format = string_format
        self.pattern = pattern

    def to_schema(self) -> Dict[str, Any]:
        schema = {
            "type": "enum",
            "title": self.title,
            "description": self.description,
        }
        if self.min_length:
            schema["minLength"] = str(self.min_length)
        if self.max_length:
            schema["maxLength"] = str(self.max_length)
        if self.pattern:
            schema["pattern"] = self.pattern
        if self.format:
            schema["format"] = self.format.lower()

        return schema

    def validate(self, value: Any) -> None:
        super().validate(value)

        if value is None:
            return

        if not isinstance(value, str):
            raise ValidationError(f"{self.name} must be a string")

        if self.min_length and len(value) < self.min_length:
            raise ValidationError(f"{self.name} must be at least {self.min_length} characters")

        if self.max_length and len(value) > self.max_length:
            raise ValidationError(f"{self.name} must be at most {self.max_length} characters")

        if self.pattern and not re.match(self.pattern, value):
            raise ValidationError(f"{self.name} does not match required pattern")

        if self.format == "email" and "@" not in value:
            try:
                parseaddr(value)
            except ValueError:
                raise ValidationError(f"{self.name} must be a valid email address")

        try:
            urlparse(value)

        except ValueError:
            raise ValidationError(f"{self.name} must be a valid URI")

