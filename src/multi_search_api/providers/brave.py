"""Brave Search provider."""

import logging
import time
from typing import Any

import requests

from multi_search_api.exceptions import RateLimitError
from multi_search_api.providers.base import SearchProvider

logger = logging.getLogger(__name__)


class BraveProvider(SearchProvider):
    """Brave Search provider (free tier with 1 req/sec limit)."""

    def __init__(self, api_key: str | None):
        self.api_key = api_key
        self.base_url = "https://api.search.brave.com/res/v1/web/search"
        self.last_request_time = 0  # Track last request for rate limiting

    def is_available(self) -> bool:
        """Check if Brave is available."""
        return bool(self.api_key)

    def search(self, query: str, **kwargs) -> list[dict[str, Any]]:
        """Search via Brave Search API (respects 1 req/sec rate limit)."""
        try:
            # Enforce 1 request per second rate limit
            current_time = time.time()
            time_since_last = current_time - self.last_request_time
            if time_since_last < 1.0:
                sleep_time = 1.0 - time_since_last
                logger.info(f"Brave rate limit: sleeping {sleep_time:.2f}s")
                time.sleep(sleep_time)

            headers = {"X-Subscription-Token": self.api_key, "Accept": "application/json"}

            params = {"q": query, "count": kwargs.get("num_results", 10)}

            self.last_request_time = time.time()  # Update before request
            response = requests.get(self.base_url, headers=headers, params=params, timeout=10)

            if response.status_code == 200:
                data = response.json()
                results = []

                for item in data.get("web", {}).get("results", []):
                    results.append(
                        {
                            "title": item.get("title", ""),
                            "snippet": item.get("description", ""),
                            "link": item.get("url", ""),
                            "source": "brave",
                        }
                    )

                logger.info(f"Brave search successful: {len(results)} results")
                return results
            elif response.status_code in (402, 429):
                logger.error(f"Brave API error: {response.status_code}")
                raise RateLimitError(f"Brave rate limit hit: {response.status_code}")
            else:
                logger.error(f"Brave API error: {response.status_code}")
                return []

        except RateLimitError:
            raise
        except Exception as e:
            logger.error(f"Brave search failed: {e}")
            return []
