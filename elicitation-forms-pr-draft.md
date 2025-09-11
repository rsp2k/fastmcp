# Add Elicitation Forms Contrib Module

## Summary
- Adds a new contrib module `fastmcp.contrib.elicitation_forms` that provides a Django-style field API for creating interactive forms with FastMCP's elicitation system
- Implements field types: `StringField`, `IntegerField`, `NumberField`, `BooleanField`, `EnumField`
- Provides `ElicitationForm` base class with metaclass-based field collection
- Includes comprehensive validation, JSON schema generation, and error handling
- Full test coverage with 49 test cases including edge cases and error conditions

## Features Added

### Field Types
- **StringField**: Text input with min/max length, pattern matching, required validation
- **IntegerField**: Integer input with min/max bounds and type coercion from strings
- **NumberField**: Float/decimal input with precision handling and bounds
- **BooleanField**: Boolean input with flexible string conversion ("true"/"false", "yes"/"no", etc.)
- **EnumField**: Choice selection with enum-based options and validation

### Form System
- **ElicitationForm**: Base class using metaclass to automatically collect field definitions
- **Event Handlers**: `on_accepted()`, `on_declined()`, `on_canceled()` hooks for form lifecycle
- **Data Access**: Clean attribute-style access to validated form data (`form.field_name`)
- **Validation**: Multi-field validation with detailed error reporting

### Integration
- Seamless integration with FastMCP's `ctx.session.elicit()` for custom schemas
- Automatic JSON schema generation for MCP protocol compatibility
- Proper error handling with FastMCP exception hierarchy

## Example Usage

```python
from fastmcp.contrib.elicitation_forms import ElicitationForm, StringField, IntegerField, BooleanField

class UserRegistrationForm(ElicitationForm):
    username = StringField(
        title="Username",
        description="Choose a unique username",
        min_length=3,
        max_length=20,
        pattern=r"^[a-zA-Z0-9_]+$"
    )
    age = IntegerField(
        title="Age", 
        description="Your age in years",
        minimum=13,
        maximum=120
    )
    newsletter = BooleanField(
        title="Subscribe to Newsletter",
        description="Receive updates and news",
        required=False,
        default=True
    )
    
    def on_accepted(self, data):
        return f"Welcome {data['username']}! Registration complete."
    
    def on_declined(self):
        return "Registration cancelled. Come back anytime!"

# Usage in FastMCP tool
@app.tool()
async def register_user(ctx: Context) -> str:
    form = UserRegistrationForm("Please complete your registration:")
    result = await form.elicit(ctx)
    
    if result.accepted:
        # Access validated data as attributes
        username = form.username
        age = form.age 
        newsletter = form.newsletter
        
        # Process registration...
        return f"User {username} registered successfully!"
    else:
        return "Registration not completed."
```

## Technical Implementation

### Field Validation Pipeline
1. **Type Coercion**: Convert input to appropriate Python type
2. **Required Check**: Validate required fields have non-empty values
3. **Format Validation**: Apply min/max bounds, pattern matching, enum choices
4. **Custom Validation**: Extensible validation system

### Schema Generation
- Automatic conversion of field definitions to JSON Schema
- Support for all JSON Schema validation keywords
- Integration with MCP's `requestedSchema` parameter

### Error Handling
- `ValidationError`: Field-level validation failures
- `ElicitationError`: General elicitation system errors  
- `ElicitationNotSupportedError`: Client capability detection
- Proper error chaining and detailed messages

## Testing
- **49 test cases** covering all functionality
- **Edge case testing**: boundary values, Unicode, special characters
- **Error condition testing**: malformed data, validation failures
- **Performance testing**: large forms, rapid creation
- **Integration testing**: FastMCP compatibility

## Compatibility
- **Python 3.10+**: Includes StrEnum backport for older Python versions
- **FastMCP 2.12.2+**: Uses latest elicitation API
- **Type Safety**: Full type hints and mypy compatibility

## Files Added
- `src/fastmcp/contrib/elicitation_forms/__init__.py` - Public API exports
- `src/fastmcp/contrib/elicitation_forms/exceptions.py` - Exception hierarchy  
- `src/fastmcp/contrib/elicitation_forms/fields.py` - Field type implementations
- `src/fastmcp/contrib/elicitation_forms/forms.py` - Form system and metaclass
- `tests/contrib/test_elicitation_forms.py` - Core functionality tests
- `tests/contrib/test_elicitation_forms_edge_cases.py` - Edge case and stress tests

## Test Results
```
49 passed, 0 failed
```

All tests pass with comprehensive coverage of:
- Field validation and type conversion
- Form lifecycle and event handling
- JSON schema generation
- Error conditions and edge cases
- Unicode and internationalization
- Performance characteristics

## Breaking Changes
None - this is a new contrib module with no impact on existing code.

## Future Enhancements
- File upload fields
- Nested form support
- Custom validation decorators
- Form templating system
- Integration with popular form libraries