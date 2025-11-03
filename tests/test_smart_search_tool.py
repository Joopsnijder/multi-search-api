"""Tests for SmartSearchTool core functionality."""

from freezegun import freeze_time

from multi_search_api import SmartSearchTool


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

    def test_successful_search_with_cache(
        self, smart_search_tool_with_cache, sample_search_results
    ):
        """Test successful search using cached results."""
        # Pre-populate cache with results
        smart_search_tool_with_cache.cache.cache_results("test query", "any", sample_search_results)

        result = smart_search_tool_with_cache.search("test query")

        assert result["query"] == "test query"
        assert result["provider"] == "cached"
        assert len(result["results"]) > 0
        assert result["cache_hit"] is True

    def test_cache_hit(self, smart_search_tool_with_cache, sample_search_results):
        """Test cache hit on second search."""
        # Manually cache results
        smart_search_tool_with_cache.cache.cache_results("test query", "any", sample_search_results)

        # Search should hit cache
        result = smart_search_tool_with_cache.search("test query")

        assert result["cache_hit"] is True
        assert result["provider"] == "cached"
        assert len(result["results"]) == len(sample_search_results)

    def test_provider_fallback_tracking(self, smart_search_tool):
        """Test rate limit provider tracking."""
        # Manually mark a provider as rate limited
        smart_search_tool.rate_limited_providers.add("SerperProvider")

        status = smart_search_tool.get_status()

        # Verify provider is tracked as rate limited
        assert "SerperProvider" in status["rate_limited_providers"]

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
        # Add cached results at a specific time
        with freeze_time("2025-01-01 12:00:00"):
            smart_search_tool_with_cache.cache.cache_results("query1", "any", sample_search_results)

        # Cache should have entries
        assert len(smart_search_tool_with_cache.cache.cache_data) > 0

        # Move to future (more than 1 day later) and clear expired entries
        with freeze_time("2025-01-03 12:00:00"):
            smart_search_tool_with_cache.clear_cache()

            # Entries should be cleared (expired)
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

    def test_run_method_crewai_compatible(
        self, smart_search_tool_with_cache, sample_search_results
    ):
        """Test CrewAI-compatible run method."""
        # Pre-populate cache
        smart_search_tool_with_cache.cache.cache_results("test query", "any", sample_search_results)

        result = smart_search_tool_with_cache.run("test query")

        assert isinstance(result, str)
        assert "test query" in result
        assert "Search results" in result or "Test Result" in result

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
