"""Base class for search providers."""

from abc import ABC, abstractmethod
from typing import Any


class SearchProvider(ABC):
    """Abstract base class for search providers."""

    @abstractmethod
    def search(self, query: str, **kwargs) -> list[dict[str, Any]]:
        """Execute a search query.

        Args:
            query: The search query string
            **kwargs: Additional provider-specific arguments

        Returns:
            List of search results, each containing:
                - title: Result title
                - snippet: Result description/snippet
                - link: Result URL
                - source: Provider identifier
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if this provider is available.

        Returns:
            True if provider can be used, False otherwise
        """
        pass
