from __future__ import annotations

import inspect
import json
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import pydantic_core
from mcp.types import RequestId, ElicitRequest, ElicitRequestedSchema, ElicitRequestParams
from pydantic import Field

from mcp.server.session import ServerSession

import fastmcp
from fastmcp.server.dependencies import get_context
from fastmcp.utilities.components import FastMCPComponent
from fastmcp.utilities.json_schema import compress_schema
from fastmcp.utilities.logging import get_logger
from fastmcp.utilities.types import (
    Audio,
    File,
    Image,
    MCPContent,
    find_kwarg_by_type,
    get_cached_typeadapter,
)


if TYPE_CHECKING:
    from fastmcp.tools.tool_transform import ArgTransform, TransformedTool

logger = get_logger(__name__)


class Elicitation(FastMCPComponent):
    """
    [Draft Specification](https://modelcontextprotocol.io/specification/draft/client/elicitation)

    Elicitation in MCP allows servers to implement interactive workflows by enabling user input requests to occur nested inside other MCP server features.

    Implementations are free to expose elicitation through any interface pattern that suits their needs—the protocol itself does not mandate any specific user interaction model.


For trust & safety and security:

Servers MUST NOT use elicitation to request sensitive information.
Applications SHOULD:

Provide UI that makes it clear which server is requesting information
Allow users to review and modify their responses before sending
Respect user privacy and provide clear reject and cancel options

    """
    # @staticmethod
    # def from_function(
    #     fn: Callable[..., Any],
    #     name: str | None = None,
    #     serializer: Callable[[Any], str] | None = None,
    #     enabled: bool | None = None,
    # ) -> FunctionTool:
    #     """Create a Tool from a function."""
    #     return FunctionTool.from_function(
    #         fn=fn,
    #         name=name,
    #         annotations=annotations,
    #         serializer=serializer,
    #         enabled=enabled,
    #     )
    #
    def to_mcp_elicit_request(self, **overrides: Any) -> ElicitRequest:
        """Convert the elicitation to an MCP elicitation."""
        kwargs = {
            "name": self.name,
            "description": self.description,
            "requestedSchema": self.requested_schema,
            "params": self.params,
        }
        return ElicitRequest(**kwargs | overrides)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name!r}, description={self.description!r}, requested_schema={self.requested_schema!r}, params={self.params!r})"
