"""Search provider implementations."""

from multi_search_api.providers.base import SearchProvider
from multi_search_api.providers.brave import BraveProvider
from multi_search_api.providers.duckduckgo import DuckDuckGoProvider
from multi_search_api.providers.google_scraper import GoogleScraperProvider
from multi_search_api.providers.ollama import OllamaProvider
from multi_search_api.providers.searxng import SearXNGProvider
from multi_search_api.providers.serper import SerperProvider

__all__ = [
    "SearchProvider",
    "SerperProvider",
    "SearXNGProvider",
    "BraveProvider",
    "DuckDuckGoProvider",
    "GoogleScraperProvider",
    "OllamaProvider",
]
