#!/usr/bin/env python3
"""
Proof of concept for type annotation-based completion system.

This explores the feedback suggestion to use type annotations instead of
string-based decorator coupling for FastMCP completions.
"""

from typing import Annotated, Literal

from pydantic import Field

from fastmcp import FastMCP

# Current approach (problematic):
# @server.completion("prompt", "analyze_data", "dataset")
# async def complete_dataset(partial: str) -> list[str]: ...


# Proposed approach using type annotations:


class FileCompletion:
    """Completion provider for file paths."""

    async def __call__(self, partial: str) -> list[str]:
        # Filesystem-based completion logic
        example_files = ["config.json", "data.csv", "readme.txt", "script.py"]
        if not partial:
            return example_files
        return [f for f in example_files if f.lower().startswith(partial.lower())]


class DatasetCompletion:
    """Completion provider for dataset names."""

    async def __call__(self, partial: str) -> list[str]:
        datasets = ["customer_data", "sales_records", "inventory_logs", "user_activity"]
        if not partial:
            return datasets
        return [d for d in datasets if d.lower().startswith(partial.lower())]


class AnalysisCompletion:
    """Completion provider for analysis types."""

    async def __call__(self, partial: str) -> list[str]:
        analysis_types = ["statistical", "trend", "comparative", "predictive"]
        if not partial:
            return analysis_types
        return [t for t in analysis_types if t.lower().startswith(partial.lower())]


# Type annotation-based approach (NEW):

server = FastMCP("Type Annotation Demo")


@server.prompt
async def analyze_data(
    dataset: Annotated[str, DatasetCompletion()],
    analysis_type: Annotated[str, AnalysisCompletion()],
    output_format: Annotated[
        Literal["json", "csv", "xml"], Field(description="Output format")
    ],
) -> str:
    """Analyze a dataset with the specified analysis type and output format."""
    return f"Analyzing {dataset} using {analysis_type} analysis"


# Alternative with Field + completion:
@server.prompt
async def process_file(
    path: Annotated[str, Field(description="File path to process"), FileCompletion()],
    mode: Annotated[
        Literal["read", "write", "append"], Field(description="File access mode")
    ],
) -> str:
    """Process a file at the given path."""
    return f"Processing {path} in {mode} mode"


# More complex completion with multiple annotations:
class FuzzyCompletion:
    """Fuzzy string matching completion."""

    def __init__(self, choices: list[str]):
        self.choices = choices

    async def __call__(self, partial: str) -> list[str]:
        if not partial:
            return self.choices
        # Simple fuzzy matching
        return [c for c in self.choices if partial.lower() in c.lower()]


@server.tool
async def search_documents(
    query: Annotated[str, Field(description="Search query")],
    category: Annotated[
        str,
        Field(description="Document category"),
        FuzzyCompletion(["all", "documents", "emails", "presentations", "code"]),
    ],
    limit: Annotated[int, Field(description="Max results", ge=1, le=100)] = 10,
) -> str:
    """Search documents with fuzzy category completion."""
    return f"Searching for '{query}' in '{category}' (limit: {limit})"


# Resource template with type annotations:

# This would require changes to ResourceTemplate to support type annotations
# in the parameters field, but the concept would be:

# wiki_template = ResourceTemplate(
#     uri_template="wiki:///{organization}/{project}",
#     name="Wiki Resource",
#     description="Access organizational wiki content",
#     parameters={
#         "organization": Annotated[str, OrganizationCompletion()],
#         "project": Annotated[str, ProjectCompletion()]
#     }
# )

if __name__ == "__main__":
    print("Type annotation-based completion concept")
    print("This demonstrates how completions could be attached directly to arguments")
    print("instead of using string-based decorator coupling.")
