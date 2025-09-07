"""
Exceptions for FastMCP elicitation forms.
"""
from __future__ import annotations

from fastmcp.exceptions import FastMCPError


class ElicitationError(FastMCPError):
    """Base exception for elicitation form errors."""
    pass


class ValidationError(ElicitationError):
    """Exception raised when field validation fails."""
    pass


class ElicitationNotSupportedError(ElicitationError):
    """Exception raised when client doesn't support elicitation."""
    pass