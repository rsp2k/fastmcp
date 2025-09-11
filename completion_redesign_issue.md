# Type Annotation-Based Completion System

## Problem Statement

The current completion system in FastMCP uses string-based coupling between completion handlers and function arguments, which creates several issues:

1. **Tight String Coupling**: `@completion("prompt", "analyze_data", "dataset")` creates fragile references that break when component names change
2. **No Type Safety**: Argument names are strings with no compile-time validation  
3. **Mounting Incompatibility**: String references may not survive FastMCP's prefixing/mounting system
4. **Separation of Concerns**: Completion logic is separated from argument definitions, reducing discoverability
5. **Footgun Potential**: Easy to misspell argument names or reference non-existent components

## Proposed Solution

Replace string-based completion handlers with type annotation-based completion providers that integrate directly with FastMCP's existing type system.

### Core Design Principles

1. **First-Class Integration**: Completion providers are explicit in function signatures
2. **Type Safety**: Providers are bound to specific arguments via type annotations
3. **Mounting Compatible**: Provider references update automatically with component prefixing
4. **Observable**: Completion behavior is discoverable from function introspection
5. **Framework Opinion**: FastMCP has clear opinions about completion-argument binding

### Implementation Approach

#### 1. Completion Provider Base Class

```python
from abc import ABC, abstractmethod
from typing import Any

class CompletionProvider(ABC):
    """Base class for completion providers attached to type annotations."""
    
    @abstractmethod
    async def complete(self, partial: str, context: dict[str, Any] | None = None) -> list[str]:
        """Generate completion suggestions for the given partial input."""
        pass
```

#### 2. Built-in Provider Types

```python
class StaticCompletion(CompletionProvider):
    """Static completion with predefined choices."""
    
    def __init__(self, choices: list[str]):
        self.choices = choices
    
    async def complete(self, partial: str, context: dict[str, Any] | None = None) -> list[str]:
        if not partial:
            return self.choices
        return [c for c in self.choices if c.lower().startswith(partial.lower())]

class FuzzyCompletion(CompletionProvider):
    """Fuzzy matching completion."""
    
    def __init__(self, choices: list[str]):
        self.choices = choices
    
    async def complete(self, partial: str, context: dict[str, Any] | None = None) -> list[str]:
        return [c for c in self.choices if partial.lower() in c.lower()]

class DynamicCompletion(CompletionProvider):
    """Dynamic completion using a callable."""
    
    def __init__(self, completion_fn: Callable[[str], Awaitable[list[str]]]):
        self.completion_fn = completion_fn
    
    async def complete(self, partial: str, context: dict[str, Any] | None = None) -> list[str]:
        return await self.completion_fn(partial)
```

#### 3. Usage Examples

```python
from typing import Annotated, Literal
from pydantic import Field

@server.tool
async def analyze_data(
    dataset: Annotated[
        str, 
        Field(description="Dataset name to analyze"),
        StaticCompletion(["customer_data", "sales_records", "inventory_logs"])
    ],
    analysis_type: Annotated[
        str,
        Field(description="Type of analysis to perform"), 
        FuzzyCompletion(["statistical", "trend", "comparative", "predictive"])
    ],
    output_format: Annotated[
        Literal["json", "csv", "xml"],
        Field(description="Output format")
    ] = "json"
) -> str:
    """Analyze a dataset with the specified analysis type."""
    return f"Analyzing {dataset} using {analysis_type} analysis"

# Dynamic completion example
async def get_user_completion(partial: str) -> list[str]:
    # Query database, API, filesystem, etc.
    return await fetch_matching_users(partial)

@server.prompt  
async def send_message(
    recipient: Annotated[
        str,
        Field(description="Message recipient"),
        DynamicCompletion(get_user_completion)
    ],
    message: Annotated[str, Field(description="Message content")]
) -> str:
    """Send a message to a user."""
    return f"Sending to {recipient}: {message}"
```

### Technical Implementation

#### 1. Provider Extraction

```python
def extract_completion_providers(func: Callable) -> dict[str, CompletionProvider]:
    """Extract completion providers from function type annotations."""
    providers = {}
    
    type_hints = get_type_hints(func, include_extras=True)
    
    for param_name, annotation in type_hints.items():
        if get_origin(annotation) is Annotated:
            args = get_args(annotation)
            for metadata in args[1:]:
                if isinstance(metadata, CompletionProvider):
                    providers[param_name] = metadata
                    break
    
    return providers
```

#### 2. Enhanced Server Integration

```python
class FastMCP:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._completion_providers: dict[str, dict[str, CompletionProvider]] = {}
    
    def tool(self, func: Callable | None = None, **kwargs):
        """Enhanced tool decorator that extracts completion providers."""
        def decorator(f):
            providers = extract_completion_providers(f)
            tool_instance = super().tool(f, **kwargs)
            if providers:
                self._completion_providers[tool_instance.key] = providers
            return tool_instance
        
        return decorator if func is None else decorator(func)
    
    async def _mcp_complete(self, request: CompleteRequest) -> CompleteResult:
        """Handle completion requests using type annotation providers."""
        component_key = self._get_component_key(request.ref)
        
        if (component_key in self._completion_providers and 
            request.argument.name in self._completion_providers[component_key]):
            
            provider = self._completion_providers[component_key][request.argument.name]
            try:
                values = await provider.complete(
                    request.argument.value,
                    context={'ref': request.ref, 'argument': request.argument}
                )
                return CompleteResult(
                    completion=Completion(
                        values=values[:100],
                        total=len(values),
                        hasMore=len(values) == 100
                    )
                )
            except Exception as e:
                logger.error(f"Completion error: {e}")
                return CompleteResult(completion=Completion(values=[], total=0, hasMore=False))
        
        return CompleteResult(completion=Completion(values=[], total=0, hasMore=False))
```

#### 3. Mounting/Prefixing Compatibility

The system integrates seamlessly with FastMCP's mounting because:

- Completion providers are stored by component `key` (not `name`)
- Component keys are automatically updated during mounting/prefixing
- No string references to component names that could break

```python
def mount(self, server: FastMCP, prefix: str | None = None, **kwargs):
    """Enhanced mount that handles completion provider keys."""
    super().mount(server, prefix, **kwargs)
    
    if hasattr(server, '_completion_providers') and prefix:
        # Component keys are automatically prefixed during mounting
        # Provider mappings follow the same prefixed keys
        for component_key, providers in server._completion_providers.items():
            prefixed_key = f"{prefix}_{component_key}"  
            self._completion_providers[prefixed_key] = providers
```

## Benefits

1. **Type Safety**: Completion providers are compile-time checkable
2. **Discoverability**: Completions are visible in function signatures  
3. **Framework Integration**: Works with existing Field descriptions and type processing
4. **Mounting Compatible**: Automatically handles prefixing without string coupling
5. **Extensible**: Easy to create custom completion providers
6. **Observable**: Can introspect completion behavior from type annotations
7. **No Footguns**: Impossible to reference non-existent arguments or components

## Migration Path

1. **Phase 1**: Implement type annotation system alongside existing string-based system
2. **Phase 2**: Add deprecation warnings for string-based completion decorators  
3. **Phase 3**: Migrate examples and documentation to type annotation approach
4. **Phase 4**: Remove string-based system in next major version

The new system can coexist with the existing system during transition.

## Resource Template Integration

For resource templates, completion providers could be specified in the parameters schema:

```python
wiki_template = ResourceTemplate(
    uri_template="wiki:///{organization}/{project}",
    name="Wiki Resource",
    description="Access organizational wiki content", 
    parameters={
        "organization": Annotated[
            str,
            Field(description="Organization name"),
            StaticCompletion(["engineering", "marketing", "sales"])
        ],
        "project": Annotated[
            str, 
            Field(description="Project name"),
            DynamicCompletion(get_projects_for_org)
        ]
    }
)
```

## Open Questions

1. Should completion providers support context-aware completions (e.g., project completion based on selected organization)?
2. How should completion providers handle async initialization or caching?
3. Should there be built-in providers for common cases (file paths, enum values, etc.)?
4. How should completion providers integrate with FastMCP's validation system?

## Proof of Concept

A working proof of concept is available demonstrating:
- Type annotation extraction
- Provider integration with FastMCP decorators
- Mounting/prefixing compatibility  
- Multiple provider types (static, fuzzy, dynamic)
- Full MCP completion request handling

This design addresses all the concerns raised in the original PR feedback while maintaining FastMCP's philosophy of providing strong opinions about how completions should be bound to their components.