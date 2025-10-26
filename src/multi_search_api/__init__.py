"""
Multi-Search-API: Intelligent multi-provider search with automatic fallback.

A powerful search tool that automatically switches between multiple search providers
(Serper, SearXNG, Brave, Google) with smart caching and rate limit handling.
"""

from multi_search_api.cache import SearchResultCache
from multi_search_api.core import SmartSearchTool
from multi_search_api.exceptions import RateLimitError

__version__ = "0.1.0"
__author__ = "Joop Snijder"

__all__ = [
    "SmartSearchTool",
    "SearchResultCache",
    "RateLimitError",
]
