"""Ollama web search provider."""

import logging
from typing import Any

import requests

from multi_search_api.exceptions import RateLimitError
from multi_search_api.providers.base import SearchProvider

logger = logging.getLogger(__name__)


class OllamaProvider(SearchProvider):
    """Ollama web search provider with free tier."""

    def __init__(self, api_key: str | None):
        self.api_key = api_key
        self.base_url = "https://ollama.com/api/web_search"

    def is_available(self) -> bool:
        """Check if Ollama is available."""
        return bool(self.api_key)

    def search(self, query: str, **kwargs) -> list[dict[str, Any]]:
        """Search via Ollama Web Search API."""
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }

            payload = {"query": query, "max_results": kwargs.get("num_results", 10)}

            response = requests.post(self.base_url, headers=headers, json=payload, timeout=15)

            if response.status_code == 200:
                data = response.json()
                results = []

                # Parse Ollama search results format
                for item in data.get("results", []):
                    results.append(
                        {
                            "title": item.get("title", ""),
                            "snippet": item.get("snippet", "") or item.get("description", ""),
                            "link": item.get("url", "") or item.get("link", ""),
                            "source": "ollama",
                        }
                    )

                logger.info(f"Ollama search successful: {len(results)} results")
                return results
            elif response.status_code in (402, 429):
                # Rate limit or payment required
                logger.error(f"Ollama API error: {response.status_code} - {response.text}")
                raise RateLimitError(f"Ollama rate limit hit: {response.status_code}")
            else:
                logger.error(f"Ollama API error: {response.status_code} - {response.text}")
                return []

        except RateLimitError:
            raise  # Re-raise rate limit errors
        except Exception as e:
            logger.error(f"Ollama search failed: {e}")
            return []
