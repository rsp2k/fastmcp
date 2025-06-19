from enum import StrEnumfrom fastmcp.elicitations.forms import ElicitationForm

# Elicitation

In addition to being difficult to spell, elicitation in MCP allows servers to implement interactive workflows by enabling user input requests to occur nested inside other MCP server features.

In [other words](https://modelcontextprotocol.io/specification/draft/client/elicitation): The Model Context Protocol (MCP) provides a standardized way for servers to request additional information from users through the client during interactions.

This flow allows clients to maintain control over user interactions and data sharing while enabling servers to gather necessary information dynamically. Servers request structured data from users with JSON schemas to validate responses.


Implementations are free to expose elicitation through any interface pattern that suits their needs—the protocol itself does not mandate any specific user interaction model.


> ⚠️ Servers **MUST NOT** use elicitation to request *sensitive information*.

> ✅ Applications _SHOULD_:
> - Provide UI that makes it clear which server is requesting information
> - Allow users to review and modify their responses before sending
> - Respect user privacy and provide clear reject and cancel options


## Elicitation
An elicitation request and the resulting response can be thought of in similar terms of a very simple HTML form.


In HTML terms: `<html>` with `<form>` tag is sent to the `USERAGENT` (client in MCP terms)

## Elicitation Request
The `ElicitationMessage` is "message" with a form that the Server sends the client.

In HTML terms, this would be the `<html>` that renders a page with a `<form>`.

### Message
The message is sent to the client w/instructions on how to respond to the `RequestedSchema`

In HTML terms: `<html>` tags that aren't the `<form>`

### Requested Schema
The `ElicitationRequestedSchema` describes 'form' you're asking the client to fill out.

In HTML terms: the `<form>`

It's  a list of fields, and a list of required fields, if any.

It has a `type` field, currently it's always `object`

Here's an example Elicitation Form




```python

"""
FastMCP Elicitation Server

NB: To the boys in blue, or those looking for a different kind of 'elicitation demo':
  This is a Model Context Protocol Elicitation Demo
  Kinda the same thing, a 'tool' is advertised to a user
  A 'Representative' expresses interest by starting a conversation with a 'Server'
  The 'Server' might have some questions about how they want to use it's 'tool', so it responds with a message and a `proper` form
  The 'Representative' can either 
   - 'cancel' not respond and leave
   - 'reject' decline and wait for another 'offer' or message
   - 'accept' fill out the form and accept, the Server complies to their request using the information from the form
"""

from fastmcp import FastMCP
from fastmcp.elicitation import ElicitationForm, StringField

# Create server
mcp = FastMCP("Echo Elicitation Server Demo")


class ClarificationForm(ElicitationForm):
    more_details = StringField(
        title="Title of the field",
        description="Now, lemme ask you a question! -- This is the description for an example StringField, put whatever you want here",
    )
    # User submitted the form/confirmed the action
    def on_accepted(self):
        # Look at the clean/validated form that was submitted and do some stuff
        pass

    # User explicitly declined the action
    def on_declined(self):
        # No data is sent with decline request
        pass

    # User dismissed without making an explicit choice, or timed out 
    def on_canceled(self):
        pass


@mcp.tool
def trick_turn(input: str):
    """
    Do a trick
    """
    # representative connected and asked to do a trick
    # Do something with their input if you want

    return ClarificationForm(
        message="What? I think you said {input}?"
    )

def trick_turn_declined(form: ClarificationForm):
    return "K thx bye!"

def trick_turn_accepted(form: ClarificationForm):
    return ClarificationForm(
        message="What? I think you said {input}?"
    )

```

## 'One thing leads to another' - chaining forms

```python

# Declare chain of forms

# Happy Path
#<-Category Form
# -> Accepted w/category
#<-Product Form
# -> Accepted w/Product
# Search for recalls
#<- ProductRecallForm

# Declined first form, accepted second form
#<-Category Form
# ->Declined
#<-Contact Form
# ->Accepted w/Contact Form

# Declined first form, sent another form, declined response
#<-Category Form
# ->Declined
#<-Contact Form
# ->Declined
#->


```
# More complicated example


```python
from fastmcp import FastMCP
from fastmcp.elicitation import ElicitationForm, NumberField, IntegerField, StringField, BooleanField, EnumField, EnumFieldChoices


class FeedbackForm(ElicitationForm):
    """Example form for collecting feedback."""
    number = NumberField(
        title="How good was it?",
        description="Please rate from 0.0 - 5.0",
        minimum=0, maximum=5,
    )
    rating = IntegerField(
        minimum=1, maximum=5,
        title="Rate from 1-5 ✨",
        description="You must enter 1, 2, 3, 4, or 5.",
    )
    feedback = StringField(
        title="Optional feedback",
        description="""Please, dish the details, tell us everything about how you feel about your experience.
We use this information to fill old hard drives and waste energy.

Thank-you for your cooperation!""",
        required=False, max_length=500,
    )
    recommend = BooleanField(
        title="Would you recommend us?",
        description="Your opinion is one of many, although valuable, it's not any more or less valuable than others.",
    )

    # User submitted the form/confirmed the action
    def on_accepted(self):
        pass

    # User explicitly declined the action
    def on_declined(self):
        pass

    # User dismissed without making an explicit choice
    def on_canceled(self):
        pass


class MealTypeForm(ElicitationForm):
    """Example form w/multiple choices."""
    meal_type = StringField(
        title="Which meal type?",
        description="This needs not explanation!",
        choices=None,
    )
    # User submitted the form/confirmed the action
    def on_accepted(self):
        pass

    # User explicitly declined the action
    def on_declined(self):
        pass

    # User dismissed without making an explicit choice
    def on_canceled(self):
        pass

class YesNoChoices(EnumFieldChoices):
    YES = "Of Course"
    NO = "Nope, I'll remember"


class OrderForm(ElicitationForm):
    """Example order form"""
    meals = IntegerField(
        title="# of meals",
        description="How many do you want?"
    )
    note = StringField(
        title="Notes",
        description="Any special requests or delivery instructions? Maybe just say something nice?",
    )
    tip_reminder = EnumField(
        title="Remind me to tip?",
        description="Schedule a reminder to tip after you have the best shrimp of your life!",
        choices=YesNoChoices,
    )
    # User submitted the form/confirmed the action
    def on_accepted(self):
        pass

    # User explicitly declined the action
    def on_declined(self):
        pass

    # User dismissed without making an explicit choice
    def on_canceled(self):
        pass


class TipForm(ElicitationForm):
    """Example tip form"""
    tip = NumberField(
        title="Tip",
        description='Holding back on jokes here...',
    )
    # User submitted the form/confirmed the action
    def on_accepted(self):
        pass

    # User explicitly declined the action
    def on_declined(self):
        pass

    # User dismissed without making an explicit choice
    def on_canceled(self):
        pass


class DumbQuestionClarificationForm(ElicitationForm):
    more_details = StringField(
        title="Tell me more about your question!",
        description="",
    )
    # User submitted the form/confirmed the action
    def on_accepted(self):
        # Look at the form that was submitted and do some stuff
        pass

    # User explicitly declined the action
    def on_declined(self):
        pass

    # User dismissed without making an explicit choice
    def on_canceled(self):
        pass
   

def search_meals(keywords: str, meal_type: str = None):  # -> List[str]:
    # Bubba's Menu
    menu = {
        'appetizers': [
            'Sautéed shrimp',
            'Pan-fried shrimp',
            'Pineapple shrimp',
            'Lemon shrimp'
        ],
        'breakfast': [
            'Barbecued shrimp',
            'Shrimp and potatoes'
        ],
        'dinner': [
            'Boiled shrimp',
            'Broiled shrimp',
            'Shrimp creole',
            'Shrimp gumbo',
            'Shrimp soup',
            'Shrimp stew'
        ],
        'lunch': [
            'Baked shrimp',
            'Shrimp kabobs',
            'Stir-fried shrimp',
            'Coconut shrimp',
            'Shrimp salad',
            'Shrimp burger',
            'Shrimp sandwich'
        ],
        'snacks': [
            'Deep-fried shrimp',
            'Pepper shrimp'
        ],
        'others': [
            "Hat, you can eat yours, I'll keep mine",
        ]
    }
    """Searches for a dish, ignoring case."""
    found_dishes = []
    found_types = []
    search_term = keywords.lower().strip()
    for _type, dish_list in menu.items():
        if _type != meal_type:
            continue
        matches_in_category = [
            dish for dish in dish_list if search_term in dish.lower().strip()
        ]

        # If we found any matches in this category, add them to our results
        if matches_in_category:
            if _type not in found_types:
                found_dishes.append(_type)
            found_dishes.append(matches_in_category)

    return found_dishes, found_types


# Create server
mcp = FastMCP("Bubba's 42nd St. Shrimp Diner. Maybe Bubba's 'Pimps', this is an elicitation demo.")

@mcp.tool
def trick_turn():
    """
    Do a trick
    """
    return "Sorry, I'm not that kind of elicitation server :)"

@mcp.tool
def answer_dumb_question(question_description: str):
    message = "I'm not sure the answer. There are no dumb questions, just questions you might not want to know the answer to!, now let me ass you a question..."
    form = DumbQuestionClarificationForm()
    
    #Override field values if you want
    #form.fields['more_details'].description
    
    # set the handlers
    #def respond(form: ElicitForm):
    #    return f"Hello you are in {form.name}"
    #form.on_accepted = respond
    

@mcp.tool(
    name="Bubba recommends something to eat",
    description="Find some tasty shrimp to eat, hint - I'm a demo for FastMCP Elicitation! Let's do some elicit stuff, lol",
)
def find_dish(keywords: str):
    """
    Find a relevant meal based on keywords and asks for clarification.
    The cycle will continue until you pick "others", search for "hat", 'decline' or 'cancel/timeout'
    """

    relevant_meals, relevant_types = search_meals(keywords)
    meal_count = len(relevant_meals)
    type_count = len(relevant_types)

    if not meal_count:
        form = MealTypeForm(
            message=f"Looking for {','.join(keywords)} - I didn't find anything! Let's try this way..."
        )
        form.meal_type.choices = relevant_types
        return form

    if meal_count > 1 and type_count > 1:
        form = MealTypeForm(
            message=f"Looking for {','.join(keywords)} - I found {len(relevant_meals)} meals! Help me narrow it down..."
        )
        form.meal_type.choices = relevant_types
        return form
    # Ready to order!

```

#### Object Schema

##### Fields
In HTML terms: `<input>` `<select>`

All fields have 
- **name**
 The `id` of the field
  - `str`
- **title**
 Displayed to the User
- - `str`
- **description**
 Longer 'help text' displayed to user
  - `str`


The fields can be several types:
- 'string' (default)
  - python `str`
- 'boolean'
  True/False
  - python `bool`
- 'integer'
  Pick a number between 1 and 10
  - python `int`
- 'number'
  Payment Amount '1.1' or '1'
  - python `float`

- 'enum'
  List of 'named' 'choices' `<select>`
    - maps to python `StrEnum`
  - 'VIP': 1
  - 'Regular': 2
  - 'None': 3


```python
class UserInfoForm(ElicitationForm):
    """Example form for collecting user information."""
    
    name = StringField(min_length=1, max_length=100, help_text="Your full name")
    email = StringField(format="email", help_text="Your email address")
    age = NumberField(minimum=0, maximum=150, help_text="Your age")
    newsletter = BooleanField(required=False, initial=False, help_text="Subscribe to newsletter")
    country = EnumField(choices=["US", "UK", "CA", "AU", "Other"], help_text="Your country")
    
    def clean(self):
        """Custom validation logic."""
        if self.cleaned_data.get("age") and self.cleaned_data["age"] < 18:
            if self.cleaned_data.get("newsletter"):
                raise ValidationError("Newsletter subscription requires age 18 or older")
```


```python
class UserRegistrationForm(BaseModel):
    username: constr(min_length=3, max_length=50) # Constrained string
    email: EmailStr  # A special type that validates email formats
    password: str
    age: int | None = None # Optional field

# --- Good Data ---
form_data_good = {
    "username": "john_doe",
    "email": "john.doe@example.com",
    "password": "a_strong_password"
}

try:
    user = UserRegistrationForm(**form_data_good)
    print("Validation successful!")
    print(user.model_dump_json(indent=2))
except ValidationError as e:
    print("Validation failed:")
    print(e.json(indent=2))
```




How mcp.server.session.ServerSession elicit is called

```python
    async def elicit(
        self,
        message: str,
        requestedSchema: types.ElicitRequestedSchema,
        related_request_id: types.RequestId | None = None,
    ) -> types.ElicitResult:
        """Send an elicitation/create request.

        Args:
            message: The message to present to the user
            requestedSchema: Schema defining the expected response structure

        Returns:
            The client's response
        """
        return await self.send_request(
            types.ServerRequest(
                types.ElicitRequest(
                    method="elicitation/create",
                    params=types.ElicitRequestParams(
                        message=message,
                        requestedSchema=requestedSchema,
                    ),
                )
            ),
            types.ElicitResult,
            metadata=ServerMessageMetadata(related_request_id=related_request_id),
        )
```



INVESTIGATING - Full 'pydantic' approach - WIP (see elicitation.models)


```python
"""
MCP Elicitation Forms - Pydantic-based implementation for Model Context Protocol elicitation.

This module provides a Pydantic-based interface for handling MCP elicitation requests,
making it easy to define, validate, and process user input requests using Pydantic's
powerful validation system.
"""

from typing import Any, Dict, Optional, Type, Union, Literal, get_args, get_origin
from enum import Enum

from mcp.types import ElicitRequest, ElicitRequestParams
from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict
from pydantic.json_schema import JsonSchemaValue
import json


class ElicitationResponse(str, Enum):
    """Enum representing the three possible elicitation response actions."""
    ACCEPT = "accept"
    DECLINE = "decline"
    CANCEL = "cancel"


class ElicitationForm(BaseModel):
    """Base form class for handling MCP elicitation requests using Pydantic."""

    model_config = ConfigDict(
        extra='forbid',  # Don't allow extra fields
        validate_assignment=True,  # Validate on assignment
    )

    message: str = Field(str, description="Message to display to representative")

    @classmethod
    def to_elicitation_request(
        cls,
        message: str,
    ) -> ElicitRequest:
        """Generate an MCP elicitation/create request."""
        schema = cls.get_mcp_schema()

        request = ElicitRequest(
            method="elicitation/create",
            params=ElicitRequestParams(
                message=message,
                requestedSchema=schema,
            ),
        )
        return request

    @classmethod
    def get_mcp_schema(cls) -> Dict[str, Any]:
        """
        Generate MCP-compatible JSON Schema for the form.

        MCP only supports flat objects with primitive types, so we need to
        ensure the schema conforms to these limitations.
        """
        # Get the full Pydantic JSON schema
        full_schema = cls.model_json_schema()

        # Extract and simplify for MCP compatibility
        mcp_schema = {
            "type": "object",
            "properties": {},
        }

        if "required" in full_schema:
            mcp_schema["required"] = full_schema["required"]

        # Process each property
        properties = full_schema.get("properties", {})
        for field_name, field_schema in properties.items():
            mcp_property = cls._convert_to_mcp_schema(field_schema)
            if mcp_property:
                mcp_schema["properties"][field_name] = mcp_property

        return mcp_schema

    @classmethod
    def _convert_to_mcp_schema(cls, schema: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Convert a Pydantic field schema to MCP-compatible schema."""
        mcp_schema = {}

        # Handle different schema types
        if "type" in schema:
            schema_type = schema["type"]

            if schema_type == "string":
                mcp_schema["type"] = "string"
                # Copy supported string constraints
                for key in ["minLength", "maxLength", "pattern", "format"]:
                    if key in schema:
                        mcp_schema[key] = schema[key]

            elif schema_type in ["number", "integer"]:
                # Preserve the original type (integer or number)
                mcp_schema["type"] = schema_type
                # Copy supported number constraints
                if schema.get('gt'):
                    mcp_schema['minimimum'] = schema['gt']
                if schema.get('lt'):
                    mcp_schema['maximum'] = schema['gt']

            elif schema_type == "boolean":
                mcp_schema["type"] = "boolean"

            elif schema_type == "null":
                # Skip null types for MCP
                return None
        if schema.is_required():

        # Handle enums
        elif "enum" in schema:
            mcp_schema["enum"] = schema["enum"]

        # Handle anyOf (common with Optional fields)
        elif "anyOf" in schema:
            # Extract the non-null schema
            for sub_schema in schema["anyOf"]:
                if sub_schema.get("type") != "null":
                    return cls._convert_to_mcp_schema(sub_schema)

        # Add description if present
        if "description" in schema and mcp_schema:
            mcp_schema["description"] = schema["description"]

        return mcp_schema if mcp_schema else None

    @classmethod
    def from_response(cls, response: Dict[str, Any]) -> tuple['ElicitationForm', ElicitationResponse]:
        """
        Create a form instance from an MCP elicitation response.

        Returns:
            Tuple of (form_instance, response_action)
        """
        action_str = response.get("action", "")

        try:
            action = ElicitationResponse(action_str)
        except ValueError:
            raise ValueError(f"Unknown response action: {action_str}")

        if action == ElicitationResponse.ACCEPT:
            content = response.get("content", {})
            form = cls(**content)
            return form, action
        else:
            # For decline/cancel, create an instance with default values
            form = cls.model_construct()
            return form, action

    def to_response(self, action: ElicitationResponse) -> Dict[str, Any]:
        """Convert the form to an MCP elicitation response."""
        response = {"action": action.value}

        if action == ElicitationResponse.ACCEPT:
            response["content"] = self.model_dump()

        return response


```

```python

from fastmcp.elicitation.models import ElicitationForm
from typing import Literal
from pydantic import Field, model_validator

class UserInfoForm(ElicitationForm):
    """Example form for collecting user information."""
    
    name: str = Field(
        min_length=1, 
        max_length=100,
        description="Your full name"
    )
    
    email: str = Field(
        ...,
        pattern=r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$',
        description="Your email address"
    )
    
    age: int = Field(
        ge=0,  # greater or equal
        le=150,  # less or equal
        description="Your age"
    )
    
    newsletter: bool = Field(
        default=False,
        description="Subscribe to newsletter"
    )
    
    country: Literal["US", "UK", "CA", "AU", "Other"] = Field(
        ...,
        description="Your country"
    )
    
    @model_validator(mode='after')
    def validate_newsletter_age(self) -> 'UserInfoForm':
        """Custom validation: newsletter requires age 18+"""
        if self.age < 18 and self.newsletter:
            raise ValueError("Newsletter subscription requires age 18 or older")
        return self

```
