# Add Elicitation Forms Contrib Module

## Summary

This PR introduces a new contrib module `fastmcp.contrib.elicitation_forms` that provides a Django-style field API for creating structured user input forms with FastMCP's elicitation system.

### Key Features

- **Field Types**: StringField, IntegerField, NumberField, BooleanField, EnumField with comprehensive validation
- **Form Classes**: ElicitationForm base class with metaclass-driven field collection
- **JSON Schema Generation**: Automatic conversion to MCP-compatible JSON schemas
- **Event Handlers**: Support for `on_accepted`, `on_declined`, and `on_canceled` callbacks
- **Validation**: Rich field validation with detailed error messages
- **Python 3.10+ Compatibility**: StrEnum backport for older Python versions

### Usage Example

```python
from fastmcp.contrib.elicitation_forms import ElicitationForm, StringField, IntegerField

class UserInfoForm(ElicitationForm):
    name = StringField(
        title="Your name",
        description="Please enter your full name",
        min_length=1,
        max_length=100
    )
    age = IntegerField(
        title="Your age", 
        description="How old are you?",
        minimum=0,
        maximum=150
    )

    def on_accepted(self, data):
        return f"Welcome {data['name']}, age {data['age']}!"

# In your tool function:
async def get_user_info(ctx: Context) -> str:
    form = UserInfoForm()
    result = await form.elicit(ctx, "Please provide your information:")
    
    if result.accepted:
        return f"Hello {result.data['name']}!"
    else:
        return "Maybe next time!"
```

## Implementation Details

### Architecture

- **Metaclass-based Field Collection**: `ElicitationFormMeta` automatically collects field definitions from class attributes
- **Validation Pipeline**: Each field validates input data with type checking, bounds checking, and format validation  
- **Schema Generation**: Fields generate JSON schema properties compatible with MCP elicitation
- **Error Handling**: Custom exception hierarchy with `ValidationError`, `ElicitationError`, and `ElicitationNotSupportedError`

### Field Types

| Field Type | Validation | Schema Properties |
|------------|------------|-------------------|
| `StringField` | min/max length, regex pattern | `minLength`, `maxLength`, `pattern` |
| `IntegerField` | min/max bounds, type conversion | `minimum`, `maximum`, `type: integer` |
| `NumberField` | min/max bounds, float conversion | `minimum`, `maximum`, `type: number` |  
| `BooleanField` | flexible true/false conversion | `type: boolean` |
| `EnumField` | choice validation against enum | `enum`, `enumNames` |

### Integration

The module integrates with FastMCP's low-level elicitation API:

```python
result = await ctx.session.elicit(
    message=elicit_message,
    requestedSchema=schema,
    related_request_id=ctx.request_id,
)
```

## Testing

- **49 test cases** covering core functionality, edge cases, and error scenarios
- **100% test pass rate** with comprehensive validation testing
- **Edge case coverage**: Unicode support, boundary values, malformed data handling
- **Performance tests**: Form creation, schema generation, memory usage

## Compatibility

- **Python 3.10+**: StrEnum backport for older Python versions
- **FastMCP v2.12.2+**: Uses session.elicit() API
- **Type Safety**: Full type annotations with proper generic usage

## Files Added

```
src/fastmcp/contrib/elicitation_forms/
├── __init__.py          # Public API exports
├── exceptions.py        # Custom exception hierarchy  
├── fields.py           # Field type implementations
└── forms.py            # ElicitationForm base class

tests/contrib/
├── test_elicitation_forms.py           # Core functionality tests
└── test_elicitation_forms_edge_cases.py # Edge case and stress tests
```

## Breaking Changes

None - this is a new contrib module with no impact on existing code.

## Migration Guide

N/A - new feature addition.

## Related Issues

This implements a higher-level API for FastMCP's elicitation capabilities, making it easier for tool developers to create structured input forms without manually crafting JSON schemas.