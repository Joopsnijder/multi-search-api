"""Custom exceptions for multi-search-api."""


class RateLimitError(Exception):
    """Raised when a provider hits rate limits."""

    pass
