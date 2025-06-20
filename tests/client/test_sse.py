import asyncio
import json
import sys
from collections.abc import Generator

import pytest
import uvicorn
from mcp import McpError
from starlette.applications import Starlette
from starlette.routing import Mount

from fastmcp.client import Client
from fastmcp.client.transports import SSETransport
from fastmcp.server.dependencies import get_http_request
from fastmcp.server.server import FastMCP
from fastmcp.utilities.tests import run_server_in_process


def fastmcp_server():
    """Fixture that creates a FastMCP server with tools, resources, and prompts."""
    server = FastMCP("TestServer")

    # Add a tool
    @server.tool
    def greet(name: str) -> str:
        """Greet someone by name."""
        return f"Hello, {name}!"

    # Add a second tool
    @server.tool
    def add(a: int, b: int) -> int:
        """Add two numbers together."""
        return a + b

    @server.tool
    async def sleep(seconds: float) -> str:
        """Sleep for a given number of seconds."""
        await asyncio.sleep(seconds)
        return f"Slept for {seconds} seconds"

    # Add a resource
    @server.resource(uri="data://users")
    async def get_users():
        return ["Alice", "Bob", "Charlie"]

    # Add a resource template
    @server.resource(uri="data://user/{user_id}")
    async def get_user(user_id: str):
        return {"id": user_id, "name": f"User {user_id}", "active": True}

    @server.resource(uri="request://headers")
    async def get_headers() -> dict[str, str]:
        request = get_http_request()

        return dict(request.headers)

    # Add a prompt
    @server.prompt
    def welcome(name: str) -> str:
        """Example greeting prompt."""
        return f"Welcome to FastMCP, {name}!"

    return server


def run_server(host: str, port: int, **kwargs) -> None:
    fastmcp_server().run(host=host, port=port, **kwargs)


@pytest.fixture(autouse=True, scope="module")
def sse_server() -> Generator[str, None, None]:
    with run_server_in_process(run_server, transport="sse") as url:
        yield f"{url}/sse/"


async def test_ping(sse_server: str):
    """Test pinging the server."""
    async with Client(transport=SSETransport(sse_server)) as client:
        result = await client.ping()
        assert result is True


async def test_http_headers(sse_server: str):
    """Test getting HTTP headers from the server."""
    async with Client(
        transport=SSETransport(sse_server, headers={"X-DEMO-HEADER": "ABC"})
    ) as client:
        raw_result = await client.read_resource("request://headers")
        json_result = json.loads(raw_result[0].text)  # type: ignore[attr-defined]
        assert "x-demo-header" in json_result
        assert json_result["x-demo-header"] == "ABC"


def run_nested_server(host: str, port: int) -> None:
    app = fastmcp_server().sse_app(path="/mcp/sse/", message_path="/mcp/messages")
    mount = Starlette(routes=[Mount("/nest-inner", app=app)])
    mount2 = Starlette(routes=[Mount("/nest-outer", app=mount)])
    server = uvicorn.Server(
        config=uvicorn.Config(app=mount2, host=host, port=port, log_level="error")
    )
    server.run()


async def test_run_server_on_path():
    with run_server_in_process(run_server, transport="sse", path="/help") as url:
        async with Client(transport=SSETransport(f"{url}/help")) as client:
            result = await client.ping()
            assert result is True


async def test_nested_sse_server_resolves_correctly():
    # tests patch for
    # https://github.com/modelcontextprotocol/python-sdk/pull/659

    with run_server_in_process(run_nested_server) as url:
        async with Client(
            transport=SSETransport(f"{url}/nest-outer/nest-inner/mcp/sse/")
        ) as client:
            result = await client.ping()
            assert result is True


@pytest.mark.skipif(
    sys.platform == "win32",
    reason="Timeout tests are flaky on Windows. Timeouts *are* supported but the tests are unreliable.",
)
class TestTimeout:
    async def test_timeout(self, sse_server: str):
        with pytest.raises(
            McpError,
            match="Timed out while waiting for response to ClientRequest. Waited 0.01 seconds",
        ):
            async with Client(
                transport=SSETransport(sse_server),
                timeout=0.01,
            ) as client:
                await client.call_tool("sleep", {"seconds": 0.1})

    async def test_timeout_tool_call(self, sse_server: str):
        async with Client(transport=SSETransport(sse_server)) as client:
            with pytest.raises(McpError, match="Timed out"):
                await client.call_tool("sleep", {"seconds": 0.1}, timeout=0.01)

    async def test_timeout_tool_call_overrides_client_timeout_if_lower(
        self, sse_server: str
    ):
        async with Client(
            transport=SSETransport(sse_server),
            timeout=2,
        ) as client:
            with pytest.raises(McpError, match="Timed out"):
                await client.call_tool("sleep", {"seconds": 0.1}, timeout=0.01)

    async def test_timeout_client_timeout_does_not_override_tool_call_timeout_if_lower(
        self, sse_server: str
    ):
        """
        With SSE, the tool call timeout always takes precedence over the client.

        Note: on Windows, the behavior appears unpredictable.
        """
        async with Client(
            transport=SSETransport(sse_server),
            timeout=0.01,
        ) as client:
            await client.call_tool("sleep", {"seconds": 0.1}, timeout=2)
