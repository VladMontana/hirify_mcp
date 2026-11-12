"""Custom exception hierarchy for Hirify API client."""

from typing import Optional


class HirifyError(Exception):
    """Base exception for all Hirify MCP errors."""

    def __init__(self, message: str, details: Optional[dict] = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def __str__(self) -> str:
        if self.details:
            return f"{self.message} (details: {self.details})"
        return self.message


class HirifyNetworkError(HirifyError):
    """Raised on connection failures, DNS errors, or network interruptions."""

    pass


class HirifyTimeoutError(HirifyNetworkError):
    """Raised when an HTTP request times out."""

    pass


class HirifyAPIError(HirifyError):
    """Raised when the Hirify API returns an error status code."""

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        response_body: Optional[str] = None,
        details: Optional[dict] = None,
    ) -> None:
        super().__init__(message, details)
        self.status_code = status_code
        self.response_body = response_body

    def __str__(self) -> str:
        status_str = f" [HTTP {self.status_code}]" if self.status_code else ""
        return f"{self.message}{status_str}"


class HirifyRateLimitError(HirifyAPIError):
    """Raised when Hirify returns HTTP 429 Too Many Requests."""

    def __init__(
        self,
        message: str = "Hirify rate limit exceeded",
        retry_after: Optional[float] = None,
        status_code: int = 429,
        response_body: Optional[str] = None,
        details: Optional[dict] = None,
    ) -> None:
        super().__init__(
            message, status_code=status_code, response_body=response_body, details=details
        )
        self.retry_after = retry_after


class HirifyNotFoundError(HirifyAPIError):
    """Raised when a requested resource (e.g. vacancy ID) is not found (HTTP 404)."""

    def __init__(
        self,
        message: str = "Resource not found on Hirify",
        status_code: int = 404,
        response_body: Optional[str] = None,
        details: Optional[dict] = None,
    ) -> None:
        super().__init__(
            message, status_code=status_code, response_body=response_body, details=details
        )


class HirifyResponseError(HirifyAPIError):
    """Raised when response is not valid JSON or has unexpected structure."""

    pass
