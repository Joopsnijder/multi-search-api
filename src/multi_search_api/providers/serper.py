"""Serper.dev search provider."""

import logging
from typing import Any

import requests

from multi_search_api.exceptions import RateLimitError
from multi_search_api.providers.base import SearchProvider

logger = logging.getLogger(__name__)


class SerperProvider(SearchProvider):
    """Serper.dev search provider."""

    def __init__(self, api_key: str | None):
        self.api_key = api_key
        self.base_url = "https://google.serper.dev/search"

    def is_available(self) -> bool:
        """Check if Serper is available."""
        return bool(self.api_key)

    def search(self, query: str, **kwargs) -> list[dict[str, Any]]:
        """Search via Serper API."""
        try:
            headers = {"X-API-KEY": self.api_key, "Content-Type": "application/json"}

            payload = {"q": query, "num": kwargs.get("num_results", 10)}

            response = requests.post(self.base_url, headers=headers, json=payload, timeout=10)

            if response.status_code == 200:
                data = response.json()
                results = []

                # Parse organic results
                for item in data.get("organic", []):
                    results.append(
                        {
                            "title": item.get("title", ""),
                            "snippet": item.get("snippet", ""),
                            "link": item.get("link", ""),
                            "source": "serper",
                        }
                    )

                logger.info(f"Serper search successful: {len(results)} results")
                return results
            elif response.status_code in (402, 429):
                logger.error(f"Serper API error: {response.status_code}")
                raise RateLimitError(f"Serper rate limit hit: {response.status_code}")
            else:
                logger.error(f"Serper API error: {response.status_code}")
                return []

        except RateLimitError:
            raise
        except Exception as e:
            logger.error(f"Serper search failed: {e}")
            return []
