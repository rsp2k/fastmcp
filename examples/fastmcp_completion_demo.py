#!/usr/bin/env python3
"""
Demo server showcasing FastMCP's type annotation-based completion system.

This example demonstrates completion providers that suggest actual FastMCP
components (prompts, resources) rather than generic string completions.
"""

import asyncio
from typing import Annotated

from pydantic import Field

from fastmcp import FastMCP
from fastmcp.completion import (
    PromptCompletion,
    ResourceCompletion,
    ResourceTemplateCompletion,
    StaticCompletion,
)

# Create the FastMCP server
server = FastMCP("FastMCP Completion Demo")


# Add some prompts for completion suggestions
@server.prompt
async def analyze_code(language: str, complexity: str) -> str:
    """Analyze code complexity for a given language."""
    return f"Analyzing {language} code with {complexity} complexity level."


@server.prompt
async def generate_docs(format: str, detail_level: str) -> str:
    """Generate documentation in specified format."""
    return f"Generating {format} docs with {detail_level} detail."


@server.prompt
async def review_pr(focus_area: str) -> str:
    """Review pull request focusing on specific area."""
    return f"Reviewing PR with focus on {focus_area}."


# Add some resources for completion suggestions
@server.resource("file://config.json")
async def config_resource() -> str:
    """Application configuration file."""
    return '{"app": "FastMCP Demo", "version": "1.0"}'


@server.resource("file://readme.md")
async def readme_resource() -> str:
    """Project README file."""
    return "# FastMCP Demo\n\nThis is a demo project."


@server.resource("file://logs/app.log")
async def logs_resource() -> str:
    """Application log file."""
    return "[INFO] Server started\n[INFO] Ready to accept connections"


# Add resource templates for completion suggestions
@server.resource_template("file://data/{dataset}.csv")
async def dataset_template(dataset: str) -> str:
    """Dataset CSV files."""
    return f"dataset,value\n{dataset},sample_data"


@server.resource_template("file://models/{model_type}.pkl")
async def model_template(model_type: str) -> str:
    """Trained model files."""
    return f"<binary model data for {model_type}>"


# Example 1: Tool that completes with available prompts
@server.tool
async def execute_prompt(
    prompt_name: Annotated[
        str,
        Field(description="Name of the prompt to execute"),
        PromptCompletion(),  # Suggests all available prompts
    ],
    context: Annotated[
        str,
        Field(description="Execution context"),
        StaticCompletion(["development", "testing", "production"]),
    ] = "development",
) -> str:
    """
    Execute a named prompt with given context.

    The prompt_name parameter will autocomplete with actual prompts available
    in this server: analyze_code, generate_docs, review_pr
    """
    prompts = server._prompt_manager.list_prompts()
    prompt = next((p for p in prompts if p.key == prompt_name), None)

    if not prompt:
        return f"Prompt '{prompt_name}' not found"

    return f"Executing prompt '{prompt_name}' in {context} context"


# Example 2: Tool that completes with available resources
@server.tool
async def read_resource(
    resource_uri: Annotated[
        str,
        Field(description="URI of the resource to read"),
        ResourceCompletion(),  # Suggests all available resources
    ],
) -> str:
    """
    Read a named resource.

    The resource_uri parameter will autocomplete with actual resources:
    file://config.json, file://readme.md, file://logs/app.log
    """
    try:
        resources = server._resource_manager.list_resources()
        resource = next((r for r in resources if r.uri == resource_uri), None)

        if not resource:
            return f"Resource '{resource_uri}' not found"

        # Execute the resource function to get content
        content = await resource.fn()
        return f"Content of '{resource_uri}':\n{content}"
    except Exception as e:
        return f"Error reading resource '{resource_uri}': {e}"


# Example 3: Tool with filtered completions
@server.tool
async def process_dataset(
    template_uri: Annotated[
        str,
        Field(description="Resource template for dataset processing"),
        ResourceTemplateCompletion(
            # Filter to only show CSV templates
            filter_fn=lambda t: t.uri_template.endswith(".csv")
        ),
    ],
    dataset_name: Annotated[
        str,
        Field(description="Name of the dataset"),
        StaticCompletion(["users", "products", "transactions", "logs"]),
    ],
) -> str:
    """
    Process a dataset using a resource template.

    The template_uri will only suggest CSV templates, and dataset_name
    provides static completion options.
    """
    return f"Processing dataset '{dataset_name}' using template '{template_uri}'"


# Example 4: Tool that completes with docs-related prompts only
@server.tool
async def generate_documentation(
    docs_prompt: Annotated[
        str,
        Field(description="Documentation generation prompt to use"),
        PromptCompletion(
            # Filter to only show prompts related to documentation
            filter_fn=lambda p: "docs" in p.key.lower() or "generate" in p.key.lower()
        ),
    ],
    output_format: Annotated[
        str,
        Field(description="Documentation output format"),
        StaticCompletion(["markdown", "html", "pdf", "rst"]),
    ] = "markdown",
) -> str:
    """
    Generate documentation using filtered prompt suggestions.

    Only prompts related to documentation will be suggested for docs_prompt.
    """
    return f"Generating documentation using '{docs_prompt}' in {output_format} format"


async def main():
    """Run the completion demo server."""
    print("🎯 FastMCP Completion Demo Server")
    print("=====================================")
    print()
    print("This server demonstrates FastMCP's type annotation completion system.")
    print("Available components for completion:")
    print()

    # List available prompts
    prompts = server._prompt_manager.list_prompts()
    print(f"📝 Prompts ({len(prompts)}):")
    for prompt in prompts:
        print(f"  - {prompt.key}")
    print()

    # List available resources
    resources = server._resource_manager.list_resources()
    print(f"📄 Resources ({len(resources)}):")
    for resource in resources:
        print(f"  - {resource.uri}")
    print()

    # List available resource templates
    templates = server._resource_manager.list_resource_templates()
    print(f"🗂️  Resource Templates ({len(templates)}):")
    for template in templates:
        print(f"  - {template.uri_template}")
    print()

    print(
        "💡 Try using MCP clients with completion support to see the autocomplete in action!"
    )
    print("   The completion providers will suggest actual FastMCP components.")
    print()

    # Keep server running
    await asyncio.Future()  # Run forever


if __name__ == "__main__":
    asyncio.run(main())
