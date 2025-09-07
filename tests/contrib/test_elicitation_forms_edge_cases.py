"""
Edge case and stress tests for elicitation forms contrib module.

Tests error conditions, boundary cases, and robustness.
"""
from __future__ import annotations

import pytest
from fastmcp import Context, FastMCP
from fastmcp.client.client import Client
from fastmcp.client.elicitation import ElicitResult

from fastmcp.contrib.elicitation_forms import (
    ElicitationForm,
    StringField,
    IntegerField,
    NumberField,
    BooleanField,
    EnumField,
    EnumFieldChoices,
    ValidationError,
    ElicitationError,
    ElicitationNotSupportedError,
)


class TestFieldEdgeCases:
    """Test edge cases in field validation."""

    def test_string_field_empty_string_handling(self):
        """Test StringField handling of empty strings."""
        # Required field should reject empty string
        required_field = StringField(title="Required", required=True)
        with pytest.raises(ValidationError):
            required_field.validate("")

        # Optional field should accept empty string
        optional_field = StringField(title="Optional", required=False)
        assert optional_field.validate("") == ""

        # Field with min_length should reject empty string
        min_length_field = StringField(title="MinLength", min_length=1)
        with pytest.raises(ValidationError):
            min_length_field.validate("")

    def test_string_field_whitespace_handling(self):
        """Test StringField handling of whitespace."""
        field = StringField(title="Test", min_length=3)
        
        # Whitespace should be preserved
        assert field.validate("   ") == "   "
        
        # But should still respect min_length
        with pytest.raises(ValidationError):
            field.validate("  ")  # Only 2 characters

    def test_integer_field_boundary_values(self):
        """Test IntegerField at boundary values."""
        field = IntegerField(title="Bounded", minimum=0, maximum=100)
        
        # Boundary values should work
        assert field.validate(0) == 0
        assert field.validate(100) == 100
        
        # Just outside boundaries should fail
        with pytest.raises(ValidationError):
            field.validate(-1)
        with pytest.raises(ValidationError):
            field.validate(101)

    def test_integer_field_large_numbers(self):
        """Test IntegerField with very large numbers."""
        field = IntegerField(title="Large", minimum=0)
        
        # Python handles arbitrarily large integers
        large_num = 10**100
        assert field.validate(large_num) == large_num

    def test_number_field_precision_handling(self):
        """Test NumberField with floating point precision."""
        field = NumberField(title="Precise", minimum=0.0, maximum=1.0)
        
        # Test precise decimal values
        assert field.validate(0.1234567890123456) == 0.1234567890123456
        
        # Test edge of precision
        tiny_value = 1e-15
        assert field.validate(tiny_value) == tiny_value

    def test_boolean_field_edge_case_conversions(self):
        """Test BooleanField with edge case string conversions."""
        field = BooleanField(title="Bool")
        
        # Test case variations
        assert field.validate("TRUE") is True
        assert field.validate("False") is False
        assert field.validate("YES") is True
        assert field.validate("nO") is False
        
        # Test numeric edge cases
        assert field.validate(0.0) is False
        assert field.validate(0.1) is True
        assert field.validate(-1) is True

    def test_enum_field_case_sensitivity(self):
        """Test EnumField case sensitivity."""
        
        class CaseSensitiveChoices(EnumFieldChoices):
            lower = "lower"
            UPPER = "UPPER"
            MiXeD = "MiXeD"

        field = EnumField(title="Case", choices=CaseSensitiveChoices)
        
        # Exact matches should work
        assert field.validate("lower") == "lower"
        assert field.validate("UPPER") == "UPPER"
        assert field.validate("MiXeD") == "MiXeD"
        
        # Wrong case should fail
        with pytest.raises(ValidationError):
            field.validate("LOWER")
        with pytest.raises(ValidationError):
            field.validate("upper")

    def test_field_none_and_null_handling(self):
        """Test field handling of None and null values."""
        
        # Required field should reject None
        required = StringField(title="Required", required=True)
        with pytest.raises(ValidationError):
            required.validate(None)
        
        # Optional field with default should return default for None
        optional_with_default = StringField(title="Optional", required=False, default="default")
        assert optional_with_default.validate(None) == "default"
        
        # Optional field without default should return empty string for None
        optional_no_default = StringField(title="Optional", required=False)
        assert optional_no_default.validate(None) == ""


class TestFormEdgeCases:
    """Test edge cases in form behavior."""

    def test_form_with_no_fields(self):
        """Test form with no field definitions."""
        
        class EmptyForm(ElicitationForm):
            pass  # No fields defined

        form = EmptyForm()
        assert len(form._fields) == 0
        
        schema = form._to_json_schema()
        assert schema["type"] == "object"
        assert schema["properties"] == {}
        assert "required" not in schema or schema["required"] == []

    def test_form_with_all_optional_fields(self):
        """Test form where all fields are optional."""
        
        class AllOptionalForm(ElicitationForm):
            field1 = StringField(title="Field1", required=False)
            field2 = IntegerField(title="Field2", required=False)

        form = AllOptionalForm()
        schema = form._to_json_schema()
        
        # Should have no required fields
        assert "required" not in schema or schema["required"] == []

    def test_form_field_name_conflicts(self):
        """Test handling of field names that conflict with form methods."""
        
        class ConflictForm(ElicitationForm):
            # These could potentially conflict with form methods/attributes
            elicit = StringField(title="Elicit Field")
            validate = StringField(title="Validate Field")
            message = StringField(title="Message Field")

        form = ConflictForm()
        
        # Fields should be collected properly
        assert "elicit" in form._fields
        assert "validate" in form._fields  
        assert "message" in form._fields
        
        # But form methods should still work
        assert callable(getattr(form, "elicit"))  # The method should exist
        
        # Field access through cleaned_data should work
        form.cleaned_data = {"elicit": "test", "validate": "test2", "message": "test3"}
        # Note: can't test direct attribute access since it would conflict

    def test_form_large_number_of_fields(self):
        """Test form with many fields (stress test)."""
        
        # Dynamically create a form class with many fields
        field_dict = {}
        for i in range(100):
            field_dict[f"field_{i}"] = StringField(title=f"Field {i}", required=False)
        
        # Create form class dynamically
        LargeForm = type("LargeForm", (ElicitationForm,), field_dict)
        
        form = LargeForm()
        assert len(form._fields) == 100
        
        schema = form._to_json_schema()
        assert len(schema["properties"]) == 100

    def test_form_inheritance_chain(self):
        """Test deep inheritance chain of forms."""
        
        class BaseForm(ElicitationForm):
            base_field = StringField(title="Base")

        class MiddleForm(BaseForm):
            middle_field = StringField(title="Middle")

        class TopForm(MiddleForm):
            top_field = StringField(title="Top")

        form = TopForm()
        assert len(form._fields) == 3
        assert "base_field" in form._fields
        assert "middle_field" in form._fields
        assert "top_field" in form._fields

    def test_form_field_override_in_inheritance(self):
        """Test field override behavior in inheritance."""
        
        class BaseForm(ElicitationForm):
            shared_field = StringField(title="Base Version")

        class OverrideForm(BaseForm):
            shared_field = IntegerField(title="Override Version")  # Different type

        form = OverrideForm()
        
        # Should have the overridden field
        assert isinstance(form._fields["shared_field"], IntegerField)
        assert form._fields["shared_field"].title == "Override Version"

    def test_form_with_complex_validation_combinations(self):
        """Test form with multiple complex validation scenarios."""
        
        class ComplexForm(ElicitationForm):
            username = StringField(
                title="Username",
                min_length=3,
                max_length=20,
                pattern=r"^[a-zA-Z0-9_]+$"
            )
            password = StringField(
                title="Password", 
                min_length=8,
                max_length=128
            )
            age = IntegerField(
                title="Age",
                minimum=13,
                maximum=120
            )
            score = NumberField(
                title="Score",
                minimum=0.0,
                maximum=100.0
            )

        form = ComplexForm()
        
        # Test data that fails multiple validations
        invalid_data = {
            "username": "a@",  # Too short + invalid pattern
            "password": "short",  # Too short
            "age": 12,  # Too young
            "score": 101.5  # Too high
        }
        
        with pytest.raises(ValidationError) as exc_info:
            form._validate_data(invalid_data)
        
        error_str = str(exc_info.value)
        assert "must be at least 3 characters" in error_str
        # Don't expect pattern error if length error comes first
        assert "must be at least 8 characters" in error_str
        assert "must be at least 13" in error_str
        assert "must be at most 100" in error_str
        
        # Test a separate case where we get format error
        pattern_invalid_data = {
            "username": "user@name",  # Valid length but invalid pattern
            "password": "validpassword123",
            "age": 25,
            "score": 85.5
        }
        
        with pytest.raises(ValidationError) as exc_info2:
            form._validate_data(pattern_invalid_data)
        
        error_str2 = str(exc_info2.value)
        assert "format is invalid" in error_str2


class TestErrorHandling:
    """Test error handling and exception scenarios."""

    def test_validation_error_chaining(self):
        """Test that ValidationError properly chains multiple field errors."""
        
        class MultiFieldForm(ElicitationForm):
            field1 = StringField(title="Field1", min_length=5)
            field2 = IntegerField(title="Field2", minimum=10)
            field3 = StringField(title="Field3", pattern=r"^\d+$")

        form = MultiFieldForm()
        
        invalid_data = {
            "field1": "abc",  # Too short
            "field2": 5,      # Too small
            "field3": "invalid"  # Wrong pattern
        }
        
        with pytest.raises(ValidationError) as exc_info:
            form._validate_data(invalid_data)
        
        # All errors should be included
        error_msg = str(exc_info.value)
        assert "Field1" in error_msg
        assert "Field2" in error_msg  
        assert "Field3" in error_msg

    def test_elicitation_error_inheritance(self):
        """Test that ElicitationError inherits from FastMCPError properly."""
        
        # Import to test inheritance
        from fastmcp.exceptions import FastMCPError
        
        # Test inheritance chain
        assert issubclass(ElicitationError, FastMCPError)
        assert issubclass(ValidationError, ElicitationError)
        assert issubclass(ElicitationNotSupportedError, ElicitationError)
        
        # Test instantiation
        error = ValidationError("Test validation error")
        assert isinstance(error, ValidationError)
        assert isinstance(error, ElicitationError)
        assert isinstance(error, FastMCPError)

    def test_form_handles_malformed_data(self):
        """Test form handling of malformed or unexpected data."""
        
        class SimpleForm(ElicitationForm):
            name = StringField(title="Name")
            age = IntegerField(title="Age")

        form = SimpleForm()
        
        # Test with extra fields
        data_with_extra = {
            "name": "Alice",
            "age": 30,
            "extra_field": "should be ignored",
            "another_extra": 123
        }
        
        # Should validate successfully, ignoring extra fields
        cleaned = form._validate_data(data_with_extra)
        assert cleaned == {"name": "Alice", "age": 30}
        
        # Test with missing fields
        incomplete_data = {"name": "Bob"}  # Missing age
        
        with pytest.raises(ValidationError):
            form._validate_data(incomplete_data)


class TestPerformanceAndMemory:
    """Test performance characteristics and memory usage."""

    def test_form_creation_performance(self):
        """Test that form creation is reasonably fast."""
        import time
        
        class TestForm(ElicitationForm):
            field1 = StringField(title="Field1")
            field2 = IntegerField(title="Field2")
            field3 = BooleanField(title="Field3")

        start_time = time.time()
        
        # Create many form instances
        forms = [TestForm() for _ in range(1000)]
        
        end_time = time.time()
        creation_time = end_time - start_time
        
        # Should be able to create 1000 forms in reasonable time (< 1 second)
        assert creation_time < 1.0
        assert len(forms) == 1000

    def test_schema_generation_performance(self):
        """Test that schema generation is reasonably fast."""
        import time
        
        class LargeForm(ElicitationForm):
            pass
        
        # Add many fields dynamically
        for i in range(50):
            setattr(LargeForm, f"field_{i}", StringField(title=f"Field {i}"))
        
        form = LargeForm()
        
        start_time = time.time()
        
        # Generate schema multiple times
        for _ in range(100):
            schema = form._to_json_schema()
        
        end_time = time.time()
        generation_time = end_time - start_time
        
        # Should be able to generate schema 100 times in reasonable time
        assert generation_time < 1.0

    def test_form_memory_usage(self):
        """Test that forms don't retain excessive references."""
        import gc
        import weakref
        
        class TestForm(ElicitationForm):
            field1 = StringField(title="Field1")

        form = TestForm()
        weak_ref = weakref.ref(form)
        
        # Form should be alive
        assert weak_ref() is not None
        
        # Delete strong reference
        del form
        gc.collect()
        
        # Form should be garbage collected
        assert weak_ref() is None


class TestUnicodeAndSpecialCharacters:
    """Test handling of Unicode and special characters."""

    def test_unicode_field_values(self):
        """Test fields with Unicode characters."""
        field = StringField(title="Unicode Field")
        
        # Test various Unicode characters
        unicode_values = [
            "Hello 世界",  # Chinese
            "Café ñoño",  # Spanish accents
            "🎉 emoji 🚀",  # Emojis
            "Здравствуй мир",  # Cyrillic
            "مرحبا بالعالم",  # Arabic
            "𝕌𝕟𝕚𝕔𝕠𝕕𝕖",  # Mathematical symbols
        ]
        
        for value in unicode_values:
            assert field.validate(value) == value

    def test_unicode_in_field_definitions(self):
        """Test Unicode in field titles and descriptions."""
        
        class UnicodeForm(ElicitationForm):
            名前 = StringField(
                title="お名前",  # Japanese title
                description="あなたの名前を入力してください"  # Japanese description
            )
            café = StringField(
                title="Café favorito",  # Spanish with accent
                description="¿Cuál es tu café favorito?"
            )

        form = UnicodeForm()
        schema = form._to_json_schema()
        
        # Unicode should be preserved in schema
        name_field = schema["properties"]["名前"]
        assert name_field["title"] == "お名前"
        assert name_field["description"] == "あなたの名前を入力してください"

    def test_special_characters_in_patterns(self):
        """Test regex patterns with special characters."""
        
        # Pattern for matching email addresses (complex regex)
        email_field = StringField(
            title="Email",
            pattern=r"^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$"
        )
        
        # Valid emails
        valid_emails = [
            "test@example.com",
            "user.name+tag@domain.co.uk",
            "x@y.z",
            "test123@test123.test123"
        ]
        
        for email in valid_emails:
            assert email_field.validate(email) == email
        
        # Invalid emails should fail
        invalid_emails = [
            "not-an-email",
            "@domain.com",
            "user@",
            "user@domain."  # Ends with dot, should fail
        ]
        
        for email in invalid_emails:
            with pytest.raises(ValidationError):
                email_field.validate(email)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])