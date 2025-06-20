import json
import logging
import uuid
from typing import Annotated, Any

import pydantic_core
import pytest
from mcp.types import ImageContent
from pydantic import BaseModel

from fastmcp import Context, FastMCP
from fastmcp.exceptions import NotFoundError, ToolError
from fastmcp.tools import FunctionTool, ToolManager
from fastmcp.tools.tool import Tool
from fastmcp.utilities.tests import temporary_settings
from fastmcp.utilities.types import Image


class TestAddTools:
    async def test_basic_function(self):
        """Test registering and running a basic function."""

        def add(a: int, b: int) -> int:
            """Add two numbers."""
            return a + b

        manager = ToolManager()
        tool = Tool.from_function(add)
        manager.add_tool(tool)

        tool = await manager.get_tool("add")
        assert tool is not None
        assert tool.name == "add"
        assert tool.description == "Add two numbers."
        assert tool.parameters["properties"]["a"]["type"] == "integer"
        assert tool.parameters["properties"]["b"]["type"] == "integer"

    async def test_async_function(self):
        """Test registering and running an async function."""

        async def fetch_data(url: str) -> str:
            """Fetch data from URL."""
            return f"Data from {url}"

        manager = ToolManager()
        tool = Tool.from_function(fetch_data)
        manager.add_tool(tool)

        tool = await manager.get_tool("fetch_data")
        assert tool is not None
        assert tool.name == "fetch_data"
        assert tool.description == "Fetch data from URL."
        assert tool.parameters["properties"]["url"]["type"] == "string"

    async def test_pydantic_model_function(self):
        """Test registering a function that takes a Pydantic model."""

        class UserInput(BaseModel):
            name: str
            age: int

        def create_user(user: UserInput, flag: bool) -> dict:
            """Create a new user."""
            return {"id": 1, **user.model_dump()}

        manager = ToolManager()
        tool = Tool.from_function(create_user)
        manager.add_tool(tool)

        tool = await manager.get_tool("create_user")
        assert tool is not None
        assert tool.name == "create_user"
        assert tool.description == "Create a new user."
        assert "name" in tool.parameters["$defs"]["UserInput"]["properties"]
        assert "age" in tool.parameters["$defs"]["UserInput"]["properties"]
        assert "flag" in tool.parameters["properties"]

    async def test_callable_object(self):
        class Adder:
            """Adds two numbers."""

            def __call__(self, x: int, y: int) -> int:
                """ignore this"""
                return x + y

        manager = ToolManager()
        tool = Tool.from_function(Adder())
        manager.add_tool(tool)

        tool = await manager.get_tool("Adder")
        assert tool is not None
        assert tool.name == "Adder"
        assert tool.description == "Adds two numbers."
        assert len(tool.parameters["properties"]) == 2
        assert tool.parameters["properties"]["x"]["type"] == "integer"
        assert tool.parameters["properties"]["y"]["type"] == "integer"

    async def test_async_callable_object(self):
        class Adder:
            """Adds two numbers."""

            async def __call__(self, x: int, y: int) -> int:
                """ignore this"""
                return x + y

        manager = ToolManager()
        tool = Tool.from_function(Adder())
        manager.add_tool(tool)

        tool = await manager.get_tool("Adder")
        assert tool is not None
        assert tool.name == "Adder"
        assert tool.description == "Adds two numbers."
        assert len(tool.parameters["properties"]) == 2
        assert tool.parameters["properties"]["x"]["type"] == "integer"
        assert tool.parameters["properties"]["y"]["type"] == "integer"

    async def test_tool_with_image_return(self):
        def image_tool(data: bytes) -> Image:
            return Image(data=data)

        manager = ToolManager()
        tool = Tool.from_function(image_tool)
        manager.add_tool(tool)

        tool = await manager.get_tool("image_tool")
        result = await tool.run({"data": "test.png"})
        assert tool.parameters["properties"]["data"]["type"] == "string"
        assert isinstance(result[0], ImageContent)

    def test_add_noncallable_tool(self):
        manager = ToolManager()
        with pytest.raises(TypeError, match="not a callable object"):
            tool = Tool.from_function(1)  # type: ignore
            manager.add_tool(tool)

    def test_add_lambda(self):
        manager = ToolManager()
        tool = Tool.from_function(lambda x: x, name="my_tool")
        manager.add_tool(tool)
        assert tool.name == "my_tool"

    def test_add_lambda_with_no_name(self):
        manager = ToolManager()
        with pytest.raises(
            ValueError, match="You must provide a name for lambda functions"
        ):
            tool = Tool.from_function(lambda x: x)
            manager.add_tool(tool)

    async def test_remove_tool_successfully(self):
        """Test removing an added tool by key."""
        manager = ToolManager()

        def add(a: int, b: int) -> int:
            return a + b

        tool = Tool.from_function(add)
        manager.add_tool(tool)
        assert await manager.get_tool("add") is not None

        manager.remove_tool("add")
        with pytest.raises(NotFoundError):
            await manager.get_tool("add")

    def test_remove_tool_missing_key(self):
        """Test removing a tool that does not exist raises NotFoundError."""
        manager = ToolManager()
        with pytest.raises(NotFoundError, match="Tool 'missing' not found"):
            manager.remove_tool("missing")

    async def test_warn_on_duplicate_tools(self, caplog):
        """Test warning on duplicate tools."""
        manager = ToolManager(duplicate_behavior="warn")

        def test_fn(x: int) -> int:
            return x

        tool1 = Tool.from_function(test_fn, name="test_tool")
        manager.add_tool(tool1)
        tool2 = Tool.from_function(test_fn, name="test_tool")
        manager.add_tool(tool2)

        assert "Tool already exists: test_tool" in caplog.text
        # Should have the tool
        assert await manager.get_tool("test_tool") is not None

    def test_disable_warn_on_duplicate_tools(self, caplog):
        """Test disabling warning on duplicate tools."""

        def f(x: int) -> int:
            return x

        manager = ToolManager(duplicate_behavior="ignore")
        tool1 = Tool.from_function(f)
        manager.add_tool(tool1)
        with caplog.at_level(logging.WARNING):
            tool2 = Tool.from_function(f)
            manager.add_tool(tool2)
            assert "Tool already exists: f" not in caplog.text

    def test_error_on_duplicate_tools(self):
        """Test error on duplicate tools."""
        manager = ToolManager(duplicate_behavior="error")

        def test_fn(x: int) -> int:
            return x

        tool1 = Tool.from_function(test_fn, name="test_tool")
        manager.add_tool(tool1)

        with pytest.raises(ValueError, match="Tool already exists: test_tool"):
            tool2 = Tool.from_function(test_fn, name="test_tool")
            manager.add_tool(tool2)

    async def test_replace_duplicate_tools(self):
        """Test replacing duplicate tools."""
        manager = ToolManager(duplicate_behavior="replace")

        def original_fn(x: int) -> int:
            return x

        def replacement_fn(x: int) -> int:
            return x + 1

        tool1 = Tool.from_function(original_fn, name="test_tool")
        manager.add_tool(tool1)
        result = Tool.from_function(replacement_fn, name="test_tool")
        manager.add_tool(result)

        # Should have replaced with the new tool
        tool = await manager.get_tool("test_tool")
        assert tool is not None
        assert isinstance(tool, FunctionTool)
        assert tool.fn.__name__ == "replacement_fn"

    async def test_ignore_duplicate_tools(self):
        """Test ignoring duplicate tools."""
        manager = ToolManager(duplicate_behavior="ignore")

        def original_fn(x: int) -> int:
            return x

        def replacement_fn(x: int) -> int:
            return x * 2

        tool1 = Tool.from_function(original_fn, name="test_tool")
        manager.add_tool(tool1)
        result = Tool.from_function(replacement_fn, name="test_tool")
        manager.add_tool(result)

        # Should keep the original
        tool = await manager.get_tool("test_tool")
        assert tool is not None
        assert isinstance(tool, FunctionTool)
        assert tool.fn.__name__ == "original_fn"
        # Result should be the original tool
        assert isinstance(result, FunctionTool)
        assert result.fn.__name__ == "replacement_fn"


class TestToolTags:
    """Test functionality related to tool tags."""

    async def test_add_tool_with_tags(self):
        """Test adding tags to a tool."""

        def example_tool(x: int) -> int:
            """An example tool with tags."""
            return x * 2

        manager = ToolManager()
        tool = Tool.from_function(example_tool, tags={"math", "utility"})
        manager.add_tool(tool)

        assert tool.tags == {"math", "utility"}
        tool = await manager.get_tool("example_tool")
        assert tool is not None
        assert tool.tags == {"math", "utility"}

    async def test_add_tool_with_empty_tags(self):
        """Test adding a tool with empty tags set."""

        def example_tool(x: int) -> int:
            """An example tool with empty tags."""
            return x * 2

        manager = ToolManager()
        tool = Tool.from_function(example_tool, tags=set())
        manager.add_tool(tool)

        assert tool.tags == set()

    async def test_add_tool_with_none_tags(self):
        """Test adding a tool with None tags."""

        def example_tool(x: int) -> int:
            """An example tool with None tags."""
            return x * 2

        manager = ToolManager()
        tool = Tool.from_function(example_tool, tags=None)
        manager.add_tool(tool)

        assert tool.tags == set()

    async def test_list_tools_with_tags(self):
        """Test listing tools with specific tags."""

        def math_tool(x: int) -> int:
            """A math tool."""
            return x * 2

        def string_tool(x: str) -> str:
            """A string tool."""
            return x.upper()

        def mixed_tool(x: int) -> str:
            """A tool with multiple tags."""
            return str(x)

        manager = ToolManager()
        tool1 = Tool.from_function(math_tool, tags={"math"})
        manager.add_tool(tool1)
        tool2 = Tool.from_function(string_tool, tags={"string", "utility"})
        manager.add_tool(tool2)
        tool3 = Tool.from_function(mixed_tool, tags={"math", "utility", "string"})
        manager.add_tool(tool3)

        # Check if we can filter by tags when listing tools
        math_tools = [
            tool for tool in (await manager.get_tools()).values() if "math" in tool.tags
        ]
        assert len(math_tools) == 2
        assert {tool.name for tool in math_tools} == {"math_tool", "mixed_tool"}

        utility_tools = [
            tool
            for tool in (await manager.get_tools()).values()
            if "utility" in tool.tags
        ]
        assert len(utility_tools) == 2
        assert {tool.name for tool in utility_tools} == {"string_tool", "mixed_tool"}


class TestCallTools:
    async def test_call_tool(self):
        def add(a: int, b: int) -> int:
            """Add two numbers."""
            return a + b

        manager = ToolManager()
        tool = Tool.from_function(add)
        manager.add_tool(tool)
        result = await manager.call_tool("add", {"a": 1, "b": 2})

        assert result[0].text == "3"  # type: ignore[attr-defined]

    async def test_call_async_tool(self):
        async def double(n: int) -> int:
            """Double a number."""
            return n * 2

        manager = ToolManager()
        tool = Tool.from_function(double)
        manager.add_tool(tool)
        result = await manager.call_tool("double", {"n": 5})
        assert result[0].text == "10"  # type: ignore[attr-defined]

    async def test_call_tool_callable_object(self):
        class Adder:
            """Adds two numbers."""

            def __call__(self, x: int, y: int) -> int:
                """ignore this"""
                return x + y

        manager = ToolManager()
        tool = Tool.from_function(Adder())
        manager.add_tool(tool)
        result = await manager.call_tool("Adder", {"x": 1, "y": 2})
        assert result[0].text == "3"  # type: ignore[attr-defined]

    async def test_call_tool_callable_object_async(self):
        class Adder:
            """Adds two numbers."""

            async def __call__(self, x: int, y: int) -> int:
                """ignore this"""
                return x + y

        manager = ToolManager()
        tool = Tool.from_function(Adder())
        manager.add_tool(tool)
        result = await manager.call_tool("Adder", {"x": 1, "y": 2})
        assert result[0].text == "3"  # type: ignore[attr-defined]

    async def test_call_tool_with_default_args(self):
        def add(a: int, b: int = 1) -> int:
            """Add two numbers."""
            return a + b

        manager = ToolManager()
        tool = Tool.from_function(add)
        manager.add_tool(tool)
        result = await manager.call_tool("add", {"a": 1})

        assert result[0].text == "2"  # type: ignore[attr-defined]

    async def test_call_tool_with_missing_args(self):
        def add(a: int, b: int) -> int:
            """Add two numbers."""
            return a + b

        manager = ToolManager()
        tool = Tool.from_function(add)
        manager.add_tool(tool)
        with pytest.raises(ToolError):
            await manager.call_tool("add", {"a": 1})

    async def test_call_unknown_tool(self):
        manager = ToolManager()
        with pytest.raises(NotFoundError, match="Tool 'unknown' not found"):
            await manager.call_tool("unknown", {"a": 1})

    async def test_call_tool_with_list_int_input(self):
        def sum_vals(vals: list[int]) -> int:
            return sum(vals)

        manager = ToolManager()
        tool = Tool.from_function(sum_vals)
        manager.add_tool(tool)

        result = await manager.call_tool("sum_vals", {"vals": [1, 2, 3]})
        assert result[0].text == "6"  # type: ignore[attr-defined]

    async def test_call_tool_with_list_int_input_legacy_behavior(self):
        """Legacy behavior -- parse a stringified JSON object"""

        def sum_vals(vals: list[int]) -> int:
            return sum(vals)

        manager = ToolManager()
        tool = Tool.from_function(sum_vals)
        manager.add_tool(tool)
        # Try both with plain list and with JSON list

        with temporary_settings(tool_attempt_parse_json_args=True):
            result = await manager.call_tool("sum_vals", {"vals": "[1, 2, 3]"})
            assert result[0].text == "6"  # type: ignore[attr-defined]

    async def test_call_tool_with_list_str_or_str_input(self):
        def concat_strs(vals: list[str] | str) -> str:
            return vals if isinstance(vals, str) else "".join(vals)

        manager = ToolManager()
        tool = Tool.from_function(concat_strs)
        manager.add_tool(tool)

        # Try both with plain python object and with JSON list
        result = await manager.call_tool("concat_strs", {"vals": ["a", "b", "c"]})
        assert result[0].text == "abc"  # type: ignore[attr-defined]

        result = await manager.call_tool("concat_strs", {"vals": "a"})
        assert result[0].text == "a"  # type: ignore[attr-defined]

    async def test_call_tool_with_list_str_or_str_input_legacy_behavior(self):
        """Legacy behavior -- parse a stringified JSON object"""

        def concat_strs(vals: list[str] | str) -> str:
            return vals if isinstance(vals, str) else "".join(vals)

        manager = ToolManager()
        tool = Tool.from_function(concat_strs)
        manager.add_tool(tool)

        with temporary_settings(tool_attempt_parse_json_args=True):
            result = await manager.call_tool("concat_strs", {"vals": '["a", "b", "c"]'})
            assert result[0].text == "abc"  # type: ignore[attr-defined]

            result = await manager.call_tool("concat_strs", {"vals": '"a"'})
            assert result[0].text == "a"  # type: ignore[attr-defined]

    async def test_call_tool_with_complex_model(self):
        class MyShrimpTank(BaseModel):
            class Shrimp(BaseModel):
                name: str

            shrimp: list[Shrimp]
            x: None

        def name_shrimp(tank: MyShrimpTank, ctx: Context | None) -> list[str]:
            return [x.name for x in tank.shrimp]

        manager = ToolManager()
        tool = Tool.from_function(name_shrimp)
        manager.add_tool(tool)

        mcp = FastMCP()
        context = Context(fastmcp=mcp)

        with context:
            result = await manager.call_tool(
                "name_shrimp",
                {
                    "tank": {
                        "x": None,
                        "shrimp": [{"name": "rex"}, {"name": "gertrude"}],
                    }
                },
            )

        assert result[0].text == '[\n  "rex",\n  "gertrude"\n]'  # type: ignore[attr-defined]

    async def test_call_tool_with_custom_serializer(self):
        """Test that a custom serializer provided to FastMCP is used by tools."""

        def custom_serializer(data: Any) -> str:
            if isinstance(data, dict):
                return f"CUSTOM:{json.dumps(data)}"
            return json.dumps(data)

        # Instantiate FastMCP with the custom serializer
        mcp = FastMCP(tool_serializer=custom_serializer)
        manager = mcp._tool_manager

        @mcp.tool
        def get_data() -> dict:
            return {"key": "value", "number": 123}

        result = await manager.call_tool("get_data", {})
        assert result[0].text == 'CUSTOM:{"key": "value", "number": 123}'  # type: ignore[attr-defined]

    async def test_call_tool_with_list_result_custom_serializer(self):
        """Test that a custom serializer provided to FastMCP is used by tools that return lists."""

        def custom_serializer(data: Any) -> str:
            if isinstance(data, list):
                return f"CUSTOM:{json.dumps(data)}"
            return json.dumps(data)

        mcp = FastMCP(tool_serializer=custom_serializer)
        manager = mcp._tool_manager

        @mcp.tool
        def get_data() -> list[dict]:
            return [
                {"key": "value", "number": 123},
                {"key": "value2", "number": 456},
            ]

        result = await manager.call_tool("get_data", {})
        assert (
            result[0].text  # type: ignore[attr-defined]
            == 'CUSTOM:[{"key": "value", "number": 123}, {"key": "value2", "number": 456}]'  # type: ignore[attr-defined]
        )

    async def test_custom_serializer_fallback_on_error(self):
        """Test that a broken custom serializer gracefully falls back."""

        uuid_result = uuid.uuid4()

        def custom_serializer(data: Any) -> str:
            return json.dumps(data)

        mcp = FastMCP(tool_serializer=custom_serializer)
        manager = mcp._tool_manager

        @mcp.tool
        def get_data() -> uuid.UUID:
            return uuid_result

        result = await manager.call_tool("get_data", {})
        assert result[0].text == pydantic_core.to_json(uuid_result).decode()  # type: ignore[attr-defined]


class TestToolSchema:
    async def test_context_arg_excluded_from_schema(self):
        def something(a: int, ctx: Context) -> int:
            return a

        manager = ToolManager()
        tool = Tool.from_function(something)
        manager.add_tool(tool)
        assert "ctx" not in json.dumps(tool.parameters)
        assert "Context" not in json.dumps(tool.parameters)

    async def test_optional_context_arg_excluded_from_schema(self):
        def something(a: int, ctx: Context | None) -> int:
            return a

        manager = ToolManager()
        tool = Tool.from_function(something)
        manager.add_tool(tool)
        assert "ctx" not in json.dumps(tool.parameters)
        assert "Context" not in json.dumps(tool.parameters)

    async def test_annotated_context_arg_excluded_from_schema(self):
        def something(a: int, ctx: Annotated[Context | int | None, "ctx"]) -> int:
            return a

        manager = ToolManager()
        tool = Tool.from_function(something)
        manager.add_tool(tool)
        assert "ctx" not in json.dumps(tool.parameters)
        assert "Context" not in json.dumps(tool.parameters)


class TestContextHandling:
    """Test context handling in the tool manager."""

    def test_context_parameter_detection(self):
        """Test that context parameters are properly detected in
        Tool.from_function()."""

        def tool_with_context(x: int, ctx: Context) -> str:
            return str(x)

        manager = ToolManager()
        tool = Tool.from_function(tool_with_context)
        manager.add_tool(tool)

        def tool_without_context(x: int) -> str:
            return str(x)

        manager.add_tool(Tool.from_function(tool_without_context))

    async def test_context_injection(self):
        """Test that context is properly injected during tool execution."""

        def tool_with_context(x: int, ctx: Context) -> str:
            assert isinstance(ctx, Context)
            return str(x)

        manager = ToolManager()
        tool = Tool.from_function(tool_with_context)
        manager.add_tool(tool)

        mcp = FastMCP()
        context = Context(fastmcp=mcp)

        with context:
            result = await manager.call_tool("tool_with_context", {"x": 42})
            assert result[0].text == "42"  # type: ignore[attr-defined]

    async def test_context_injection_async(self):
        """Test that context is properly injected in async tools."""

        async def async_tool(x: int, ctx: Context) -> str:
            assert isinstance(ctx, Context)
            return str(x)

        manager = ToolManager()
        tool = Tool.from_function(async_tool)
        manager.add_tool(tool)

        mcp = FastMCP()
        context = Context(fastmcp=mcp)

        with context:
            result = await manager.call_tool("async_tool", {"x": 42})
            assert result[0].text == "42"  # type: ignore[attr-defined]

    async def test_context_optional(self):
        """Test that context is optional when calling tools."""

        def tool_with_context(x: int, ctx: Context | None) -> int:
            return x

        manager = ToolManager()
        tool = Tool.from_function(tool_with_context)
        manager.add_tool(tool)
        # Should not raise an error when context is not provided

        mcp = FastMCP()
        context = Context(fastmcp=mcp)

        with context:
            result = await manager.call_tool("tool_with_context", {"x": 42})
            assert result[0].text == "42"  # type: ignore[attr-defined]

    def test_parameterized_context_parameter_detection(self):
        """Test that context parameters are properly detected in
        Tool.from_function()."""

        def tool_with_context(x: int, ctx: Context) -> str:
            return str(x)

        manager = ToolManager()
        tool = Tool.from_function(tool_with_context)
        manager.add_tool(tool)

    def test_annotated_context_parameter_detection(self):
        def tool_with_context(x: int, ctx: Annotated[Context, "ctx"]) -> str:
            return str(x)

        manager = ToolManager()
        tool = Tool.from_function(tool_with_context)
        manager.add_tool(tool)

    def test_parameterized_union_context_parameter_detection(self):
        """Test that context parameters are properly detected in
        Tool.from_function()."""

        def tool_with_context(x: int, ctx: Context | None) -> str:
            return str(x)

        manager = ToolManager()
        tool = Tool.from_function(tool_with_context)
        manager.add_tool(tool)

    async def test_context_error_handling(self):
        """Test error handling when context injection fails."""

        def tool_with_context(x: int, ctx: Context) -> str:
            raise ValueError("Test error")

        manager = ToolManager()
        tool = Tool.from_function(tool_with_context)
        manager.add_tool(tool)

        mcp = FastMCP()
        context = Context(fastmcp=mcp)

        with context:
            with pytest.raises(
                ToolError, match="Error calling tool 'tool_with_context'"
            ):
                await manager.call_tool("tool_with_context", {"x": 42})


class TestCustomToolNames:
    """Test adding tools with custom names that differ from their function names."""

    async def test_add_tool_with_custom_name(self):
        """Test adding a tool with a custom name parameter using add_tool_from_fn."""

        def original_fn(x: int) -> int:
            return x * 2

        manager = ToolManager()
        tool = Tool.from_function(original_fn, name="custom_name")
        manager.add_tool(tool)

        # The tool is stored under the custom name and its .name is also set to custom_name
        assert await manager.get_tool("custom_name") is not None
        assert tool.name == "custom_name"
        assert isinstance(tool, FunctionTool)
        assert tool.fn.__name__ == "original_fn"
        # The tool should not be accessible via its original function name
        with pytest.raises(NotFoundError, match="Tool 'original_fn' not found"):
            await manager.get_tool("original_fn")

    async def test_add_tool_object_with_custom_key(self):
        """Test adding a Tool object with a custom key using add_tool()."""

        def fn(x: int) -> int:
            return x + 1

        # Create a tool with a specific name
        tool = Tool.from_function(fn, name="my_tool")
        manager = ToolManager()
        # Use with_key to create a new tool with the custom key
        tool_with_custom_key = tool.with_key("proxy_tool")
        manager.add_tool(tool_with_custom_key)
        # The tool is accessible under the key
        stored = await manager.get_tool("proxy_tool")
        assert stored is not None
        # But the tool's .name is unchanged
        assert stored.name == "my_tool"
        # The tool is not accessible under its original name
        with pytest.raises(NotFoundError, match="Tool 'my_tool' not found"):
            await manager.get_tool("my_tool")

    async def test_call_tool_with_custom_name(self):
        """Test calling a tool added with a custom name."""

        def multiply(a: int, b: int) -> int:
            """Multiply two numbers."""
            return a * b

        manager = ToolManager()
        tool = Tool.from_function(multiply, name="custom_multiply")
        manager.add_tool(tool)

        # Tool should be callable by its custom name
        result = await manager.call_tool("custom_multiply", {"a": 5, "b": 3})
        assert result[0].text == "15"  # type: ignore[attr-defined]

        # Original name should not be registered
        with pytest.raises(NotFoundError, match="Tool 'multiply' not found"):
            await manager.call_tool("multiply", {"a": 5, "b": 3})

    async def test_replace_tool_keeps_original_name(self):
        """Test that replacing a tool with "replace" keeps the original name."""

        def original_fn(x: int) -> int:
            return x

        def replacement_fn(x: int) -> int:
            return x * 2

        # Create a manager with REPLACE behavior
        manager = ToolManager(duplicate_behavior="replace")

        # Add the original tool
        original_tool = Tool.from_function(original_fn, name="test_tool")
        manager.add_tool(original_tool)
        assert original_tool.name == "test_tool"

        # Replace with a new function but keep the same registered name
        replacement_tool = Tool.from_function(replacement_fn, name="test_tool")
        manager.add_tool(replacement_tool)

        # The tool object should have been replaced
        stored_tool = await manager.get_tool("test_tool")
        assert stored_tool is not None
        assert stored_tool == replacement_tool

        # The name should still be the same
        assert stored_tool.name == "test_tool"

        # But the function is different
        assert isinstance(stored_tool, FunctionTool)
        assert stored_tool.fn.__name__ == "replacement_fn"


class TestToolErrorHandling:
    """Test error handling in the ToolManager."""

    async def test_tool_error_passthrough(self):
        """Test that ToolErrors are passed through directly."""
        manager = ToolManager()

        def error_tool(x: int) -> int:
            """Tool that raises a ToolError."""
            raise ToolError("Specific tool error")

        manager.add_tool(Tool.from_function(error_tool))

        with pytest.raises(ToolError, match="Specific tool error"):
            await manager.call_tool("error_tool", {"x": 42})

    async def test_exception_converted_to_tool_error_with_details(self):
        """Test that other exceptions include details by default."""
        manager = ToolManager()

        def buggy_tool(x: int) -> int:
            """Tool that raises a ValueError."""
            raise ValueError("Internal error details")

        manager.add_tool(Tool.from_function(buggy_tool))

        with pytest.raises(ToolError) as excinfo:
            await manager.call_tool("buggy_tool", {"x": 42})

        # Exception message should include the tool name and the internal details
        assert "Error calling tool 'buggy_tool'" in str(excinfo.value)
        assert "Internal error details" in str(excinfo.value)

    async def test_exception_converted_to_masked_tool_error(self):
        """Test that other exceptions are masked when enabled."""
        manager = ToolManager(mask_error_details=True)

        def buggy_tool(x: int) -> int:
            """Tool that raises a ValueError."""
            raise ValueError("Internal error details")

        manager.add_tool(Tool.from_function(buggy_tool))

        with pytest.raises(ToolError) as excinfo:
            await manager.call_tool("buggy_tool", {"x": 42})

        # Exception message should only contain the tool name, not the internal details
        assert "Error calling tool 'buggy_tool'" in str(excinfo.value)
        assert "Internal error details" not in str(excinfo.value)

    async def test_async_tool_error_passthrough(self):
        """Test that ToolErrors from async tools are passed through directly."""
        manager = ToolManager()

        async def async_error_tool(x: int) -> int:
            """Async tool that raises a ToolError."""
            raise ToolError("Async tool error")

        manager.add_tool(Tool.from_function(async_error_tool))

        with pytest.raises(ToolError, match="Async tool error"):
            await manager.call_tool("async_error_tool", {"x": 42})

    async def test_async_exception_converted_to_tool_error_with_details(self):
        """Test that other exceptions from async tools include details by default."""
        manager = ToolManager()

        async def async_buggy_tool(x: int) -> int:
            """Async tool that raises a ValueError."""
            raise ValueError("Internal async error details")

        manager.add_tool(Tool.from_function(async_buggy_tool))

        with pytest.raises(ToolError) as excinfo:
            await manager.call_tool("async_buggy_tool", {"x": 42})

        # Exception message should include the tool name and the internal details
        assert "Error calling tool 'async_buggy_tool'" in str(excinfo.value)
        assert "Internal async error details" in str(excinfo.value)

    async def test_async_exception_converted_to_masked_tool_error(self):
        """Test that other exceptions from async tools are masked when enabled."""
        manager = ToolManager(mask_error_details=True)

        async def async_buggy_tool(x: int) -> int:
            """Async tool that raises a ValueError."""
            raise ValueError("Internal async error details")

        manager.add_tool(Tool.from_function(async_buggy_tool))

        with pytest.raises(ToolError) as excinfo:
            await manager.call_tool("async_buggy_tool", {"x": 42})

        # Exception message should contain the tool name but not the internal details
        assert "Error calling tool 'async_buggy_tool'" in str(excinfo.value)
        assert "Internal async error details" not in str(excinfo.value)
