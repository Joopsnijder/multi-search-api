"""Serper.dev search provider."""

import logging
from typing import Any

import requests

from multi_search_api.exceptions import RateLimitError
from multi_search_api.providers.base import SearchProvider

logger = logging.getLogger(__name__)


def _error_reason(response: requests.Response) -> str:
    """Describe why Serper refused a request.

    Serper answers failures with a JSON body carrying the actual cause --
    an exhausted quota comes back as 400 "Not enough credits", not as the
    402 you would expect. Logging the status alone turns every one of those
    into the same opaque line, so read the message out of the body and fall
    back to the raw text when it is not JSON.
    """
    try:
        message = response.json().get("message")
    except ValueError:
        message = None

    return message or response.text[:200].strip() or "no detail in response body"


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
                reason = _error_reason(response)
                logger.error(f"Serper API error {response.status_code}: {reason}")
                raise RateLimitError(f"Serper rate limit hit: {response.status_code}: {reason}")
            else:
                reason = _error_reason(response)
                logger.error(f"Serper API error {response.status_code}: {reason}")
                return []

        except RateLimitError:
            raise
        except Exception as e:
            logger.error(f"Serper search failed: {e}")
            return []
