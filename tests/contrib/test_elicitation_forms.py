"""
Comprehensive tests for the elicitation forms contrib module.

Tests the field-based elicitation forms that provide a Django-style API
for creating rich elicitation forms with FastMCP.
"""

from __future__ import annotations

import pytest

from fastmcp import Context, FastMCP
from fastmcp.client.client import Client
from fastmcp.client.elicitation import ElicitResult
from fastmcp.contrib.elicitation_forms import (
    BooleanField,
    ElicitationForm,
    EnumField,
    EnumFieldChoices,
    IntegerField,
    NumberField,
    StringField,
    ValidationError,
)


class TestFieldValidation:
    """Test individual field validation logic."""

    def test_string_field_validation(self):
        """Test StringField validation with various constraints."""
        field = StringField(
            title="Test String",
            description="A test field",
            min_length=3,
            max_length=10,
            required=True,
        )

        # Valid cases
        assert field.validate("hello") == "hello"
        assert field.validate("test") == "test"

        # Invalid cases
        with pytest.raises(ValidationError, match="must be at least 3 characters"):
            field.validate("hi")

        with pytest.raises(ValidationError, match="must be at most 10 characters"):
            field.validate("this is too long")

        with pytest.raises(ValidationError, match="is required"):
            field.validate(None)

        with pytest.raises(ValidationError, match="must be a string"):
            field.validate(123)

    def test_string_field_with_choices(self):
        """Test StringField with predefined choices."""
        field = StringField(
            title="Color Choice",
            description="Pick a color",
            choices=["red", "green", "blue"],
        )

        # Valid choice
        assert field.validate("red") == "red"

        # Invalid choice
        with pytest.raises(ValidationError, match="must be one of: red, green, blue"):
            field.validate("yellow")

    def test_string_field_with_pattern(self):
        """Test StringField with regex pattern validation."""
        field = StringField(
            title="Email",
            description="Enter email",
            pattern=r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$",
        )

        # Valid email
        assert field.validate("test@example.com") == "test@example.com"

        # Invalid email
        with pytest.raises(ValidationError, match="format is invalid"):
            field.validate("invalid-email")

    def test_integer_field_validation(self):
        """Test IntegerField validation with ranges."""
        field = IntegerField(
            title="Age", description="Your age", minimum=0, maximum=150
        )

        # Valid cases
        assert field.validate(25) == 25
        assert field.validate("30") == 30  # String conversion

        # Invalid cases
        with pytest.raises(ValidationError, match="must be at least 0"):
            field.validate(-5)

        with pytest.raises(ValidationError, match="must be at most 150"):
            field.validate(200)

        with pytest.raises(ValidationError, match="must be an integer"):
            field.validate("not a number")

    def test_number_field_validation(self):
        """Test NumberField validation with decimals."""
        field = NumberField(
            title="Price", description="Item price", minimum=0.0, maximum=999.99
        )

        # Valid cases
        assert field.validate(19.99) == 19.99
        assert field.validate("25.50") == 25.50
        assert field.validate(100) == 100.0

        # Invalid cases
        with pytest.raises(ValidationError, match="must be at least 0"):
            field.validate(-1.0)

        with pytest.raises(ValidationError, match="must be at most 999.99"):
            field.validate(1500.00)

    def test_boolean_field_validation(self):
        """Test BooleanField validation and conversion."""
        field = BooleanField(title="Subscribe", description="Subscribe to newsletter")

        # Valid cases
        assert field.validate(True) is True
        assert field.validate(False) is False
        assert field.validate("true") is True
        assert field.validate("false") is False
        assert field.validate("1") is True
        assert field.validate("0") is False
        assert field.validate("yes") is True
        assert field.validate("no") is False
        assert field.validate(1) is True
        assert field.validate(0) is False

        # Invalid cases
        with pytest.raises(ValidationError, match="must be true or false"):
            field.validate("maybe")

    def test_enum_field_validation(self):
        """Test EnumField validation with custom choices."""

        class PriorityChoices(EnumFieldChoices):
            LOW = "low"
            MEDIUM = "medium"
            HIGH = "high"

        field = EnumField(
            title="Priority", description="Task priority", choices=PriorityChoices
        )

        # Valid choices
        assert field.validate("low") == "low"
        assert field.validate("medium") == "medium"

        # Invalid choice
        with pytest.raises(ValidationError, match="must be one of: LOW, MEDIUM, HIGH"):
            field.validate("urgent")

    def test_field_defaults_and_optional(self):
        """Test field default values and optional behavior."""
        field = StringField(
            title="Optional Field",
            description="Not required",
            required=False,
            default="default_value",
        )

        # Should return default for None
        assert field.validate(None) == "default_value"

        # Should accept provided value
        assert field.validate("custom") == "custom"


class TestFormDefinition:
    """Test form definition and schema generation."""

    def test_form_metaclass_field_collection(self):
        """Test that metaclass properly collects field definitions."""

        class TestChoices(EnumFieldChoices):
            OPTION_A = "a"
            OPTION_B = "b"

        class TestForm(ElicitationForm):
            name = StringField(title="Name", description="Your name", min_length=1)
            age = IntegerField(title="Age", description="Your age", minimum=0)
            active = BooleanField(
                title="Active", description="Are you active?", default=True
            )
            choice = EnumField(
                title="Choice", description="Pick one", choices=TestChoices
            )

        form = TestForm()

        # Check that fields were collected
        assert len(form._fields) == 4
        assert "name" in form._fields
        assert "age" in form._fields
        assert "active" in form._fields
        assert "choice" in form._fields

        # Check field types
        assert isinstance(form._fields["name"], StringField)
        assert isinstance(form._fields["age"], IntegerField)
        assert isinstance(form._fields["active"], BooleanField)
        assert isinstance(form._fields["choice"], EnumField)

    def test_form_json_schema_generation(self):
        """Test JSON schema generation from form fields."""

        class TestForm(ElicitationForm):
            required_field = StringField(
                title="Required",
                description="A required field",
                min_length=1,
                max_length=50,
            )
            optional_field = IntegerField(
                title="Optional",
                description="An optional field",
                required=False,
                minimum=0,
                maximum=100,
                default=0,
            )

        form = TestForm()
        schema = form._to_json_schema()

        # Check top-level structure
        assert schema["type"] == "object"
        assert "properties" in schema
        assert "required" in schema

        # Check required fields
        assert schema["required"] == ["required_field"]

        # Check properties
        props = schema["properties"]
        assert "required_field" in props
        assert "optional_field" in props

        # Check StringField schema
        str_prop = props["required_field"]
        assert str_prop["type"] == "string"
        assert str_prop["title"] == "Required"
        assert str_prop["description"] == "A required field"
        assert str_prop["minLength"] == 1
        assert str_prop["maxLength"] == 50

        # Check IntegerField schema
        int_prop = props["optional_field"]
        assert int_prop["type"] == "integer"
        assert int_prop["title"] == "Optional"
        assert int_prop["minimum"] == 0
        assert int_prop["maximum"] == 100
        assert int_prop["default"] == 0

    def test_form_with_enum_choices(self):
        """Test form schema with enum field choices."""

        class StatusChoices(EnumFieldChoices):
            ACTIVE = "active"
            INACTIVE = "inactive"
            PENDING = "pending"

        class StatusForm(ElicitationForm):
            status = EnumField(
                title="Status", description="Current status", choices=StatusChoices
            )

        form = StatusForm()
        schema = form._to_json_schema()

        status_prop = schema["properties"]["status"]
        assert "enum" in status_prop
        assert status_prop["enum"] == ["active", "inactive", "pending"]
        assert "enumNames" in status_prop
        assert status_prop["enumNames"] == ["Active", "Inactive", "Pending"]

    def test_form_data_validation(self):
        """Test form data validation across multiple fields."""

        class UserForm(ElicitationForm):
            name = StringField(title="Name", min_length=2, max_length=50)
            age = IntegerField(title="Age", minimum=0, maximum=150)
            email = StringField(title="Email", pattern=r"^[^@]+@[^@]+\.[^@]+$")

        form = UserForm()

        # Valid data
        valid_data = {"name": "John Doe", "age": 30, "email": "john@example.com"}
        cleaned = form._validate_data(valid_data)
        assert cleaned == valid_data

        # Invalid data - multiple errors
        invalid_data = {
            "name": "J",  # Too short
            "age": 200,  # Too high
            "email": "not-an-email",  # Invalid format
        }

        with pytest.raises(ValidationError) as exc_info:
            form._validate_data(invalid_data)

        error_msg = str(exc_info.value)
        assert "must be at least 2 characters" in error_msg
        assert "must be at most 150" in error_msg
        assert "format is invalid" in error_msg


class TestFormElicitationIntegration:
    """Test integration with FastMCP elicitation system."""

    def test_basic_form_elicitation(self):
        """Test basic form elicitation with accept/decline/cancel."""

        class NameForm(ElicitationForm):
            name = StringField(
                title="Your Name",
                description="Please enter your full name",
                min_length=1,
            )

            def on_accepted(self, data):
                return f"Hello {data['name']}!"

            def on_declined(self):
                return "No problem!"

        mcp = FastMCP("TestServer")

        @mcp.tool
        async def get_name(ctx: Context) -> str:
            form = NameForm(message="Please tell me your name")
            result = await form.elicit(ctx)

            if result.accepted and result.data is not None:
                return f"Got name: {result.data['name']}"
            elif result.declined:
                return "User declined"
            else:
                return "User cancelled"

        # Test accept
        async def accept_handler(message, response_type, params, ctx):
            return ElicitResult(action="accept", content={"name": "Alice"})

        async def test_accept():
            async with Client(mcp, elicitation_handler=accept_handler) as client:
                result = await client.call_tool("get_name")
                assert result.data == "Got name: Alice"

        # Test decline
        async def decline_handler(message, response_type, params, ctx):
            return ElicitResult(action="decline")

        async def test_decline():
            async with Client(mcp, elicitation_handler=decline_handler) as client:
                result = await client.call_tool("get_name")
                assert result.data == "User declined"

        # Test cancel
        async def cancel_handler(message, response_type, params, ctx):
            return ElicitResult(action="cancel")

        async def test_cancel():
            async with Client(mcp, elicitation_handler=cancel_handler) as client:
                result = await client.call_tool("get_name")
                assert result.data == "User cancelled"

        # Run the tests (manually since we can't await in test functions)
        import asyncio

        asyncio.run(test_accept())
        asyncio.run(test_decline())
        asyncio.run(test_cancel())

    def test_form_chaining(self):
        """Test chaining multiple forms in sequence."""

        class PersonInfoForm(ElicitationForm):
            name = StringField(title="Name", description="Your name")
            age = IntegerField(title="Age", description="Your age", minimum=0)

        class ConfirmationForm(ElicitationForm):
            confirm = BooleanField(
                title="Confirm",
                description="Is this information correct?",
                default=True,
            )

        mcp = FastMCP("TestServer")

        @mcp.tool
        async def collect_person_info(ctx: Context) -> str:
            # First form - collect info
            info_form = PersonInfoForm(message="Please provide your information")
            info_result = await info_form.elicit(ctx)

            if not info_result.accepted or info_result.data is None:
                return "Information collection cancelled"

            name = info_result.data["name"]
            age = info_result.data["age"]

            # Second form - confirm info
            confirm_form = ConfirmationForm(
                message=f"You entered: {name}, age {age}. Is this correct?"
            )
            confirm_result = await confirm_form.elicit(ctx)

            if (
                confirm_result.accepted
                and confirm_result.data is not None
                and confirm_result.data["confirm"]
            ):
                return f"Confirmed: {name} is {age} years old"
            else:
                return "Information not confirmed"

        call_count = 0

        async def chaining_handler(message, response_type, params, ctx):
            nonlocal call_count
            call_count += 1

            if call_count == 1:
                # First call - provide person info
                return ElicitResult(action="accept", content={"name": "Bob", "age": 25})
            elif call_count == 2:
                # Second call - confirm
                return ElicitResult(action="accept", content={"confirm": True})
            else:
                raise ValueError("Unexpected call")

        async def test_chaining():
            async with Client(mcp, elicitation_handler=chaining_handler) as client:
                result = await client.call_tool("collect_person_info")
                assert result.data == "Confirmed: Bob is 25 years old"
                assert call_count == 2

        import asyncio

        asyncio.run(test_chaining())

    def test_validation_error_handling(self):
        """Test handling of validation errors in elicitation."""

        class StrictForm(ElicitationForm):
            email = StringField(
                title="Email",
                description="Valid email address",
                pattern=r"^[^@]+@[^@]+\.[^@]+$",
            )
            age = IntegerField(title="Age", minimum=18, maximum=100)

        mcp = FastMCP("TestServer")

        @mcp.tool
        async def validate_input(ctx: Context) -> str:
            form = StrictForm(message="Enter valid information")
            try:
                result = await form.elicit(ctx)
                if result.accepted:
                    return f"Valid: {result.data}"
                else:
                    return "Not accepted"
            except ValidationError as e:
                return f"Validation error: {e}"

        # Test with invalid data
        async def invalid_handler(message, response_type, params, ctx):
            return ElicitResult(
                action="accept",
                content={
                    "email": "not-an-email",  # Invalid
                    "age": 15,  # Too young
                },
            )

        async def test_validation_error():
            async with Client(mcp, elicitation_handler=invalid_handler) as client:
                result = await client.call_tool("validate_input")
                assert "Validation error" in result.data
                assert "format is invalid" in result.data
                assert "must be at least 18" in result.data

        import asyncio

        asyncio.run(test_validation_error())

    def test_graceful_fallback_when_elicitation_not_supported(self):
        """Test graceful handling when client doesn't support elicitation."""

        class SimpleForm(ElicitationForm):
            message_text = StringField(title="Message", description="Enter a message")

        mcp = FastMCP("TestServer")

        @mcp.tool
        async def try_elicit(ctx: Context) -> str:
            form = SimpleForm(message="Please enter a message")
            try:
                result = await form.elicit(ctx)
                return f"Got: {result.data}"
            except Exception as e:
                # Should gracefully handle elicitation not supported
                return f"Elicitation failed: {type(e).__name__}"

        # Test without elicitation handler (simulates unsupported client)
        async def test_fallback():
            async with Client(mcp) as client:  # No elicitation handler
                result = await client.call_tool("try_elicit")
                assert "Elicitation failed" in result.data
                assert "ElicitationNotSupportedError" in result.data

        import asyncio

        asyncio.run(test_fallback())


class TestFieldSchemaGeneration:
    """Test that field schemas match FastMCP elicitation requirements."""

    def test_string_field_schema_completeness(self):
        """Test StringField generates complete JSON schema."""
        field = StringField(
            title="Test Field",
            description="A test string field",
            min_length=3,
            max_length=20,
            pattern=r"^[a-zA-Z]+$",
            default="test",
        )

        schema = field.to_schema_property()

        assert schema == {
            "type": "string",
            "title": "Test Field",
            "description": "A test string field",
            "minLength": 3,
            "maxLength": 20,
            "pattern": r"^[a-zA-Z]+$",
            "default": "test",
        }

    def test_integer_field_schema_completeness(self):
        """Test IntegerField generates complete JSON schema."""
        field = IntegerField(
            title="Count",
            description="Number of items",
            minimum=1,
            maximum=100,
            default=10,
        )

        schema = field.to_schema_property()

        assert schema == {
            "type": "integer",
            "title": "Count",
            "description": "Number of items",
            "minimum": 1,
            "maximum": 100,
            "default": 10,
        }

    def test_number_field_schema_completeness(self):
        """Test NumberField generates complete JSON schema."""
        field = NumberField(
            title="Price", description="Item price in USD", minimum=0.01, maximum=999.99
        )

        schema = field.to_schema_property()

        assert schema == {
            "type": "number",
            "title": "Price",
            "description": "Item price in USD",
            "minimum": 0.01,
            "maximum": 999.99,
        }

    def test_boolean_field_schema_completeness(self):
        """Test BooleanField generates complete JSON schema."""
        field = BooleanField(title="Active", description="Is active?", default=False)

        schema = field.to_schema_property()

        assert schema == {
            "type": "boolean",
            "title": "Active",
            "description": "Is active?",
            "default": False,
        }

    def test_enum_field_schema_completeness(self):
        """Test EnumField generates complete JSON schema with choices."""

        class StatusChoices(EnumFieldChoices):
            DRAFT = "draft"
            PUBLISHED = "published"
            ARCHIVED = "archived"

        field = EnumField(
            title="Status",
            description="Document status",
            choices=StatusChoices,
            default="draft",
        )

        schema = field.to_schema_property()

        assert schema == {
            "title": "Status",
            "description": "Document status",
            "default": "draft",
            "enum": ["draft", "published", "archived"],
            "enumNames": ["Draft", "Published", "Archived"],
        }


class TestEventHandlers:
    """Test form event handlers (on_accepted, on_declined, on_canceled)."""

    def test_event_handler_execution(self):
        """Test that event handlers are called correctly."""
        handler_calls = []

        class TestForm(ElicitationForm):
            name = StringField(title="Name", description="Your name")

            def on_accepted(self, data):
                handler_calls.append(("accepted", data))
                return f"Hello {data['name']}!"

            def on_declined(self):
                handler_calls.append(("declined", None))
                return "Goodbye!"

            def on_canceled(self):
                handler_calls.append(("canceled", None))
                return "Maybe later!"

        # Note: Event handlers are called internally by the form.elicit() method
        # This test verifies the handler definitions are correct
        form = TestForm()

        # Test handler definitions exist and are callable
        assert hasattr(form, "on_accepted")
        assert callable(form.on_accepted)
        assert hasattr(form, "on_declined")
        assert callable(form.on_declined)
        assert hasattr(form, "on_canceled")
        assert callable(form.on_canceled)

        # Test handlers can be called directly
        result = form.on_accepted({"name": "Test"})
        assert result == "Hello Test!"
        assert handler_calls == [("accepted", {"name": "Test"})]

    def test_async_event_handlers(self):
        """Test that async event handlers work correctly."""

        class AsyncForm(ElicitationForm):
            message_text = StringField(title="Message", description="Enter message")

            async def on_accepted(self, data):
                # Simulate async operation
                import asyncio

                await asyncio.sleep(0.01)
                return f"Processed: {data['message_text']}"

        form = AsyncForm()

        # Verify async handler exists
        assert hasattr(form, "on_accepted")
        import inspect

        assert inspect.iscoroutinefunction(form.on_accepted)


def test_field_inheritance_and_composition():
    """Test that fields can be inherited and composed properly."""

    class BaseChoices(EnumFieldChoices):
        OPTION_1 = "opt1"
        OPTION_2 = "opt2"

    class BaseForm(ElicitationForm):
        name = StringField(title="Name", description="Base name field")
        choice = EnumField(title="Choice", choices=BaseChoices)

    class ExtendedForm(BaseForm):
        email = StringField(title="Email", description="Email address")
        age = IntegerField(title="Age", minimum=0)

    # Test that extended form has all fields
    extended = ExtendedForm()
    assert len(extended._fields) == 4
    assert "name" in extended._fields
    assert "choice" in extended._fields
    assert "email" in extended._fields
    assert "age" in extended._fields

    # Test schema generation works with inheritance
    schema = extended._to_json_schema()
    assert len(schema["properties"]) == 4
    assert all(
        field in schema["properties"] for field in ["name", "choice", "email", "age"]
    )


def test_form_field_access():
    """Test accessing field values through form instance."""

    class TestForm(ElicitationForm):
        name = StringField(title="Name", default="default_name")
        count = IntegerField(title="Count", default=5)

    form = TestForm()

    # Test default value access
    assert form.name == "default_name"
    assert form.count == 5

    # Test setting cleaned data
    form.cleaned_data = {"name": "Alice", "count": 10}
    assert form.name == "Alice"
    assert form.count == 10

    # Test accessing non-existent field raises AttributeError
    with pytest.raises(AttributeError):
        _ = form.nonexistent_field


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
