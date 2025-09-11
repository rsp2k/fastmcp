#!/usr/bin/env python3
"""
Proof of concept implementation for type annotation-based completion system.

This addresses the concerns raised in PR feedback:
1. Eliminates string-based coupling
2. Integrates properly with FastMCP's mounting/prefixing system
3. Makes completion handling first-class and observable
4. Compatible with type annotations and Field descriptions
"""

from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from typing import Annotated, Any, Literal, get_args, get_origin

from mcp.types import CompleteRequest, CompleteResult, Completion
from pydantic import Field

from fastmcp import FastMCP
from fastmcp.utilities.types import get_type_hints


class CompletionProvider(ABC):
    """Base class for completion providers attached to type annotations."""

    @abstractmethod
    async def complete(
        self, partial: str, context: dict[str, Any] | None = None
    ) -> list[str]:
        """Generate completion suggestions for the given partial input."""
        pass

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}()"


class StaticCompletion(CompletionProvider):
    """Static completion provider with predefined choices."""

    def __init__(self, choices: list[str]):
        self.choices = choices

    async def complete(
        self, partial: str, context: dict[str, Any] | None = None
    ) -> list[str]:
        if not partial:
            return self.choices
        return [c for c in self.choices if c.lower().startswith(partial.lower())]

    def __repr__(self) -> str:
        return f"StaticCompletion({self.choices!r})"


class FuzzyCompletion(CompletionProvider):
    """Fuzzy matching completion provider."""

    def __init__(self, choices: list[str]):
        self.choices = choices

    async def complete(
        self, partial: str, context: dict[str, Any] | None = None
    ) -> list[str]:
        if not partial:
            return self.choices
        return [c for c in self.choices if partial.lower() in c.lower()]


class FilePathCompletion(CompletionProvider):
    """File system completion provider."""

    def __init__(self, base_path: str = "."):
        self.base_path = base_path

    async def complete(
        self, partial: str, context: dict[str, Any] | None = None
    ) -> list[str]:
        # In a real implementation, this would use os.listdir() or pathlib
        # For demo purposes, return some example files
        example_files = ["config.json", "data.csv", "readme.txt", "script.py"]
        if not partial:
            return example_files
        return [f for f in example_files if f.lower().startswith(partial.lower())]


class DynamicCompletion(CompletionProvider):
    """Dynamic completion provider using a callable."""

    def __init__(self, completion_fn: Callable[[str], Awaitable[list[str]]]):
        self.completion_fn = completion_fn

    async def complete(
        self, partial: str, context: dict[str, Any] | None = None
    ) -> list[str]:
        return await self.completion_fn(partial)


def extract_completion_providers(func: Callable) -> dict[str, CompletionProvider]:
    """Extract completion providers from function type annotations."""
    providers = {}

    try:
        type_hints = get_type_hints(func, include_extras=True)
    except Exception:
        # Fallback to raw annotations if type hint resolution fails
        type_hints = getattr(func, "__annotations__", {})

    for param_name, annotation in type_hints.items():
        # Skip return type annotation
        if param_name == "return":
            continue

        # Check if this is an Annotated type
        if get_origin(annotation) is Annotated:
            args = get_args(annotation)
            if len(args) >= 2:
                # Look for CompletionProvider instances in the annotation metadata
                for metadata in args[1:]:
                    if isinstance(metadata, CompletionProvider):
                        providers[param_name] = metadata
                        break

    return providers


class CompletionAwareServer(FastMCP):
    """Extended FastMCP server with type annotation-based completion support."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._completion_providers: dict[str, dict[str, CompletionProvider]] = {}

    def tool(self, func: Callable | None = None, **kwargs):
        """Enhanced tool decorator that extracts completion providers."""

        def decorator(f):
            # Extract completion providers from type annotations
            providers = extract_completion_providers(f)
            if providers:
                # Store providers using the function's key (which will handle prefixing)
                tool_instance = super(CompletionAwareServer, self).tool(f, **kwargs)
                self._completion_providers[tool_instance.key] = providers
                return tool_instance
            else:
                return super(CompletionAwareServer, self).tool(f, **kwargs)

        if func is None:
            return decorator
        return decorator(func)

    def prompt(self, func: Callable | None = None, **kwargs):
        """Enhanced prompt decorator that extracts completion providers."""

        def decorator(f):
            # Extract completion providers from type annotations
            providers = extract_completion_providers(f)
            if providers:
                # Store providers using the function's key (which will handle prefixing)
                prompt_instance = super(CompletionAwareServer, self).prompt(f, **kwargs)
                self._completion_providers[prompt_instance.key] = providers
                return prompt_instance
            else:
                return super(CompletionAwareServer, self).prompt(f, **kwargs)

        if func is None:
            return decorator
        return decorator(func)

    async def _mcp_complete(self, request: CompleteRequest) -> CompleteResult:
        """Handle completion requests using type annotation providers."""
        ref = request.ref
        argument = request.argument

        # Determine the component type and identifier
        if hasattr(ref, "name"):  # ToolReference or PromptReference
            component_key = ref.name
        else:  # ResourceReference
            component_key = ref.uri

        # Look for completion providers for this component and argument
        if component_key in self._completion_providers:
            providers = self._completion_providers[component_key]
            if argument.name in providers:
                provider = providers[argument.name]
                try:
                    # Generate completions using the provider
                    completion_values = await provider.complete(
                        argument.value, context={"ref": ref, "argument": argument}
                    )

                    # Limit to 100 items per MCP spec
                    completion_values = (
                        completion_values[:100] if completion_values else []
                    )

                    return CompleteResult(
                        completion=Completion(
                            values=completion_values,
                            total=len(completion_values),
                            hasMore=len(completion_values) == 100,
                        )
                    )
                except Exception as e:
                    # Log error and return empty completion
                    print(
                        f"Completion provider error for {component_key}.{argument.name}: {e}"
                    )
                    return CompleteResult(
                        completion=Completion(values=[], total=0, hasMore=False)
                    )

        # Fallback to parent implementation (string-based handlers)
        return await super()._mcp_complete(request)

    def mount(self, server: "FastMCP", prefix: str | None = None, **kwargs):
        """Enhanced mount that properly handles completion provider prefixing."""
        super().mount(server, prefix, **kwargs)

        # If the mounted server has completion providers, we need to update their keys
        # This is automatically handled because the component keys are updated during mounting
        # and our completion providers are keyed by component key
        if isinstance(server, CompletionAwareServer) and prefix:
            # Update completion provider keys to match the prefixed component keys
            updated_providers = {}
            for component_key, providers in server._completion_providers.items():
                # Component keys get prefixed during mounting
                prefixed_key = f"{prefix}_{component_key}"
                updated_providers[prefixed_key] = providers

            # Merge with existing providers
            self._completion_providers.update(updated_providers)


# Example usage demonstrating the new approach:

if __name__ == "__main__":
    server = CompletionAwareServer("Type Annotation Completion Demo")

    # Example 1: Tool with multiple completion providers
    @server.tool
    async def analyze_data(
        dataset: Annotated[
            str,
            Field(description="Dataset name to analyze"),
            StaticCompletion(["customer_data", "sales_records", "inventory_logs"]),
        ],
        analysis_type: Annotated[
            str,
            Field(description="Type of analysis to perform"),
            FuzzyCompletion(["statistical", "trend", "comparative", "predictive"]),
        ],
        output_format: Annotated[
            Literal["json", "csv", "xml"], Field(description="Output format")
        ] = "json",
    ) -> str:
        """Analyze a dataset with the specified analysis type."""
        return f"Analyzing {dataset} using {analysis_type} analysis, outputting as {output_format}"

    # Example 2: Prompt with file path completion
    @server.prompt
    async def process_file(
        path: Annotated[
            str, Field(description="Path to file to process"), FilePathCompletion()
        ],
        operation: Annotated[
            str,
            Field(description="Operation to perform"),
            StaticCompletion(["read", "write", "delete", "copy"]),
        ],
    ) -> str:
        """Process a file at the given path."""
        return f"Processing {path} with operation {operation}"

    # Example 3: Dynamic completion using a callable
    async def get_user_completion(partial: str) -> list[str]:
        # In real implementation, this might query a database
        users = ["alice", "bob", "charlie", "diana"]
        if not partial:
            return users
        return [u for u in users if u.startswith(partial.lower())]

    @server.tool
    async def send_message(
        recipient: Annotated[
            str,
            Field(description="Message recipient"),
            DynamicCompletion(get_user_completion),
        ],
        message: Annotated[str, Field(description="Message content")],
    ) -> str:
        """Send a message to a user."""
        return f"Sending message to {recipient}: {message}"

    print("🚀 Type Annotation Completion Server Demo")
    print("")
    print("Key improvements over string-based approach:")
    print("1. ✅ No string coupling - completions are bound to type annotations")
    print("2. ✅ Type safety - completion providers are type-checked")
    print("3. ✅ Mounting compatible - provider keys update with component prefixing")
    print(
        "4. ✅ First-class - completion providers are explicit in function signatures"
    )
    print("5. ✅ Observable - providers can be inspected from type annotations")
    print("")
    print("Tools with completion:")
    print("  - analyze_data (dataset, analysis_type parameters)")
    print("  - send_message (recipient parameter)")
    print("")
    print("Prompts with completion:")
    print("  - process_file (path, operation parameters)")
