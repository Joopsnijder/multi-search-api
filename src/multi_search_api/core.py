"""Core SmartSearchTool implementation."""

import logging
import os
from datetime import datetime, timedelta
from typing import Any

from dotenv import load_dotenv

from multi_search_api.cache import SearchResultCache
from multi_search_api.exceptions import RateLimitError
from multi_search_api.providers import (
    BraveProvider,
    DuckDuckGoProvider,
    GoogleScraperProvider,
    SearXNGProvider,
    SerperProvider,
)

# Load environment variables
load_dotenv()

# Setup logging - only show warnings and errors by default
logger = logging.getLogger(__name__)

# Suppress verbose logging from httpx
logging.getLogger("httpx").setLevel(logging.WARNING)


def configure_logging(level: int = logging.WARNING, quiet: bool = False) -> None:
    """Configure logging for multi-search-api.

    Args:
        level: Logging level (e.g., logging.DEBUG, logging.INFO, logging.WARNING)
        quiet: If True, suppress all output (sets level to CRITICAL+1)
    """
    if quiet:
        level = logging.CRITICAL + 1
    logger.setLevel(level)
    # Also set level on parent logger for providers
    logging.getLogger("multi_search_api").setLevel(level)


class SmartSearchTool:
    """
    Intelligent search tool with automatic fallback and rate limit handling.

    Features:
    - Multi-provider fallback (Serper → SearXNG → Brave → DuckDuckGo → Google Scraper)
    - Automatic rate limit detection (HTTP 402/429)
    - Session-based provider skipping when rate limited
    - 1-day result caching for performance

    Provider Priority:
    1. Serper - Best quality with rich snippets (primary choice)
    2. SearXNG - Free, unlimited, variable quality
    3. Brave - Good quality with snippets (requires API key)
    4. DuckDuckGo - Free, no API key, rate limited (~20 req/min)
    5. Google Scraper - Last resort fallback

    Note: Ollama provider disabled by default due to empty snippets issue
    """

    def __init__(
        self,
        ollama_api_key: str | None = None,
        serper_api_key: str | None = None,
        brave_api_key: str | None = None,
        searxng_instance: str | None = None,
        enable_cache: bool = True,
        cache_file: str | None = None,
        log_level: int | None = None,
        quiet: bool = False,
    ):
        """Initialize SmartSearchTool.

        Args:
            ollama_api_key: Ollama API key (optional, not recommended)
            serper_api_key: Serper.dev API key (recommended)
            brave_api_key: Brave Search API key (optional)
            searxng_instance: Custom SearXNG instance URL (optional)
            enable_cache: Enable result caching (default: True)
            cache_file: Custom cache file path (optional)
            log_level: Logging level (e.g., logging.DEBUG, logging.INFO).
                       Default: WARNING (only warnings and errors shown)
            quiet: If True, suppress all logging output
        """
        # Configure logging if specified
        if quiet or log_level is not None:
            configure_logging(level=log_level or logging.WARNING, quiet=quiet)
        # Initialize cache only
        self.cache = SearchResultCache(cache_file=cache_file) if enable_cache else None

        # Track rate-limited providers for current session
        self.rate_limited_providers = set()

        # Track warnings that have already been shown (to avoid spam)
        self._seen_warnings: set[str] = set()

        # Initialize providers in priority order
        self.providers = []

        # 1. Serper (best quality results with snippets, free up to 2,500/month)
        if serper_api_key or os.getenv("SERPER_API_KEY"):
            self.providers.append(SerperProvider(serper_api_key or os.getenv("SERPER_API_KEY")))

        # 2. SearXNG (fully free, open source, variable quality)
        self.providers.append(SearXNGProvider(searxng_instance))

        # 3. Brave (good quality with snippets, free tier available)
        if brave_api_key or os.getenv("BRAVE_API_KEY"):
            self.providers.append(BraveProvider(brave_api_key or os.getenv("BRAVE_API_KEY")))

        # 4. DuckDuckGo (free, no API key, rate limited)
        duckduckgo_provider = DuckDuckGoProvider()
        if duckduckgo_provider.is_available():
            self.providers.append(duckduckgo_provider)

        # 5. Google Scraper (last resort)
        self.providers.append(GoogleScraperProvider())

        # Note: Ollama disabled by default due to empty snippets issue
        # if ollama_api_key or os.getenv("OLLAMA_API_KEY"):
        #     self.providers.append(OllamaProvider(ollama_api_key or os.getenv("OLLAMA_API_KEY")))

        logger.info(f"Smart Search Tool initialized with {len(self.providers)} providers")

    def _log_warning_once(self, message: str):
        """Log warning once, then debug for subsequent occurrences."""
        if message in self._seen_warnings:
            logger.debug(message)
        else:
            self._seen_warnings.add(message)
            logger.warning(message)

    async def search_recent_content(
        self, query: str, max_results: int = 10, days_back: int = 14, language: str = "nl,en"
    ) -> list[dict]:
        """
        Search for recent content within specified timeframe.

        Args:
            query: Search query
            max_results: Maximum number of results
            days_back: Number of days to look back
            language: Language filter

        Returns:
            List of search results
        """
        # Add date filter to query
        cutoff_date = datetime.now() - timedelta(days=days_back)

        try:
            # Use existing search method
            search_results = self.search(
                query=query,
                max_results=max_results,
                language=language,
                time_range="recent",  # Provider-specific recent filter
            )

            results = search_results.get("results", [])

            # Filter by date if available
            filtered_results = []
            for result in results:
                # Try to parse date if available
                result_date = result.get("date") or result.get("published_date")
                if result_date:
                    try:
                        # Parse various date formats
                        if isinstance(result_date, str):
                            # Try common formats
                            for _date_format in ["%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%d %b %Y"]:
                                try:
                                    parsed_date = datetime.strptime(result_date[:10], "%Y-%m-%d")
                                    if parsed_date >= cutoff_date:
                                        filtered_results.append(result)
                                    break
                                except ValueError:
                                    continue
                        else:
                            filtered_results.append(result)  # Include if date parsing fails
                    except Exception:
                        filtered_results.append(result)  # Include if date parsing fails
                else:
                    # Include results without date (assume recent)
                    filtered_results.append(result)

            logger.info(f"Found {len(filtered_results)} recent results for query: {query}")
            return filtered_results[:max_results]

        except Exception as e:
            logger.error(f"Error in search_recent_content: {e}")
            return []

    def search(self, query: str, **kwargs) -> dict[str, Any]:
        """
        Execute search with automatic fallback and caching.

        Args:
            query: Search query string
            **kwargs: Additional arguments:
                - num_results: Number of results to return (default: 10)
                - language: Language filter (default: "nl")

        Returns:
            Dictionary containing:
                - query: The search query
                - provider: Provider used (or "cached")
                - cache_hit: Whether result came from cache
                - timestamp: ISO timestamp
                - results: List of search results
        """
        results = []
        used_provider = None
        cache_hit = False

        # Try cache first if enabled (query-based, provider-agnostic)
        if self.cache:
            cached_results = self.cache.get_cached_results(query, "any", **kwargs)

            if cached_results is not None and len(cached_results) > 0:
                results = cached_results
                used_provider = "cached"
                cache_hit = True
                logger.info(f"Cache hit for query '{query}': {len(results)} results")

        # If no cache hit, search with providers
        if not cache_hit:
            for provider in self.providers:
                provider_name = provider.__class__.__name__

                # Skip rate-limited providers
                if provider_name in self.rate_limited_providers:
                    logger.info(f"⏭️  Skipping {provider_name} (rate limited during this session)")
                    continue

                if provider.is_available():
                    logger.info(f"Trying search with {provider_name}")
                    try:
                        results = provider.search(query, **kwargs)

                        if results:
                            used_provider = provider_name
                            query_display = query[:50] + "..." if len(query) > 50 else query
                            logger.info(
                                f"🔍 {query_display} → {len(results)} results ({provider_name})"
                            )

                            # Cache the results if caching is enabled (only cache non-empty)
                            # Cache under generic "any" provider so any provider can retrieve it
                            if self.cache and len(results) > 0:
                                self.cache.cache_results(query, "any", results, **kwargs)

                            break
                        else:
                            self._log_warning_once(
                                f"⏭️  {provider_name} returned no results, trying next provider"
                            )
                    except RateLimitError as e:
                        # Mark provider as rate-limited for rest of session
                        self.rate_limited_providers.add(provider_name)
                        self._log_warning_once(
                            f"⚠️  {provider_name} rate limited, skipping for rest of session: {e}"
                        )
                        # Continue to next provider
                        continue
                    except Exception as e:
                        # Other errors - log and try next provider
                        self._log_warning_once(
                            f"⏭️  {provider_name} failed: {e}, trying next provider"
                        )
                        continue
                else:
                    logger.info(f"⏭️  {provider_name} not available, trying next provider")

        # Format response
        return {
            "query": query,
            "provider": used_provider,
            "results": results,
            "cache_hit": cache_hit,
            "timestamp": datetime.now().isoformat(),
        }

    def get_status(self) -> dict[str, Any]:
        """Get status of all providers and cache."""
        status: dict[str, Any] = {
            "providers": [p.__class__.__name__ for p in self.providers],
            "rate_limited_providers": list(self.rate_limited_providers),
        }

        # Add cache statistics if caching is enabled
        if self.cache:
            status["cache"] = self.cache.get_cache_stats()

        return status

    def clear_cache(self):
        """Clear all cached search results."""
        if self.cache:
            self.cache.clear_expired_entries()
            logger.info("Cleared expired cache entries")
        else:
            logger.info("Caching not enabled")

    def reset_rate_limits(self):
        """Reset rate limit tracking (useful for new sessions)."""
        self.rate_limited_providers.clear()
        logger.info("Rate limit tracking reset")

    def disable_cache(self):
        """Disable caching for testing or other purposes."""
        self.cache = None
        logger.info("Search result caching disabled")

    def enable_cache(self, cache_file: str | None = None):
        """Re-enable caching.

        Args:
            cache_file: Optional custom cache file path
        """
        if not self.cache:
            self.cache = SearchResultCache(cache_file=cache_file)
            logger.info("Search result caching enabled")

    def run(self, query: str) -> str:
        """
        CrewAI compatible run method.

        Args:
            query: Search query

        Returns:
            Formatted string with search results
        """
        result = self.search(query)

        # Format for CrewAI
        if result["results"]:
            formatted = f"Search results for '{query}' (via {result['provider']}):\n\n"
            for i, r in enumerate(result["results"][:5], 1):
                formatted += f"{i}. {r['title']}\n"
                formatted += f"   {r['snippet']}\n"
                formatted += f"   URL: {r['link']}\n\n"
            return formatted
        else:
            return f"No results found for '{query}'"
