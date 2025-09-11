#!/usr/bin/env python3
"""
Demo server showcasing FastMCP completion functionality.

This example demonstrates how to use the @completion decorator to provide
autocomplete suggestions for resource templates and prompts.
"""

import asyncio

from fastmcp import FastMCP
from fastmcp.resources import ResourceTemplate

# Create the FastMCP server
server = FastMCP("Completion Demo Server")


# Example 1: File path completion for a resource template
file_template = ResourceTemplate(
    uri_template="file:///{path}",
    name="File Resource",
    description="Access files on the local system",
    parameters={},
)
server.add_template(file_template)


@server.completion("resource_template", "file:///{path}", "path")
async def complete_file_path(partial: str) -> list[str]:
    """Provide file path completions based on partial input."""
    # In a real implementation, you'd scan the filesystem
    # For demo purposes, we return some example files
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

    # Return files that start with the partial input
    return [f for f in example_files if f.lower().startswith(partial.lower())]


# Example 2: Prompt with multiple completion handlers
@server.prompt
async def analyze_data(
    dataset: str, analysis_type: str, output_format: str = "json"
) -> str:
    """Analyze a dataset with the specified analysis type and output format."""
    return f"Analyzing {dataset} using {analysis_type} analysis, outputting as {output_format}"


@server.completion("prompt", "analyze_data", "dataset")
async def complete_dataset(partial: str) -> list[str]:
    """Provide dataset name completions."""
    datasets = [
        "customer_data",
        "sales_records",
        "inventory_logs",
        "user_activity",
        "financial_reports",
        "survey_responses",
    ]

    if not partial:
        return datasets

    return [d for d in datasets if d.lower().startswith(partial.lower())]


@server.completion("prompt", "analyze_data", "analysis_type")
async def complete_analysis_type(partial: str) -> list[str]:
    """Provide analysis type completions."""
    analysis_types = [
        "statistical",
        "trend",
        "comparative",
        "predictive",
        "correlation",
        "regression",
        "clustering",
        "classification",
    ]

    if not partial:
        return analysis_types

    return [t for t in analysis_types if t.lower().startswith(partial.lower())]


@server.completion("prompt", "analyze_data", "output_format")
async def complete_output_format(partial: str) -> list[str]:
    """Provide output format completions."""
    formats = ["json", "csv", "xml", "yaml", "html", "pdf"]

    if not partial:
        return formats

    return [f for f in formats if f.lower().startswith(partial.lower())]


# Example 3: Dynamic completions (context-aware)
wiki_template = ResourceTemplate(
    uri_template="wiki:///{organization}/{project}",
    name="Wiki Resource",
    description="Access organizational wiki content",
    parameters={},
)
server.add_template(wiki_template)


@server.completion(
    "resource_template", "wiki:///{organization}/{project}", "organization"
)
async def complete_organization(partial: str) -> list[str]:
    """Provide organization completions."""
    orgs = ["engineering", "marketing", "sales", "support", "legal", "hr"]

    if not partial:
        return orgs

    return [org for org in orgs if org.lower().startswith(partial.lower())]


@server.completion("resource_template", "wiki:///{organization}/{project}", "project")
async def complete_project(partial: str) -> list[str]:
    """
    Provide project completions.

    Note: In a real implementation, you might filter projects based on the
    selected organization using context or parameter passing.
    """
    projects = [
        "web-app",
        "mobile-app",
        "api-service",
        "documentation",
        "infrastructure",
        "analytics-platform",
    ]

    if not partial:
        return projects

    return [p for p in projects if p.lower().startswith(partial.lower())]


# Example 4: Tool with completion (shows completion works across all MCP object types)
@server.tool
async def search_documents(query: str, category: str = "all") -> str:
    """Search documents by query and category."""
    return f"Searching for '{query}' in category '{category}'"


@server.prompt
async def search_prompt(query: str, category: str) -> str:
    """Search documents using a prompt interface."""
    return f"Search query: {query}, Category: {category}"


@server.completion("prompt", "search_prompt", "category")
async def complete_search_category(partial: str) -> list[str]:
    """Provide search category completions."""
    categories = [
        "all",
        "documents",
        "emails",
        "presentations",
        "spreadsheets",
        "images",
        "videos",
        "code",
    ]

    if not partial:
        return categories

    return [c for c in categories if c.lower().startswith(partial.lower())]


if __name__ == "__main__":
    print("🚀 Starting Completion Demo Server...")
    print("")
    print("This server demonstrates FastMCP's completion functionality.")
    print("Try using completion requests with:")
    print("")
    print("Resource Templates:")
    print("  - file:///{path} (path argument)")
    print("  - wiki:///{organization}/{project} (organization, project arguments)")
    print("")
    print("Prompts:")
    print("  - analyze_data (dataset, analysis_type, output_format arguments)")
    print("  - search_prompt (category argument)")
    print("")
    print("Press Ctrl+C to stop the server")

    # Run the server
    asyncio.run(server.run_async())
