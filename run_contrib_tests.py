#!/usr/bin/env python3
"""
Manual test runner for elicitation forms contrib module.

Since we can't install FastMCP in this environment, this script manually
sets up the path and runs targeted tests.
"""

from __future__ import annotations

import sys

# Add the FastMCP source to Python path
sys.path.insert(0, "/home/rpm/fastmcp/src")


def test_field_validation():
    """Test basic field validation without FastMCP dependencies."""
    print("🧪 Testing field validation...")

    try:
        from fastmcp.contrib.elicitation_forms.exceptions import ValidationError
        from fastmcp.contrib.elicitation_forms.fields import (
            BooleanField,
            EnumField,
            EnumFieldChoices,
            IntegerField,
            StringField,
        )

        # Test StringField
        string_field = StringField(
            title="Test String", description="A test field", min_length=3, max_length=10
        )

        assert string_field.validate("hello") == "hello"
        print("✅ StringField basic validation works")

        try:
            string_field.validate("hi")
            assert False, "Should have failed validation"
        except ValidationError:
            print("✅ StringField min_length validation works")

        # Test IntegerField
        int_field = IntegerField(title="Age", minimum=0, maximum=150)

        assert int_field.validate(25) == 25
        assert int_field.validate("30") == 30  # String conversion
        print("✅ IntegerField validation and conversion works")

        try:
            int_field.validate(-5)
            assert False, "Should have failed validation"
        except ValidationError:
            print("✅ IntegerField range validation works")

        # Test BooleanField
        bool_field = BooleanField(title="Subscribe")

        assert bool_field.validate(True) is True
        assert bool_field.validate("false") is False
        assert bool_field.validate("1") is True
        assert bool_field.validate(0) is False
        print("✅ BooleanField conversion works")

        # Test EnumField
        class TestChoices(EnumFieldChoices):
            OPTION_A = "option_a"
            OPTION_B = "option_b"

        enum_field = EnumField(title="Choice", choices=TestChoices)

        assert enum_field.validate("option_a") == "option_a"
        print("✅ EnumField validation works")

        try:
            enum_field.validate("invalid")
            assert False, "Should have failed validation"
        except ValidationError:
            print("✅ EnumField invalid choice rejection works")

        return True

    except Exception as e:
        print(f"❌ Field validation test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_form_definition():
    """Test form definition and schema generation."""
    print("\n🧪 Testing form definition...")

    try:
        from fastmcp.contrib.elicitation_forms import (
            BooleanField,
            ElicitationForm,
            EnumField,
            EnumFieldChoices,
            IntegerField,
            StringField,
        )

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

        # Check field collection
        assert len(form._fields) == 4
        assert all(
            field in form._fields for field in ["name", "age", "active", "choice"]
        )
        print("✅ Form field collection works")

        # Check field types
        assert isinstance(form._fields["name"], StringField)
        assert isinstance(form._fields["age"], IntegerField)
        assert isinstance(form._fields["active"], BooleanField)
        assert isinstance(form._fields["choice"], EnumField)
        print("✅ Field types preserved correctly")

        # Test schema generation
        schema = form._to_json_schema()
        assert schema["type"] == "object"
        assert "properties" in schema
        assert "required" in schema

        # Check properties
        props = schema["properties"]
        assert len(props) == 4
        assert "name" in props
        assert "age" in props
        assert "active" in props
        assert "choice" in props

        # Check required fields (active is not required due to default)
        required = schema["required"]
        assert "name" in required
        assert "age" in required
        assert "choice" in required
        print("✅ JSON schema generation works")

        # Check specific field schemas
        name_prop = props["name"]
        assert name_prop["type"] == "string"
        assert name_prop["title"] == "Name"
        assert name_prop["minLength"] == 1

        choice_prop = props["choice"]
        assert "enum" in choice_prop
        assert choice_prop["enum"] == ["a", "b"]
        assert "enumNames" in choice_prop
        print("✅ Field-specific schemas correct")

        return True

    except Exception as e:
        print(f"❌ Form definition test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_form_validation():
    """Test form data validation."""
    print("\n🧪 Testing form validation...")

    try:
        from fastmcp.contrib.elicitation_forms import (
            ElicitationForm,
            IntegerField,
            StringField,
            ValidationError,
        )

        class UserForm(ElicitationForm):
            name = StringField(title="Name", min_length=2, max_length=50)
            age = IntegerField(title="Age", minimum=0, maximum=150)

        form = UserForm()

        # Valid data
        valid_data = {"name": "John Doe", "age": 30}
        cleaned = form._validate_data(valid_data)
        assert cleaned == valid_data
        print("✅ Valid data passes validation")

        # Invalid data
        invalid_data = {
            "name": "J",  # Too short
            "age": 200,  # Too high
        }

        try:
            form._validate_data(invalid_data)
            assert False, "Should have failed validation"
        except ValidationError as e:
            error_str = str(e)
            assert "must be at least 2 characters" in error_str
            assert "must be at most 150" in error_str
            print("✅ Invalid data properly rejected with multiple errors")

        return True

    except Exception as e:
        print(f"❌ Form validation test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_form_inheritance():
    """Test form inheritance."""
    print("\n🧪 Testing form inheritance...")

    try:
        from fastmcp.contrib.elicitation_forms import (
            ElicitationForm,
            EnumField,
            EnumFieldChoices,
            IntegerField,
            StringField,
        )

        class BaseChoices(EnumFieldChoices):
            OPTION_1 = "opt1"
            OPTION_2 = "opt2"

        class BaseForm(ElicitationForm):
            name = StringField(title="Name")
            choice = EnumField(title="Choice", choices=BaseChoices)

        class ExtendedForm(BaseForm):
            email = StringField(title="Email")
            age = IntegerField(title="Age")

        extended = ExtendedForm()
        assert len(extended._fields) == 4
        assert all(
            field in extended._fields for field in ["name", "choice", "email", "age"]
        )
        print("✅ Form inheritance works correctly")

        schema = extended._to_json_schema()
        assert len(schema["properties"]) == 4
        print("✅ Inherited form schema generation works")

        return True

    except Exception as e:
        print(f"❌ Form inheritance test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_event_handlers():
    """Test form event handlers."""
    print("\n🧪 Testing event handlers...")

    try:
        from fastmcp.contrib.elicitation_forms import ElicitationForm, StringField

        handler_calls = []

        class TestForm(ElicitationForm):
            name = StringField(title="Name")

            def on_accepted(self, data):
                handler_calls.append(("accepted", data))
                return f"Hello {data['name']}!"

            def on_declined(self):
                handler_calls.append(("declined", None))
                return "Goodbye!"

            def on_canceled(self):
                handler_calls.append(("canceled", None))
                return "Maybe later!"

        form = TestForm()

        # Test handler existence
        assert hasattr(form, "on_accepted") and callable(form.on_accepted)
        assert hasattr(form, "on_declined") and callable(form.on_declined)
        assert hasattr(form, "on_canceled") and callable(form.on_canceled)
        print("✅ Event handlers defined correctly")

        # Test handler execution
        result = form.on_accepted({"name": "Test"})
        assert result == "Hello Test!"
        assert handler_calls == [("accepted", {"name": "Test"})]
        print("✅ Event handlers execute correctly")

        return True

    except Exception as e:
        print(f"❌ Event handler test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_edge_cases():
    """Test edge cases and error conditions."""
    print("\n🧪 Testing edge cases...")

    try:
        from fastmcp.contrib.elicitation_forms import (
            ElicitationForm,
            StringField,
        )

        # Empty form
        class EmptyForm(ElicitationForm):
            pass

        empty_form = EmptyForm()
        assert len(empty_form._fields) == 0
        schema = empty_form._to_json_schema()
        assert schema["properties"] == {}
        print("✅ Empty form handled correctly")

        # Unicode handling
        unicode_field = StringField(title="Unicode Field")
        unicode_values = ["Hello 世界", "Café ñoño", "🎉 emoji 🚀", "Здравствуй мир"]

        for value in unicode_values:
            assert unicode_field.validate(value) == value
        print("✅ Unicode handling works")

        # Large number handling
        from fastmcp.contrib.elicitation_forms import IntegerField

        large_field = IntegerField(title="Large")
        large_num = 10**100
        assert large_field.validate(large_num) == large_num
        print("✅ Large number handling works")

        return True

    except Exception as e:
        print(f"❌ Edge case test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_rpn_forms():
    """Test RPN-specific forms."""
    print("\n🧪 Testing RPN forms...")

    try:
        # Import the RPN server forms
        sys.path.insert(0, "/home/rpm/rpn-mcp/src")
        from rpn_mcp_server.server import (
            HelpTopicChoices,
            OutputFormatChoices,
            RPNErrorCorrectionForm,
            RPNHelpRequestForm,
            RPNPreferencesForm,
            SkillLevelChoices,
        )

        # Test RPNErrorCorrectionForm
        error_form = RPNErrorCorrectionForm()
        schema = error_form._to_json_schema()

        assert "corrected_code" in schema["properties"]
        assert "learn_more" in schema["properties"]
        assert schema["required"] == ["corrected_code"]

        code_field = schema["properties"]["corrected_code"]
        assert code_field["type"] == "string"
        assert code_field["minLength"] == 1
        assert code_field["maxLength"] == 500
        print("✅ RPNErrorCorrectionForm schema correct")

        # Test RPNPreferencesForm
        prefs_form = RPNPreferencesForm()
        prefs_schema = prefs_form._to_json_schema()

        expected_fields = ["precision", "output_format", "show_stack", "auto_print"]
        for field in expected_fields:
            assert field in prefs_schema["properties"]

        # Check enum field
        format_field = prefs_schema["properties"]["output_format"]
        assert "enum" in format_field
        assert set(format_field["enum"]) == {"decimal", "fraction", "scientific"}
        print("✅ RPNPreferencesForm schema correct")

        # Test RPNHelpRequestForm
        help_form = RPNHelpRequestForm()
        help_schema = help_form._to_json_schema()

        topic_field = help_schema["properties"]["help_topic"]
        assert "enum" in topic_field
        expected_topics = {
            "basic_operations",
            "stack_operations",
            "advanced_math",
            "precision_control",
            "memory_operations",
            "examples",
        }
        assert set(topic_field["enum"]).issuperset(expected_topics)
        print("✅ RPNHelpRequestForm schema correct")

        # Test enum choices
        assert OutputFormatChoices.DECIMAL == "decimal"
        assert SkillLevelChoices.BEGINNER == "beginner"
        assert HelpTopicChoices.BASIC_OPERATIONS == "basic_operations"
        print("✅ RPN enum choices work correctly")

        return True

    except Exception as e:
        print(f"❌ RPN forms test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("🚀 Running Elicitation Forms Contrib Module Tests")
    print("=" * 60)

    tests = [
        test_field_validation,
        test_form_definition,
        test_form_validation,
        test_form_inheritance,
        test_event_handlers,
        test_edge_cases,
        test_rpn_forms,
    ]

    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"❌ Test {test.__name__} crashed: {e}")
            results.append(False)

    print("\n" + "=" * 60)
    passed = sum(results)
    total = len(results)

    if passed == total:
        print(f"🎉 All {total} tests passed! Contrib module is working correctly.")
        return 0
    else:
        print(f"❌ {passed}/{total} tests passed. Some issues need to be fixed.")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
