import mcp.types
import pytest

from fastmcp import Client, FastMCP
from fastmcp.resources import ResourceTemplate


@pytest.fixture
def completion_server():
    """Fixture that creates a FastMCP server with completion handlers."""
    server = FastMCP("CompletionTestServer")

    # Add a prompt with completion
    @server.prompt
    async def analyze_data(dataset: str, analysis_type: str) -> str:
        """Analyze data with specified type."""
        return f"Analyzing {dataset} with {analysis_type}"

    @server.completion("prompt", "analyze_data", "dataset")
    async def complete_dataset(partial: str) -> list[str]:
        datasets = ["customers", "products", "sales", "inventory"]
        if not partial:
            return datasets
        return [d for d in datasets if d.startswith(partial.lower())]

    @server.completion("prompt", "analyze_data", "analysis_type")
    async def complete_analysis_type(partial: str) -> list[str]:
        types = ["statistical", "trend", "comparative", "predictive"]
        if not partial:
            return types
        return [t for t in types if t.startswith(partial.lower())]

    # Add a resource template with completion
    file_template = ResourceTemplate(
        uri_template="file:///{path}",
        name="File Resource",
        description="Access files",
        parameters={},
    )
    server.add_template(file_template)

    @server.completion("resource_template", "file:///{path}", "path")
    async def complete_file_path(partial: str) -> list[str]:
        files = ["config.json", "data.csv", "readme.txt", "script.py"]
        if not partial:
            return files
        return [f for f in files if f.startswith(partial.lower())]

    return server


class TestClientCompletion:
    """Test client completion methods."""

    async def test_complete_prompt_no_partial(self, completion_server):
        """Test completion for prompt with no partial input."""
        async with Client(completion_server) as client:
            result = await client.complete(
                mcp.types.PromptReference(type="ref/prompt", name="analyze_data"),
                {"name": "dataset", "value": ""},
            )

            assert isinstance(result, mcp.types.Completion)
            assert result.values == ["customers", "products", "sales", "inventory"]
            assert result.total == 4
            assert result.hasMore is False

    async def test_complete_prompt_with_partial(self, completion_server):
        """Test completion for prompt with partial input."""
        async with Client(completion_server) as client:
            result = await client.complete(
                mcp.types.PromptReference(type="ref/prompt", name="analyze_data"),
                {"name": "dataset", "value": "c"},
            )

            assert isinstance(result, mcp.types.Completion)
            assert result.values == ["customers"]
            assert result.total == 1
            assert result.hasMore is False

    async def test_complete_mcp_prompt(self, completion_server):
        """Test complete_mcp method returns full MCP result."""
        async with Client(completion_server) as client:
            result = await client.complete_mcp(
                mcp.types.PromptReference(type="ref/prompt", name="analyze_data"),
                {"name": "analysis_type", "value": "s"},
            )

            assert isinstance(result, mcp.types.CompleteResult)
            assert isinstance(result.completion, mcp.types.Completion)
            assert result.completion.values == ["statistical"]
            assert result.completion.total == 1
            assert result.completion.hasMore is False

    async def test_complete_resource_template_no_partial(self, completion_server):
        """Test completion for resource template with no partial input."""
        async with Client(completion_server) as client:
            result = await client.complete(
                mcp.types.ResourceTemplateReference(
                    type="ref/resource", uri="file:///{path}"
                ),
                {"name": "path", "value": ""},
            )

            assert isinstance(result, mcp.types.Completion)
            assert result.values == [
                "config.json",
                "data.csv",
                "readme.txt",
                "script.py",
            ]
            assert result.total == 4
            assert result.hasMore is False

    async def test_complete_resource_template_with_partial(self, completion_server):
        """Test completion for resource template with partial input."""
        async with Client(completion_server) as client:
            result = await client.complete(
                mcp.types.ResourceTemplateReference(
                    type="ref/resource", uri="file:///{path}"
                ),
                {"name": "path", "value": "c"},
            )

            assert isinstance(result, mcp.types.Completion)
            assert result.values == ["config.json"]
            assert result.total == 1
            assert result.hasMore is False

    async def test_complete_nonexistent_handler(self, completion_server):
        """Test completion for non-existent handler returns empty."""
        async with Client(completion_server) as client:
            result = await client.complete(
                mcp.types.PromptReference(type="ref/prompt", name="nonexistent"),
                {"name": "arg", "value": "test"},
            )

            assert isinstance(result, mcp.types.Completion)
            assert result.values == []
            assert result.total == 0
            assert result.hasMore is False

    async def test_complete_nonexistent_argument(self, completion_server):
        """Test completion for existing prompt but non-existent argument."""
        async with Client(completion_server) as client:
            result = await client.complete(
                mcp.types.PromptReference(type="ref/prompt", name="analyze_data"),
                {"name": "nonexistent_arg", "value": "test"},
            )

            assert isinstance(result, mcp.types.Completion)
            assert result.values == []
            assert result.total == 0
            assert result.hasMore is False

    async def test_complete_multiple_prompts_same_argument(self):
        """Test completions for multiple prompts with same argument name."""
        server = FastMCP("MultiPromptTest")

        @server.prompt
        async def prompt1(dataset: str) -> str:
            return f"Prompt1: {dataset}"

        @server.prompt
        async def prompt2(dataset: str) -> str:
            return f"Prompt2: {dataset}"

        @server.completion("prompt", "prompt1", "dataset")
        async def complete1(partial: str) -> list[str]:
            return ["dataset1_a", "dataset1_b"]

        @server.completion("prompt", "prompt2", "dataset")
        async def complete2(partial: str) -> list[str]:
            return ["dataset2_x", "dataset2_y"]

        async with Client(server) as client:
            # Test first prompt
            result1 = await client.complete(
                mcp.types.PromptReference(type="ref/prompt", name="prompt1"),
                {"name": "dataset", "value": ""},
            )
            assert result1.values == ["dataset1_a", "dataset1_b"]

            # Test second prompt
            result2 = await client.complete(
                mcp.types.PromptReference(type="ref/prompt", name="prompt2"),
                {"name": "dataset", "value": ""},
            )
            assert result2.values == ["dataset2_x", "dataset2_y"]

    async def test_complete_case_insensitive_matching(self, completion_server):
        """Test that partial matching works case-insensitively."""
        async with Client(completion_server) as client:
            # Test uppercase partial
            result = await client.complete(
                mcp.types.PromptReference(type="ref/prompt", name="analyze_data"),
                {"name": "dataset", "value": "C"},
            )
            assert result.values == ["customers"]

            # Test mixed case partial
            result = await client.complete(
                mcp.types.PromptReference(type="ref/prompt", name="analyze_data"),
                {"name": "dataset", "value": "CuS"},
            )
            assert result.values == ["customers"]

    async def test_complete_empty_result(self):
        """Test completion handler that returns empty list."""
        server = FastMCP("EmptyResultTest")

        @server.prompt
        async def test_prompt(arg: str) -> str:
            return f"Test: {arg}"

        @server.completion("prompt", "test_prompt", "arg")
        async def complete_empty(partial: str) -> list[str]:
            return []

        async with Client(server) as client:
            result = await client.complete(
                mcp.types.PromptReference(type="ref/prompt", name="test_prompt"),
                {"name": "arg", "value": "test"},
            )

            assert result.values == []
            assert result.total == 0
            assert result.hasMore is False

    async def test_complete_handler_error(self):
        """Test completion handler that throws an error."""
        server = FastMCP("ErrorTest")

        @server.prompt
        async def test_prompt(arg: str) -> str:
            return f"Test: {arg}"

        @server.completion("prompt", "test_prompt", "arg")
        async def complete_error(partial: str) -> list[str]:
            raise ValueError("Test error")

        async with Client(server) as client:
            # Should return empty completion on error
            result = await client.complete(
                mcp.types.PromptReference(type="ref/prompt", name="test_prompt"),
                {"name": "arg", "value": "test"},
            )

            assert result.values == []
            assert result.total == 0
            assert result.hasMore is False

    async def test_complete_large_result_limited(self):
        """Test completion with many results is limited to 100 items."""
        server = FastMCP("LimitTest")

        @server.prompt
        async def test_prompt(arg: str) -> str:
            return f"Test: {arg}"

        @server.completion("prompt", "test_prompt", "arg")
        async def complete_many(partial: str) -> list[str]:
            # Return 200 items to test the 100-item limit
            return [f"item_{i:03d}" for i in range(200)]

        async with Client(server) as client:
            result = await client.complete(
                mcp.types.PromptReference(type="ref/prompt", name="test_prompt"),
                {"name": "arg", "value": ""},
            )

            assert len(result.values) == 100
            assert result.total == 100
            assert result.hasMore is True  # Indicates more results available
            assert result.values[0] == "item_000"
            assert result.values[99] == "item_099"

    async def test_complete_unicode_support(self):
        """Test completion with unicode characters."""
        server = FastMCP("UnicodeTest")

        @server.prompt
        async def test_prompt(lang: str) -> str:
            return f"Language: {lang}"

        @server.completion("prompt", "test_prompt", "lang")
        async def complete_languages(partial: str) -> list[str]:
            languages = ["English", "Français", "Español", "中文", "日本語", "العربية"]
            if not partial:
                return languages
            return [
                lang for lang in languages if lang.lower().startswith(partial.lower())
            ]

        async with Client(server) as client:
            # Test no partial
            result = await client.complete(
                mcp.types.PromptReference(type="ref/prompt", name="test_prompt"),
                {"name": "lang", "value": ""},
            )
            assert "中文" in result.values
            assert "العربية" in result.values

            # Test partial matching
            result = await client.complete(
                mcp.types.PromptReference(type="ref/prompt", name="test_prompt"),
                {"name": "lang", "value": "f"},
            )
            assert result.values == ["Français"]
