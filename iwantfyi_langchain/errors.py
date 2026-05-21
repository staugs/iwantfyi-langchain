"""Typed exceptions matching JSON-RPC error codes from iwant.fyi demand-side protocol v1.0 section 11."""

from __future__ import annotations
from typing import Any, Optional


class IwantError(Exception):
    """Base exception. Carries a JSON-RPC error code."""

    def __init__(self, message: str, code: int = -32603, data: Any = None) -> None:
        super().__init__(message)
        self.code = code
        self.data = data


class UnauthorizedError(IwantError):
    """API key invalid or missing. JSON-RPC -32000."""

    def __init__(self, message: str = "Unauthorized: valid API key required") -> None:
        super().__init__(message, code=-32000)


class RateLimitedError(IwantError):
    """Rate limited. JSON-RPC -32001."""

    def __init__(self, message: str = "Rate limit exceeded") -> None:
        super().__init__(message, code=-32001)


class ValidationError(IwantError):
    """Invalid parameters. JSON-RPC -32602."""

    def __init__(self, message: str, data: Any = None) -> None:
        super().__init__(message, code=-32602, data=data)


class NotFoundError(IwantError):
    """Resource not found."""

    def __init__(self, message: str = "Resource not found") -> None:
        super().__init__(message, code=-32602)


def error_from_code(code: int, message: str, data: Optional[Any] = None) -> IwantError:
    if code == -32000:
        return UnauthorizedError(message)
    if code == -32001:
        return RateLimitedError(message)
    if code == -32602:
        return ValidationError(message, data)
    return IwantError(message, code, data)
