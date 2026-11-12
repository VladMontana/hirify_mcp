"""API clients module for Hirify."""

from hirify_mcp.clients.exceptions import (
    HirifyAPIError,
    HirifyError,
    HirifyNetworkError,
    HirifyNotFoundError,
    HirifyRateLimitError,
    HirifyResponseError,
    HirifyTimeoutError,
)

__all__ = [
    "HirifyError",
    "HirifyAPIError",
    "HirifyNetworkError",
    "HirifyTimeoutError",
    "HirifyRateLimitError",
    "HirifyNotFoundError",
    "HirifyResponseError",
]
