"""Tests for SmartSearchTool core functionality."""

import pytest
import responses
from freezegun import freeze_time

from multi_search_api import SmartSearchTool
from multi_search_api.exceptions import RateLimitError


class TestSmartSearchTool:
    """Tests for SmartSearchTool."""

    def test_initialization(self):
        """Test SmartSearchTool initialization."""
        tool = SmartSearchTool(enable_cache=False)

        assert tool.cache is None
        assert len(tool.providers) > 0
        assert len(tool.rate_limited_providers) == 0

    def test_initialization_with_cache(self, temp_cache_file):
        """Test initialization with caching enabled."""
        tool = SmartSearchTool(enable_cache=True, cache_file=temp_cache_file)

        assert tool.cache is not None

    def test_initialization_with_api_keys(self):
        """Test initialization with explicit API keys."""
        tool = SmartSearchTool(
            serper_api_key="serper_test",
            brave_api_key="brave_test",
            enable_cache=False,
        )

        # Should have providers for serper and brave
        provider_names = [p.__class__.__name__ for p in tool.providers]
        assert "SerperProvider" in provider_names
        assert "BraveProvider" in provider_names

    @responses.activate
    def test_successful_search(self, smart_search_tool, mock_searxng_response):
        """Test successful search."""
        # Mock SearXNG (as it's always available)
        responses.add(
            responses.GET,
            "https://searx.be/search",
            json=mock_searxng_response,
            status=200,
        )

        result = smart_search_tool.search("test query")

        assert result["query"] == "test query"
        assert result["provider"] is not None
        assert len(result["results"]) > 0
        assert result["cache_hit"] is False

    def test_cache_hit(self, smart_search_tool_with_cache, sample_search_results):
        """Test cache hit on second search."""
        # Manually cache results
        smart_search_tool_with_cache.cache.cache_results(
            "test query", "any", sample_search_results
        )

        # Search should hit cache
        result = smart_search_tool_with_cache.search("test query")

        assert result["cache_hit"] is True
        assert result["provider"] == "cached"
        assert len(result["results"]) == len(sample_search_results)

    @responses.activate
    def test_provider_fallback(self, temp_cache_file, mock_searxng_response):
        """Test automatic provider fallback."""
        tool = SmartSearchTool(
            serper_api_key="test_key", enable_cache=False, cache_file=temp_cache_file
        )

        # Mock Serper to return rate limit
        responses.add(
            responses.POST,
            "https://google.serper.dev/search",
            json={},
            status=429,
        )

        # Mock SearXNG to succeed
        responses.add(
            responses.GET,
            "https://searx.be/search",
            json=mock_searxng_response,
            status=200,
        )

        result = tool.search("test query")

        # Should have fallen back to SearXNG
        assert "SearXNG" in result["provider"]
        assert len(result["results"]) > 0

        # Serper should be marked as rate limited
        assert "SerperProvider" in tool.rate_limited_providers

    def test_get_status(self, smart_search_tool):
        """Test get_status method."""
        status = smart_search_tool.get_status()

        assert "providers" in status
        assert "rate_limited_providers" in status
        assert isinstance(status["providers"], list)
        assert len(status["providers"]) > 0

    def test_get_status_with_cache(self, smart_search_tool_with_cache):
        """Test get_status with caching enabled."""
        status = smart_search_tool_with_cache.get_status()

        assert "cache" in status
        assert "total_entries" in status["cache"]

    def test_clear_cache(self, smart_search_tool_with_cache, sample_search_results):
        """Test cache clearing."""
        # Add some cached results
        smart_search_tool_with_cache.cache.cache_results(
            "query1", "any", sample_search_results
        )

        # Cache should have entries
        assert len(smart_search_tool_with_cache.cache.cache_data) > 0

        # Clear cache (only clears expired, so use freeze_time)
        with freeze_time("2025-01-03"):
            smart_search_tool_with_cache.clear_cache()

        # Entries should be cleared
        assert len(smart_search_tool_with_cache.cache.cache_data) == 0

    def test_reset_rate_limits(self, smart_search_tool):
        """Test resetting rate limits."""
        # Manually add a rate limited provider
        smart_search_tool.rate_limited_providers.add("TestProvider")

        assert len(smart_search_tool.rate_limited_providers) == 1

        # Reset
        smart_search_tool.reset_rate_limits()

        assert len(smart_search_tool.rate_limited_providers) == 0

    def test_disable_cache(self, smart_search_tool_with_cache):
        """Test disabling cache."""
        assert smart_search_tool_with_cache.cache is not None

        smart_search_tool_with_cache.disable_cache()

        assert smart_search_tool_with_cache.cache is None

    def test_enable_cache(self, smart_search_tool, temp_cache_file):
        """Test enabling cache."""
        assert smart_search_tool.cache is None

        smart_search_tool.enable_cache(cache_file=temp_cache_file)

        assert smart_search_tool.cache is not None

    @responses.activate
    def test_run_method_crewai_compatible(self, smart_search_tool, mock_searxng_response):
        """Test CrewAI-compatible run method."""
        # Mock SearXNG
        responses.add(
            responses.GET,
            "https://searx.be/search",
            json=mock_searxng_response,
            status=200,
        )

        result = smart_search_tool.run("test query")

        assert isinstance(result, str)
        assert "test query" in result
        assert "Search results" in result or "No results" in result

    def test_num_results_parameter(self, smart_search_tool_with_cache, sample_search_results):
        """Test num_results parameter."""
        # Cache results
        smart_search_tool_with_cache.cache.cache_results(
            "test", "any", sample_search_results, num_results=5
        )

        # Different num_results should not hit cache
        result = smart_search_tool_with_cache.search("test", num_results=10)
        # Will try to search since cache key is different
        assert result["cache_hit"] is False or result["provider"] != "cached"
