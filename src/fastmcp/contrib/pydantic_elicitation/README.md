# Pydantic Elicitation Forms – Contrib Module for FastMCP

The **Pydantic Elicitation Forms** module provides a declarative, Pydantic-based interface for creating rich, multi-step elicitation workflows in FastMCP servers. Build complex server-driven conversations using familiar Pydantic syntax while leveraging the full power of MCP elicitation.

---

## 🎯 **Why This Module?**

MCP elicitation enables servers to drive interactive conversations with users, but managing multi-step flows with raw `ctx.elicit()` calls can become complex. This module provides:

- **🎨 Familiar Pydantic syntax** for declaring forms
- **🔄 Server-driven conversation flows** with automatic state management
- **✅ Rich validation** using Pydantic's powerful validation system
- **🛡️ Graceful fallbacks** for clients that don't support elicitation
- **🧩 Composable form wizards** for complex multi-step interactions

---

## 📦 Installation

This module is part of the `fastmcp.contrib` package. No separate installation is required if you're already using **FastMCP**.

---

## 🚀 Quick Start

### Basic Form

```python
from fastmcp import FastMCP, Context
from fastmcp.contrib.pydantic_elicitation import ElicitationForm
from pydantic import Field
from typing import Literal

class UserInfoForm(ElicitationForm):
    name: str = Field(..., min_length=1, description="Your full name")
    email: str = Field(..., description="Email address")
    role: Literal["user", "admin"] = Field(default="user", description="Account type")

mcp = FastMCP("My Server")

@mcp.tool()
async def collect_user_info(ctx: Context) -> str:
    result = await UserInfoForm().elicit(
        ctx, 
        message="Please provide your information to get started"
    )
    
    if result.accepted():
        return f"Welcome {result.data.name}! Email: {result.data.email}"
    else:
        return "Information collection cancelled"
```

### Multi-Step Wizard

```python
from fastmcp.contrib.pydantic_elicitation import ElicitationWizard

class OnboardingForm(ElicitationForm):
    name: str = Field(..., description="Your name")

class PreferencesForm(ElicitationForm):
    theme: Literal["light", "dark"] = Field(default="light")
    notifications: bool = Field(default=True)

class ConfirmationForm(ElicitationForm):
    agree_to_terms: bool = Field(..., description="I agree to the terms of service")

class OnboardingWizard(ElicitationWizard):
    steps = [OnboardingForm, PreferencesForm, ConfirmationForm]
    
    def get_step_message(self, step_class, step_data=None):
        messages = {
            OnboardingForm: "Welcome! Let's get you set up.",
            PreferencesForm: f"Hi {step_data.get('name', 'there')}! Set your preferences:",
            ConfirmationForm: "Almost done! Please confirm:"
        }
        return messages.get(step_class, "Please fill out this form:")

@mcp.tool()
async def user_onboarding(ctx: Context) -> str:
    wizard = OnboardingWizard()
    result = await wizard.run(ctx)
    
    if result.completed():
        return f"Onboarding complete! Welcome {result.data['name']}"
    else:
        return f"Onboarding cancelled at step {result.cancelled_step}"
```

### Conditional Flow

```python
class UserTypeForm(ElicitationForm):
    user_type: Literal["basic", "premium", "enterprise"] = Field(...)
    
    def next_step(self):
        """Return the next form based on user selection"""
        if self.user_type == "premium":
            return PremiumSetupForm
        elif self.user_type == "enterprise":
            return EnterpriseSetupForm
        return None  # End flow for basic users

class PremiumSetupForm(ElicitationForm):
    billing_cycle: Literal["monthly", "yearly"] = Field(...)
    payment_method: Literal["card", "paypal"] = Field(...)

class EnterpriseSetupForm(ElicitationForm):
    company_name: str = Field(...)
    employee_count: int = Field(..., ge=1)

@mcp.tool()
async def account_setup(ctx: Context) -> str:
    current_form = UserTypeForm()
    collected_data = {}
    
    while current_form:
        result = await current_form.elicit(
            ctx, 
            message="Please complete the form:"
        )
        
        if result.declined_or_cancelled():
            return "Account setup cancelled"
            
        # Collect data from this step
        collected_data.update(result.data.dict())
        
        # Determine next step
        current_form = result.data.next_step()
        if current_form:
            current_form = current_form()  # Instantiate next form
    
    return f"Account setup complete! Type: {collected_data['user_type']}"
```

---

## 🧩 API Reference

### `ElicitationForm`

Base class for creating elicitation forms using Pydantic.

```python
class ElicitationForm(BaseModel):
    async def elicit(
        self, 
        ctx: Context, 
        message: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ElicitationResult:
        """Elicit user input for this form"""
        
    def next_step(self) -> Optional['ElicitationForm']:
        """Override to define conditional flow logic"""
        return None
```

### `ElicitationResult`

Result wrapper for elicitation responses.

```python
class ElicitationResult:
    action: Literal["accept", "decline", "cancel"]
    data: Optional[ElicitationForm]
    
    def accepted(self) -> bool: ...
    def declined(self) -> bool: ...
    def cancelled(self) -> bool: ...
    def declined_or_cancelled(self) -> bool: ...
```

### `ElicitationWizard` 

Helper class for managing multi-step form wizards.

```python
class ElicitationWizard:
    steps: List[Type[ElicitationForm]]
    
    async def run(self, ctx: Context) -> WizardResult:
        """Run the complete wizard flow"""
        
    def get_step_message(
        self, 
        step_class: Type[ElicitationForm], 
        collected_data: Dict = None
    ) -> str:
        """Override to customize messages for each step"""
```

---

## 🛡️ Graceful Fallbacks

The module automatically handles clients that don't support elicitation:

```python
@mcp.tool()
async def collect_info_with_fallback(ctx: Context) -> str:
    form = UserInfoForm()
    
    try:
        result = await form.elicit(ctx, "Please provide your info:")
        if result.accepted():
            return f"Hello {result.data.name}!"
        else:
            return "Information collection declined"
            
    except ElicitationNotSupportedError:
        # Automatic fallback for non-elicitation clients
        return """
        Information collection requires an interactive client.
        
        Please provide:
        - name: Your full name
        - email: Your email address  
        - role: 'user' or 'admin'
        """
```

---

## 💡 Best Practices

### 1. **Keep Forms Simple**
MCP elicitation supports only primitive types (string, number, boolean, enums):

```python
class GoodForm(ElicitationForm):
    name: str                           # ✅ String
    age: int                           # ✅ Number  
    active: bool                       # ✅ Boolean
    role: Literal["user", "admin"]     # ✅ Enum

class BadForm(ElicitationForm):
    address: Dict[str, str]            # ❌ Nested object
    tags: List[str]                    # ❌ Array
    metadata: Optional[CustomModel]    # ❌ Complex type
```

### 2. **Design Server-Driven Flows**
Remember that the server controls the conversation:

```python
# ✅ Good: Server decides next step
async def registration_flow(ctx: Context):
    basic_info = await BasicInfoForm().elicit(ctx, "Basic info:")
    if basic_info.accepted():
        prefs = await PreferencesForm().elicit(ctx, "Your preferences:")
        # Server continues...

# ❌ Bad: Trying to let client decide
class FormWithClientChoice(ElicitationForm):
    next_action: Literal["continue", "skip", "back"]  # Client can't control flow
```

### 3. **Provide Clear Messages**
Each elicitation should have a clear, contextual message:

```python
# ✅ Good: Clear, contextual messages
result1 = await UserForm().elicit(ctx, "Welcome! Please tell us about yourself:")
result2 = await PlanForm().elicit(ctx, f"Hi {result1.data.name}! Choose your plan:")

# ❌ Bad: Generic messages
result1 = await UserForm().elicit(ctx, "Fill out form")
result2 = await PlanForm().elicit(ctx, "Next step")
```

### 4. **Handle All Response Types**
Always handle decline and cancel scenarios:

```python
async def robust_flow(ctx: Context):
    result = await MyForm().elicit(ctx, "Please fill out:")
    
    if result.accepted():
        # Happy path
        return process_data(result.data)
    elif result.declined():
        # User said no, but stayed engaged
        return "No problem! You can try again later."
    else:  # result.cancelled()
        # User closed/abandoned
        return "Session ended."
```

---

## 🔍 Examples

See the `examples/` directory for complete working examples:

- **`basic_form.py`** - Simple single-step form
- **`wizard_flow.py`** - Multi-step wizard with linear progression
- **`conditional_flow.py`** - Branching logic based on user responses
- **`error_handling.py`** - Comprehensive error and fallback handling

---

## 🤝 Contributing

Contributions are welcome! Please ensure your contributions include:

- Tests for new functionality
- Documentation updates
- Examples demonstrating usage

---

## ⚠️ Limitations

- **MCP Constraints**: Only primitive types supported (no nested objects/arrays)
- **Server-Driven**: Client cannot control conversation flow, only respond
- **Three Actions Only**: Clients can only Accept/Decline/Cancel
- **No Client State**: Each elicitation is stateless from client perspective

These limitations are by design in the MCP specification to maintain security and simplicity.