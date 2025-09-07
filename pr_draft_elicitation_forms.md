# Add Elicitation Forms contrib module

This PR adds a Django-style field API for MCP elicitation workflows. The elicitation forms provide a clean, declarative way to create interactive forms that integrate with FastMCP's native elicitation system.

While FastMCP supports elicitation through `ctx.elicit()`, building complex forms required manual schema construction and validation. This contribution provides a field-based API that auto-generates JSON schemas and handles validation.

## Usage Example

```python
from fastmcp.contrib.elicitation_forms import ElicitationForm, StringField, IntegerField

class UserForm(ElicitationForm):
    name = StringField(title="Name", min_length=1, max_length=50)
    age = IntegerField(title="Age", minimum=0, maximum=150)
    
    def on_accepted(self, data):
        return f"Hello {data['name']}, age {data['age']}!"

# In a tool
@server.tool
async def register_user(ctx: Context) -> str:
    form = UserForm()
    result = await form.elicit(ctx, "Please provide your details")
    
    if result.accepted:
        return f"Registered: {result.data}"
    else:
        return "Registration cancelled"
```

## Field Types

- **StringField**: Text validation with min/max length, regex patterns, choices
- **IntegerField**: Numeric validation with min/max bounds
- **NumberField**: Float validation with precision control
- **BooleanField**: True/false with flexible string conversion
- **EnumField**: Type-safe choices with custom enum classes

## FastMCP Integration

Forms automatically convert to MCP JSON schemas and integrate with `ctx.session.elicit()`. Validation errors bubble up as tool errors. Graceful fallback when clients don't support elicitation.

## Test Coverage

49 comprehensive tests covering:
- Field validation and edge cases (24 tests)
- Form behavior and integration (25 tests) 
- Error handling, inheritance, performance
- Unicode support and complex validation scenarios

All existing tests pass with no regressions.

## Files Added

- `src/fastmcp/contrib/elicitation_forms/`: Core module with forms, fields, exceptions
- `tests/contrib/test_elicitation_forms.py`: Comprehensive test suite
- `tests/contrib/test_elicitation_forms_edge_cases.py`: Edge case testing
- Helper test files for direct contrib testing

## Backward Compatibility

Fully backward compatible. Elicitation forms are an optional contrib module that doesn't affect existing FastMCP functionality.