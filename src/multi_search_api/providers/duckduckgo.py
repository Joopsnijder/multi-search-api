"""DuckDuckGo Search provider."""

import logging
import time
from typing import Any

from ddgs import DDGS
from ddgs.exceptions import RatelimitException

from multi_search_api.exceptions import RateLimitError
from multi_search_api.providers.base import SearchProvider

logger = logging.getLogger(__name__)


class DuckDuckGoProvider(SearchProvider):
    """DuckDuckGo Search provider (free, no API key required).

    Rate limiting strategy:
    - Minimum 3 seconds between requests to avoid rate limits
    - Exponential backoff on rate limit errors (up to 60 seconds)
    - DuckDuckGo typically allows ~20-30 requests per minute
    """

    def __init__(self, min_delay: float = 3.0, max_backoff: float = 60.0):
        """Initialize DuckDuckGo provider.

        Args:
            min_delay: Minimum seconds between requests (default: 3.0)
            max_backoff: Maximum backoff time in seconds (default: 60.0)
        """
        self.min_delay = min_delay
        self.max_backoff = max_backoff
        self.last_request_time = 0.0
        self.consecutive_failures = 0

    def is_available(self) -> bool:
        """Check if DuckDuckGo is available."""
        return True

    def _get_backoff_time(self) -> float:
        """Calculate exponential backoff time based on consecutive failures."""
        if self.consecutive_failures == 0:
            return self.min_delay

        # Exponential backoff: min_delay * 2^failures, capped at max_backoff
        backoff = self.min_delay * (2**self.consecutive_failures)
        return min(backoff, self.max_backoff)

    def _wait_for_rate_limit(self):
        """Wait appropriate time before making a request."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        required_delay = self._get_backoff_time()

        if time_since_last < required_delay:
            sleep_time = required_delay - time_since_last
            logger.info(f"DuckDuckGo rate limit: sleeping {sleep_time:.2f}s")
            time.sleep(sleep_time)

    def search(self, query: str, **kwargs) -> list[dict[str, Any]]:
        """Search via DuckDuckGo (free, with rate limiting).

        Args:
            query: Search query string
            **kwargs: Additional arguments
                - num_results: Number of results (default: 10)
                - region: Region code (default: 'wt-wt' for no region)

        Returns:
            List of search results
        """
        try:
            # Apply rate limiting
            self._wait_for_rate_limit()

            num_results = kwargs.get("num_results", 10)
            region = kwargs.get("region", "wt-wt")  # wt-wt = no specific region

            # Update request time before making request
            self.last_request_time = time.time()

            # Use DDGS context manager for proper resource cleanup
            with DDGS() as ddgs:
                raw_results = list(
                    ddgs.text(
                        query,
                        region=region,
                        max_results=num_results,
                    )
                )

            # Reset consecutive failures on success
            self.consecutive_failures = 0

            results = []
            for item in raw_results:
                results.append(
                    {
                        "title": item.get("title", ""),
                        "snippet": item.get("body", ""),
                        "link": item.get("href", ""),
                        "source": "duckduckgo",
                    }
                )

            logger.info(f"DuckDuckGo search successful: {len(results)} results")
            return results

        except RatelimitException as e:
            self.consecutive_failures += 1
            logger.warning(f"DuckDuckGo rate limit hit (attempt {self.consecutive_failures}): {e}")
            raise RateLimitError(f"DuckDuckGo rate limit: {e}") from e

        except Exception as e:
            # Don't increase consecutive_failures for non-rate-limit errors
            logger.error(f"DuckDuckGo search failed: {e}")
            return []
