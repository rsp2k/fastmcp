"""
FastMCP Elicitation Forms - Main form class that bridges field API to FastMCP elicitation.

This implements your original vision from the design notes, adapted to work with 
FastMCP's actual elicitation infrastructure.
"""
from __future__ import annotations

import inspect
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from fastmcp import Context
from fastmcp.utilities.logging import get_logger

from .exceptions import ElicitationError, ElicitationNotSupportedError, ValidationError
from .fields import BaseField

if TYPE_CHECKING:
    from collections.abc import Callable

logger = get_logger(__name__)


@dataclass
class ElicitationResult:
    """Result of an elicitation request."""
    action: str  # "accept", "decline", "cancel"
    data: dict[str, Any] | None = None
    form: ElicitationForm | None = None
    
    @property
    def accepted(self) -> bool:
        return self.action == "accept"
    
    @property 
    def declined(self) -> bool:
        return self.action == "decline"
    
    @property
    def cancelled(self) -> bool:
        return self.action == "cancel"
    
    @property
    def declined_or_cancelled(self) -> bool:
        return self.action in ("decline", "cancel")


class ElicitationFormMeta(type):
    """Metaclass that collects field definitions from class attributes."""
    
    def __new__(mcs, name, bases, namespace):
        # Collect fields from class definition
        fields = {}
        
        # Get fields from parent classes
        for base in bases:
            if hasattr(base, '_fields'):
                fields.update(base._fields)
        
        # Get fields from current class
        for key, value in namespace.items():
            if isinstance(value, BaseField):
                fields[key] = value
        
        # Store fields and remove them from class namespace
        # (they'll be accessed through _fields instead)
        for field_name in fields.keys():
            namespace.pop(field_name, None)
        
        namespace['_fields'] = fields
        return super().__new__(mcs, name, bases, namespace)


class ElicitationForm(metaclass=ElicitationFormMeta):
    """
    Base class for creating elicitation forms using field definitions.
    
    Based on your original design vision, this provides a Django-style
    field API that bridges to FastMCP's elicitation system.
    
    Example:
        class UserInfoForm(ElicitationForm):
            name = StringField(
                title="Your name",
                description="Please enter your full name"
            )
            age = IntegerField(
                title="Your age", 
                minimum=0,
                maximum=150
            )
            
            def on_accepted(self, data):
                print(f"Hello {data.name}, age {data.age}!")
                return f"Welcome {data.name}!"
            
            def on_declined(self):
                return "Maybe next time!"
    """
    
    def __init__(self, message: str = "", **field_overrides: Any):
        """
        Initialize form with optional message and field overrides.
        
        Args:
            message: Message to show when eliciting
            **field_overrides: Override field values/properties
        """
        # Initialize cleaned_data first to avoid recursion in __setattr__
        super().__setattr__('cleaned_data', {})
        super().__setattr__('_field_overrides', field_overrides)
        super().__setattr__('message', message)
        
        # Apply field overrides
        for field_name, overrides in field_overrides.items():
            if field_name in self._fields:
                field = self._fields[field_name]
                for attr, value in overrides.items():
                    setattr(field, attr, value)
    
    async def elicit(
        self, 
        ctx: Context, 
        message: str | None = None
    ) -> ElicitationResult:
        """
        Elicit user input using this form.
        
        Args:
            ctx: FastMCP context
            message: Override form message
            
        Returns:
            ElicitationResult with action and data
        """
        elicit_message = message or self.message or "Please fill out the form"
        
        try:
            # Convert fields to JSON schema
            schema = self._to_json_schema()
            
            # Use FastMCP's low-level elicitation with custom schema
            result = await ctx.session.elicit(
                message=elicit_message,
                requestedSchema=schema,
                related_request_id=ctx.request_id,
            )
            
            if result.action == "accept" and result.content:
                # Validate and clean the data
                try:
                    cleaned_data = self._validate_data(result.content)
                    self.cleaned_data = cleaned_data
                    
                    # Call on_accepted handler if defined
                    handler_result = await self._call_handler('on_accepted', cleaned_data)
                    
                    return ElicitationResult(
                        action="accept",
                        data=cleaned_data,
                        form=self
                    )
                    
                except ValidationError as e:
                    logger.error(f"Form validation failed: {e}")
                    # Re-raise as ElicitationError to distinguish from field validation
                    raise ValidationError(str(e)) from e
                    
            elif result.action == "decline":
                # Call on_declined handler if defined  
                handler_result = await self._call_handler('on_declined')
                
                return ElicitationResult(action="decline", form=self)
                
            else:  # cancel
                # Call on_canceled handler if defined
                handler_result = await self._call_handler('on_canceled')
                
                return ElicitationResult(action="cancel", form=self)
        
        except ValidationError:
            # Let ValidationError bubble up to the tool for handling
            raise
                
        except Exception as e:
            logger.error(f"Elicitation failed: {e}")
            
            # Check if it's an elicitation support issue
            if "elicit" in str(e).lower() or "not supported" in str(e).lower():
                raise ElicitationNotSupportedError(
                    f"Client doesn't support elicitation: {e}"
                ) from e
            else:
                raise ElicitationError(f"Elicitation failed: {e}") from e
    
    def _to_json_schema(self) -> dict[str, Any]:
        """Convert form fields to JSON schema for MCP elicitation."""
        properties = {}
        required = []
        
        for field_name, field in self._fields.items():
            properties[field_name] = field.to_schema_property()
            if field.required:
                required.append(field_name)
        
        schema = {
            "type": "object",
            "properties": properties
        }
        
        if required:
            schema["required"] = required
            
        return schema
    
    def _validate_data(self, data: dict[str, Any]) -> dict[str, Any]:
        """Validate form data using field validators."""
        cleaned_data = {}
        errors = []
        
        for field_name, field in self._fields.items():
            try:
                value = data.get(field_name)
                cleaned_value = field.validate(value)
                cleaned_data[field_name] = cleaned_value
            except ValidationError as e:
                errors.append(f"{field_name}: {e}")
        
        if errors:
            raise ValidationError("; ".join(errors))
            
        return cleaned_data
    
    async def _call_handler(
        self, 
        handler_name: str, 
        *args, **kwargs
    ) -> Any:
        """Call form event handler if defined."""
        handler = getattr(self, handler_name, None)
        if handler and callable(handler):
            if inspect.iscoroutinefunction(handler):
                return await handler(*args, **kwargs)
            else:
                return handler(*args, **kwargs)
        return None
    
    # Event handlers - override in subclasses
    def on_accepted(self, data: dict[str, Any]) -> Any:
        """Called when user accepts the form with data."""
        pass
    
    def on_declined(self) -> Any:
        """Called when user declines the form."""
        pass
    
    def on_canceled(self) -> Any:
        """Called when user cancels the form."""
        pass
    
    # Convenience methods for accessing field values
    def __getattr__(self, name: str) -> Any:
        """Allow accessing cleaned data as form.field_name."""
        # Avoid recursion during initialization
        if name in ('cleaned_data', '_fields', '_field_overrides'):
            raise AttributeError(f"'{self.__class__.__name__}' has no attribute '{name}'")
        
        cleaned_data = super().__getattribute__('cleaned_data')
        if name in cleaned_data:
            return cleaned_data[name]
        
        fields = super().__getattribute__('_fields')
        if name in fields:
            return fields[name].default
            
        raise AttributeError(f"'{self.__class__.__name__}' has no attribute '{name}'")
    
    def __setattr__(self, name: str, value: Any) -> None:
        """Allow setting field values as form.field_name = value."""
        # During initialization, set attributes directly
        if not hasattr(self, 'cleaned_data') or name in ('cleaned_data', '_fields', '_field_overrides', 'message'):
            super().__setattr__(name, value)
            return
            
        # After initialization, check if it's a field
        if hasattr(self, '_fields') and name in self._fields:
            self.cleaned_data[name] = value
        else:
            super().__setattr__(name, value)