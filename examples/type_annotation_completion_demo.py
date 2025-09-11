#!/usr/bin/env python3
"""
Demo server showcasing FastMCP's NEW type annotation-based completion system.

This example demonstrates the improved completion system that uses type annotations
instead of string-based decorator coupling, addressing the concerns about tight
coupling, type safety, and mounting compatibility.
"""

import asyncio
from typing import Annotated, Literal

from pydantic import Field

from fastmcp import FastMCP
from fastmcp.completion import (
    DynamicCompletion,
    FilePathCompletion,
    FuzzyCompletion,
    StaticCompletion,
)
from fastmcp.resources import ResourceTemplate

# Create the FastMCP server
server = FastMCP("Type Annotation Completion Demo")


# Example 1: Tool with type annotation completions
@server.tool
async def analyze_data(
    dataset: Annotated[
        str,
        Field(description="Dataset name to analyze"),
        StaticCompletion(
            ["customer_data", "sales_records", "inventory_logs", "user_activity"]
        ),
    ],
    analysis_type: Annotated[
        str,
        Field(description="Type of analysis to perform"),
        FuzzyCompletion(
            [
                "statistical",
                "trend_analysis",
                "comparative",
                "predictive_modeling",
                "correlation_study",
            ]
        ),
    ],
    output_format: Annotated[
        Literal["json", "csv", "xml", "yaml"],
        Field(description="Output format for results"),
    ] = "json",
) -> str:
    """
    Analyze a dataset with specified analysis type and output format.

    This tool demonstrates type annotation-based completions:
    - dataset: Static completion with predefined choices
    - analysis_type: Fuzzy completion allowing substring matching
    - output_format: Literal type (no completion provider needed)
    """
    return f"Analyzing {dataset} using {analysis_type} analysis, outputting as {output_format}"


# Example 2: Prompt with file path completion
@server.prompt
async def process_file(
    path: Annotated[
        str,
        Field(description="Path to file to process"),
        FilePathCompletion(base_path=".", extensions=[".txt", ".json", ".csv", ".py"]),
    ],
    operation: Annotated[
        str,
        Field(description="Operation to perform on the file"),
        StaticCompletion(["read", "write", "delete", "copy", "move", "compress"]),
    ],
    backup: Annotated[bool, Field(description="Create backup before operation")] = True,
) -> str:
    """
    Process a file with specified operation.

    This prompt demonstrates:
    - path: File path completion with extension filtering
    - operation: Static completion for available operations
    - backup: Boolean parameter (no completion needed)
    """
    backup_text = " (with backup)" if backup else " (no backup)"
    return f"Processing {path} with operation {operation}{backup_text}"


# Example 3: Dynamic completion using custom logic
async def get_available_models(partial: str) -> list[str]:
    """Custom completion function that might query a database or API."""
    # Simulate dynamic model fetching
    models = [
        "gpt-4",
        "gpt-3.5-turbo",
        "claude-3-opus",
        "claude-3-sonnet",
        "llama-2-70b",
        "mixtral-8x7b",
        "gemini-pro",
        "palm-2",
    ]

    # Apply filtering based on partial input
    if not partial:
        return models
    return [m for m in models if partial.lower() in m.lower()]


@server.tool
async def generate_text(
    model: Annotated[
        str,
        Field(description="AI model to use for generation"),
        DynamicCompletion(get_available_models),
    ],
    prompt: Annotated[str, Field(description="Text prompt for generation")],
    max_tokens: Annotated[
        int, Field(description="Maximum tokens to generate", ge=1, le=4000)
    ] = 100,
) -> str:
    """
    Generate text using specified AI model.

    This tool demonstrates dynamic completion that could fetch
    available models from an API or database in real-time.
    """
    return f"Generating text with {model}: '{prompt}' (max tokens: {max_tokens})"


# Example 4: Context-aware completion (advanced)
async def get_projects_for_organization(
    partial: str, context: dict = None
) -> list[str]:
    """
    Context-aware completion that could use other parameter values.

    Note: In a real implementation, you might use context to get the
    selected organization and filter projects accordingly.
    """
    # Mock projects for different organizations
    all_projects = {
        "engineering": ["web-app", "mobile-app", "api-service", "infrastructure"],
        "marketing": ["website", "campaigns", "analytics", "content-management"],
        "sales": ["crm", "reporting", "lead-generation", "forecasting"],
    }

    # In a real implementation, you could access other parameter values via context
    # org = context.get('organization') if context else None

    # For demo, return all projects
    projects = []
    for org_projects in all_projects.values():
        projects.extend(org_projects)

    if not partial:
        return projects
    return [p for p in projects if partial.lower() in p.lower()]


@server.prompt
async def access_project(
    organization: Annotated[
        str,
        Field(description="Organization name"),
        StaticCompletion(
            ["engineering", "marketing", "sales", "support", "legal", "hr"]
        ),
    ],
    project: Annotated[
        str,
        Field(description="Project name within the organization"),
        DynamicCompletion(get_projects_for_organization),  # Could be made context-aware
    ],
) -> str:
    """
    Access a project within an organization.

    This demonstrates how completions could potentially be made context-aware
    in future versions (project completion could filter by selected organization).
    """
    return f"Accessing project '{project}' in organization '{organization}'"


# Example 5: Mixed completion systems (new + legacy)
@server.prompt
async def search_documents(
    query: Annotated[str, Field(description="Search query")],
    category: Annotated[
        str,
        Field(description="Document category"),
        FuzzyCompletion(
            ["all", "documents", "emails", "presentations", "spreadsheets", "images"]
        ),
    ],
    author: str,  # This parameter will use legacy string-based completion
) -> str:
    """Search documents with mixed completion systems."""
    return f"Searching for '{query}' in category '{category}' by author '{author}'"


# Legacy string-based completion for the 'author' parameter
@server.completion("prompt", "search_documents", "author")
async def complete_author(partial: str) -> list[str]:
    """Legacy string-based completion handler."""
    authors = ["alice", "bob", "charlie", "diana", "eve", "frank"]
    if not partial:
        return authors
    return [a for a in authors if a.startswith(partial.lower())]


# Example 6: Resource template (future enhancement)
# Note: Resource templates don't yet support type annotation parameters,
# but this shows how they could work in the future

file_template = ResourceTemplate(
    uri_template="file:///{path}",
    name="File Resource",
    description="Access files on the local system with type-safe path completion",
    parameters={},  # Future: Could support type annotations here
)
server.add_template(file_template)


# For now, use legacy completion for resource templates
@server.completion("resource_template", "file:///{path}", "path")
async def complete_file_path(partial: str) -> list[str]:
    """File path completion for resource template (legacy approach)."""
    # In a real implementation, scan filesystem
    example_files = [
        "config.json",
        "data.csv",
        "readme.txt",
        "script.py",
        "styles.css",
        "index.html",
        "package.json",
        "requirements.txt",
    ]

    if not partial:
        return example_files
    return [f for f in example_files if f.lower().startswith(partial.lower())]


if __name__ == "__main__":
    print("🚀 Starting Type Annotation Completion Demo Server...")
    print("")
    print(
        "This server demonstrates FastMCP's NEW type annotation-based completion system."
    )
    print("")
    print("🆕 NEW: Type Annotation Completions (Recommended)")
    print("✅ Type-safe completion providers attached to parameter annotations")
    print("✅ No string coupling - providers bound directly to arguments")
    print("✅ Mounting/prefixing compatible - automatic key management")
    print("✅ Observable - completion behavior visible in function signatures")
    print("")
    print("Tools with type annotation completions:")
    print(
        "  - analyze_data (dataset: StaticCompletion, analysis_type: FuzzyCompletion)"
    )
    print("  - generate_text (model: DynamicCompletion)")
    print("")
    print("Prompts with type annotation completions:")
    print("  - process_file (path: FilePathCompletion, operation: StaticCompletion)")
    print(
        "  - access_project (organization: StaticCompletion, project: DynamicCompletion)"
    )
    print(
        "  - search_documents (category: FuzzyCompletion, author: legacy string-based)"
    )
    print("")
    print(
        "🔄 Legacy string-based completions still supported for backward compatibility"
    )
    print("  - Resource templates still use @completion decorator")
    print("  - Mixed systems can coexist during migration")
    print("")
    print("Key advantages of the new system:")
    print("  1. No 'footguns' - impossible to reference non-existent arguments")
    print("  2. Type safety - providers are compile-time checkable")
    print("  3. Framework opinion - clear binding between completions and arguments")
    print("  4. Discoverability - completion behavior visible in code")
    print("  5. Mounting compatible - works seamlessly with server composition")
    print("")
    print("Press Ctrl+C to stop the server")

    # Run the server
    asyncio.run(server.run_async())
