import mcp.types

from fastmcp import Client, FastMCP
from fastmcp.resources import ResourceTemplate


class TestCompletion:
    async def test_completion_handler_registration(self):
        """Test that completion handlers are registered correctly."""
        server = FastMCP()

        @server.completion("prompt", "test_prompt", "arg1")
        async def complete_prompt_arg(partial: str) -> list[str]:
            return ["option1", "option2", "option3"]

        # Check that handler was registered
        handler_key = "prompt:test_prompt:arg1"
        assert handler_key in server._completion_handlers

        # Test the handler function directly
        result = await server._completion_handlers[handler_key]("test")
        assert result == ["option1", "option2", "option3"]

    async def test_completion_for_prompt(self):
        """Test completion functionality for prompts."""
        server = FastMCP()

        @server.prompt
        async def analyze_data(dataset: str, analysis_type: str) -> str:
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

        async with Client(server) as client:
            # Test dataset completion with no partial
            result = await client.complete(
                mcp.types.PromptReference(type="ref/prompt", name="analyze_data"),
                {"name": "dataset", "value": ""},
            )
            assert result.values == ["customers", "products", "sales", "inventory"]
            assert result.total == 4

            # Test dataset completion with partial
            result = await client.complete(
                mcp.types.PromptReference(type="ref/prompt", name="analyze_data"),
                {"name": "dataset", "value": "c"},
            )
            assert result.values == ["customers"]
            assert result.total == 1

            # Test analysis_type completion
            result = await client.complete(
                mcp.types.PromptReference(type="ref/prompt", name="analyze_data"),
                {"name": "analysis_type", "value": "s"},
            )
            assert result.values == ["statistical"]
            assert result.total == 1

    async def test_completion_for_resource_template(self):
        """Test completion functionality for resource templates."""
        server = FastMCP()

        # Add a resource template
        file_template = ResourceTemplate(
            uri_template="file:///{path}",
            name="File Template",
            description="Template for file resources",
            parameters={},
        )
        server.add_template(file_template)

        @server.completion("resource_template", "file:///{path}", "path")
        async def complete_file_path(partial: str) -> list[str]:
            files = ["config.json", "data.csv", "readme.txt", "script.py"]
            if not partial:
                return files
            return [f for f in files if f.startswith(partial.lower())]

        async with Client(server) as client:
            # Test file path completion with no partial
            result = await client.complete(
                mcp.types.ResourceTemplateReference(
                    type="ref/resource", uri="file:///{path}"
                ),
                {"name": "path", "value": ""},
            )
            assert result.values == [
                "config.json",
                "data.csv",
                "readme.txt",
                "script.py",
            ]
            assert result.total == 4

            # Test file path completion with partial
            result = await client.complete(
                mcp.types.ResourceTemplateReference(
                    type="ref/resource", uri="file:///{path}"
                ),
                {"name": "path", "value": "c"},
            )
            assert result.values == ["config.json"]
            assert result.total == 1

    async def test_completion_for_wiki_template(self):
        """Test completion functionality for wiki resource templates."""
        server = FastMCP()

        # Add a wiki resource template
        wiki_template = ResourceTemplate(
            uri_template="wiki:///{org}/{project}",
            name="Wiki Template",
            description="Template for wiki resources",
            parameters={},
        )
        server.add_template(wiki_template)

        @server.completion("resource_template", "wiki:///{org}/{project}", "org")
        async def complete_org(partial: str) -> list[str]:
            orgs = ["engineering", "marketing", "sales", "hr"]
            if not partial:
                return orgs
            return [o for o in orgs if o.startswith(partial.lower())]

        @server.completion("resource_template", "wiki:///{org}/{project}", "project")
        async def complete_project(partial: str) -> list[str]:
            projects = ["webapp", "mobile", "api", "docs"]
            if not partial:
                return projects
            return [p for p in projects if p.startswith(partial.lower())]

        async with Client(server) as client:
            # Test org completion
            result = await client.complete(
                mcp.types.ResourceTemplateReference(
                    type="ref/resource", uri="wiki:///{org}/{project}"
                ),
                {"name": "org", "value": ""},
            )
            assert result.values == ["engineering", "marketing", "sales", "hr"]
            assert result.total == 4

            # Test project completion with partial
            result = await client.complete(
                mcp.types.ResourceTemplateReference(
                    type="ref/resource", uri="wiki:///{org}/{project}"
                ),
                {"name": "project", "value": "a"},
            )
            assert result.values == ["api"]
            assert result.total == 1

    async def test_completion_limit_100_items(self):
        """Test that completion results are limited to 100 items."""
        server = FastMCP()

        @server.completion("prompt", "test_prompt", "arg")
        async def complete_with_many_items(partial: str) -> list[str]:
            # Return 150 items to test the limit
            return [f"item_{i:03d}" for i in range(150)]

        async with Client(server) as client:
            result = await client.complete(
                mcp.types.PromptReference(type="ref/prompt", name="test_prompt"),
                {"name": "arg", "value": ""},
            )

            # Should be limited to 100 items
            assert len(result.values) == 100
            assert result.total == 100
            assert result.hasMore is True  # Indicates there might be more

            # Check that we got the first 100 items
            assert result.values[0] == "item_000"
            assert result.values[99] == "item_099"

    async def test_completion_no_handler_returns_empty(self):
        """Test that requests for non-existent completion handlers return empty results."""
        server = FastMCP()

        async with Client(server) as client:
            # Request completion for non-existent prompt
            result = await client.complete(
                mcp.types.PromptReference(
                    type="ref/prompt", name="non_existent_prompt"
                ),
                {"name": "arg", "value": "test"},
            )

            assert result.values == []
            assert result.total == 0
            assert result.hasMore is False

    async def test_completion_handler_error_handling(self):
        """Test that completion handler errors are handled gracefully."""
        server = FastMCP()

        @server.completion("prompt", "test_prompt", "arg")
        async def complete_with_error(partial: str) -> list[str]:
            raise ValueError("Handler error")

        async with Client(server) as client:
            # Should return empty completion when handler throws error
            result = await client.complete(
                mcp.types.PromptReference(type="ref/prompt", name="test_prompt"),
                {"name": "arg", "value": "test"},
            )

            assert result.values == []
            assert result.total == 0
            assert result.hasMore is False

    async def test_completion_empty_result_handling(self):
        """Test that completion handlers can return empty results."""
        server = FastMCP()

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

    async def test_completion_none_result_handling(self):
        """Test that completion handlers returning None are handled correctly."""
        server = FastMCP()

        @server.completion("prompt", "test_prompt", "arg")
        async def complete_none(partial: str) -> list[str]:
            return None  # type: ignore

        async with Client(server) as client:
            result = await client.complete(
                mcp.types.PromptReference(type="ref/prompt", name="test_prompt"),
                {"name": "arg", "value": "test"},
            )

            assert result.values == []
            assert result.total == 0
            assert result.hasMore is False

    async def test_multiple_completion_handlers(self):
        """Test that multiple completion handlers for different arguments work correctly."""
        server = FastMCP()

        @server.completion("prompt", "test_prompt", "arg1")
        async def complete_arg1(partial: str) -> list[str]:
            return ["arg1_option1", "arg1_option2"]

        @server.completion("prompt", "test_prompt", "arg2")
        async def complete_arg2(partial: str) -> list[str]:
            return ["arg2_option1", "arg2_option2", "arg2_option3"]

        @server.completion("prompt", "another_prompt", "arg1")
        async def complete_another_arg1(partial: str) -> list[str]:
            return ["another_option1", "another_option2"]

        async with Client(server) as client:
            # Test first prompt, arg1
            result = await client.complete(
                mcp.types.PromptReference(type="ref/prompt", name="test_prompt"),
                {"name": "arg1", "value": ""},
            )
            assert result.values == ["arg1_option1", "arg1_option2"]

            # Test first prompt, arg2
            result = await client.complete(
                mcp.types.PromptReference(type="ref/prompt", name="test_prompt"),
                {"name": "arg2", "value": ""},
            )
            assert result.values == ["arg2_option1", "arg2_option2", "arg2_option3"]

            # Test second prompt, arg1
            result = await client.complete(
                mcp.types.PromptReference(type="ref/prompt", name="another_prompt"),
                {"name": "arg1", "value": ""},
            )
            assert result.values == ["another_option1", "another_option2"]

    async def test_completion_handler_key_construction(self):
        """Test that completion handler keys are constructed correctly for different reference types."""
        server = FastMCP()

        @server.completion("resource", "file:///{path}", "path")
        async def complete_resource(partial: str) -> list[str]:
            return ["resource_test"]

        @server.completion("resource_template", "wiki:///{org}/{project}", "org")
        async def complete_template(partial: str) -> list[str]:
            return ["template_test"]

        @server.completion("prompt", "test_prompt", "arg")
        async def complete_prompt(partial: str) -> list[str]:
            return ["prompt_test"]

        # Verify the correct handler keys were created
        assert "resource:file:///{path}:path" in server._completion_handlers
        assert (
            "resource_template:wiki:///{org}/{project}:org"
            in server._completion_handlers
        )
        assert "prompt:test_prompt:arg" in server._completion_handlers
