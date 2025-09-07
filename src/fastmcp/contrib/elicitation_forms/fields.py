"""
Field types for FastMCP elicitation forms.

Based on the original vision from /home/rpm/NOW/fastmcp/src/fastmcp/server/elicitation/README.md
"""
from __future__ import annotations

import re
from abc import ABC, abstractmethod
from enum import StrEnum
from typing import TYPE_CHECKING, Any

from .exceptions import ValidationError

if TYPE_CHECKING:
    from collections.abc import Sequence


class BaseField(ABC):
    """Base class for all elicitation form fields."""
    
    def __init__(
        self,
        title: str,
        description: str = "",
        required: bool = True,
        default: Any = None,
        **kwargs
    ):
        self.title = title
        self.description = description
        self.required = required
        self.default = default
        self.extra_kwargs = kwargs
        self._value = default
        
    @abstractmethod
    def to_schema_property(self) -> dict[str, Any]:
        """Convert field to JSON schema property."""
        pass
    
    @abstractmethod 
    def validate(self, value: Any) -> Any:
        """Validate and clean the field value."""
        pass
    
    def get_base_schema(self) -> dict[str, Any]:
        """Get base schema properties common to all fields."""
        schema = {}
        if self.title:
            schema["title"] = self.title
        if self.description:
            schema["description"] = self.description
        if self.default is not None:
            schema["default"] = self.default
        return schema


class StringField(BaseField):
    """String field for text input."""
    
    def __init__(
        self,
        title: str,
        description: str = "",
        required: bool = True,
        default: str | None = None,
        min_length: int | None = None,
        max_length: int | None = None,
        pattern: str | None = None,
        choices: Sequence[str] | None = None,
        **kwargs
    ):
        super().__init__(title, description, required, default, **kwargs)
        self.min_length = min_length
        self.max_length = max_length
        self.pattern = pattern
        self.choices = choices
        
    def to_schema_property(self) -> dict[str, Any]:
        """Convert to JSON schema string property."""
        schema = self.get_base_schema()
        schema["type"] = "string"
        
        if self.min_length is not None:
            schema["minLength"] = self.min_length
        if self.max_length is not None:
            schema["maxLength"] = self.max_length
        if self.pattern:
            schema["pattern"] = self.pattern
        if self.choices:
            schema["enum"] = self.choices
            
        return schema
    
    def validate(self, value: Any) -> str:
        """Validate string value."""
        if value is None:
            if self.required:
                raise ValidationError(f"{self.title} is required")
            return self.default or ""
            
        if not isinstance(value, str):
            raise ValidationError(f"{self.title} must be a string")
            
        if self.min_length is not None and len(value) < self.min_length:
            raise ValidationError(f"{self.title} must be at least {self.min_length} characters")
            
        if self.max_length is not None and len(value) > self.max_length:
            raise ValidationError(f"{self.title} must be at most {self.max_length} characters")
            
        if self.pattern and not re.match(self.pattern, value):
            raise ValidationError(f"{self.title} format is invalid")
            
        if self.choices and value not in self.choices:
            raise ValidationError(f"{self.title} must be one of: {', '.join(self.choices)}")
            
        return value


class IntegerField(BaseField):
    """Integer field for whole number input."""
    
    def __init__(
        self,
        title: str,
        description: str = "",
        required: bool = True,
        default: int | None = None,
        minimum: int | None = None,
        maximum: int | None = None,
        **kwargs
    ):
        super().__init__(title, description, required, default, **kwargs)
        self.minimum = minimum
        self.maximum = maximum
        
    def to_schema_property(self) -> dict[str, Any]:
        """Convert to JSON schema integer property."""
        schema = self.get_base_schema()
        schema["type"] = "integer"
        
        if self.minimum is not None:
            schema["minimum"] = self.minimum
        if self.maximum is not None:
            schema["maximum"] = self.maximum
            
        return schema
    
    def validate(self, value: Any) -> int:
        """Validate integer value."""
        if value is None:
            if self.required:
                raise ValidationError(f"{self.title} is required")
            return self.default or 0
            
        if not isinstance(value, int):
            try:
                value = int(value)
            except (ValueError, TypeError):
                raise ValidationError(f"{self.title} must be an integer")
                
        if self.minimum is not None and value < self.minimum:
            raise ValidationError(f"{self.title} must be at least {self.minimum}")
            
        if self.maximum is not None and value > self.maximum:
            raise ValidationError(f"{self.title} must be at most {self.maximum}")
            
        return value


class NumberField(BaseField):
    """Number field for decimal input."""
    
    def __init__(
        self,
        title: str,
        description: str = "",
        required: bool = True,
        default: float | None = None,
        minimum: float | None = None,
        maximum: float | None = None,
        **kwargs
    ):
        super().__init__(title, description, required, default, **kwargs)
        self.minimum = minimum
        self.maximum = maximum
        
    def to_schema_property(self) -> dict[str, Any]:
        """Convert to JSON schema number property."""
        schema = self.get_base_schema()
        schema["type"] = "number"
        
        if self.minimum is not None:
            schema["minimum"] = self.minimum
        if self.maximum is not None:
            schema["maximum"] = self.maximum
            
        return schema
    
    def validate(self, value: Any) -> float:
        """Validate number value."""
        if value is None:
            if self.required:
                raise ValidationError(f"{self.title} is required")
            return self.default or 0.0
            
        if not isinstance(value, (int, float)):
            try:
                value = float(value)
            except (ValueError, TypeError):
                raise ValidationError(f"{self.title} must be a number")
                
        if self.minimum is not None and value < self.minimum:
            raise ValidationError(f"{self.title} must be at least {self.minimum}")
            
        if self.maximum is not None and value > self.maximum:
            raise ValidationError(f"{self.title} must be at most {self.maximum}")
            
        return float(value)


class BooleanField(BaseField):
    """Boolean field for true/false input."""
    
    def __init__(
        self,
        title: str,
        description: str = "",
        required: bool = True,
        default: bool | None = None,
        **kwargs
    ):
        super().__init__(title, description, required, default, **kwargs)
        
    def to_schema_property(self) -> dict[str, Any]:
        """Convert to JSON schema boolean property."""
        schema = self.get_base_schema()
        schema["type"] = "boolean"
        return schema
    
    def validate(self, value: Any) -> bool:
        """Validate boolean value."""
        if value is None:
            if self.required:
                raise ValidationError(f"{self.title} is required")
            return self.default or False
            
        if not isinstance(value, bool):
            # Try to convert common truthy/falsy values
            if isinstance(value, str):
                if value.lower() in ('true', '1', 'yes', 'on'):
                    return True
                elif value.lower() in ('false', '0', 'no', 'off'):
                    return False
            elif isinstance(value, (int, float)):
                return bool(value)
                
            raise ValidationError(f"{self.title} must be true or false")
            
        return value


class EnumFieldChoices(StrEnum):
    """Base class for enum field choices."""
    pass


class EnumField(BaseField):
    """Enum field for selecting from predefined choices."""
    
    def __init__(
        self,
        title: str,
        description: str = "",
        required: bool = True,
        default: str | None = None,
        choices: type[EnumFieldChoices] | None = None,
        **kwargs
    ):
        super().__init__(title, description, required, default, **kwargs)
        self.choices = choices
        
    def to_schema_property(self) -> dict[str, Any]:
        """Convert to JSON schema enum property."""
        schema = self.get_base_schema()
        
        if self.choices:
            # Use enum values
            schema["enum"] = [choice.value for choice in self.choices]
            # Add enumNames for better UI display
            schema["enumNames"] = [choice.name.replace('_', ' ').title() for choice in self.choices]
        else:
            schema["type"] = "string"
            
        return schema
    
    def validate(self, value: Any) -> str:
        """Validate enum value."""
        if value is None:
            if self.required:
                raise ValidationError(f"{self.title} is required")
            return self.default or ""
            
        if not isinstance(value, str):
            raise ValidationError(f"{self.title} must be a string")
            
        if self.choices:
            valid_values = [choice.value for choice in self.choices]
            if value not in valid_values:
                valid_names = [choice.name for choice in self.choices]
                raise ValidationError(f"{self.title} must be one of: {', '.join(valid_names)}")
                
        return value