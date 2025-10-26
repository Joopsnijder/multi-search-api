"""Tests for search result caching."""

from datetime import datetime, timedelta

import pytest
from freezegun import freeze_time

from multi_search_api import SearchResultCache


def test_cache_initialization(temp_cache_file):
    """Test cache initialization."""
    cache = SearchResultCache(cache_file=temp_cache_file)

    assert cache.cache_file.exists()
    assert cache.cache_data == {}
    assert cache.cache_duration == timedelta(days=1)


def test_cache_results(search_cache, sample_search_results):
    """Test caching search results."""
    query = "test query"
    provider = "test_provider"

    # Cache results
    search_cache.cache_results(query, provider, sample_search_results)

    # Verify cache was saved
    assert len(search_cache.cache_data) == 1

    # Get cached results
    cached = search_cache.get_cached_results(query, provider)

    assert cached is not None
    assert len(cached) == len(sample_search_results)
    assert cached[0]["title"] == "Test Result 1"


def test_cache_expiration(search_cache, sample_search_results):
    """Test cache expiration after 24 hours."""
    query = "test query"
    provider = "test_provider"

    # Cache results with current time
    with freeze_time("2025-01-01 12:00:00"):
        search_cache.cache_results(query, provider, sample_search_results)

        # Results should be available immediately
        cached = search_cache.get_cached_results(query, provider)
        assert cached is not None

    # Move forward 25 hours (past expiration)
    with freeze_time("2025-01-02 13:00:00"):
        cached = search_cache.get_cached_results(query, provider)
        assert cached is None  # Should be expired


def test_cache_key_generation(search_cache):
    """Test cache key generation."""
    # Same query with same params should generate same key
    key1 = search_cache._generate_cache_key("test", "provider", num_results=10)
    key2 = search_cache._generate_cache_key("test", "provider", num_results=10)
    assert key1 == key2

    # Different query should generate different key
    key3 = search_cache._generate_cache_key("different", "provider", num_results=10)
    assert key1 != key3

    # Different params should generate different key
    key4 = search_cache._generate_cache_key("test", "provider", num_results=20)
    assert key1 != key4


def test_clear_expired_entries(search_cache, sample_search_results):
    """Test clearing expired cache entries."""
    # Add some entries at different times
    with freeze_time("2025-01-01 12:00:00"):
        search_cache.cache_results("query1", "provider", sample_search_results)

    with freeze_time("2025-01-02 12:00:00"):
        search_cache.cache_results("query2", "provider", sample_search_results)

    assert len(search_cache.cache_data) == 2

    # Move to future and clear expired
    with freeze_time("2025-01-03 12:00:00"):
        search_cache.clear_expired_entries()

        # Only first entry should be expired and removed
        assert len(search_cache.cache_data) == 1


def test_cache_stats(search_cache, sample_search_results):
    """Test cache statistics."""
    # Cache some results
    search_cache.cache_results("query1", "provider", sample_search_results)
    search_cache.cache_results("query2", "provider", sample_search_results)

    stats = search_cache.get_cache_stats()

    assert stats["total_entries"] == 2
    assert stats["cache_file_size"] > 0
    assert stats["oldest_entry"] is not None
    assert stats["newest_entry"] is not None


def test_cache_with_different_languages(search_cache, sample_search_results):
    """Test caching with different language parameters."""
    query = "test query"

    # Cache with different languages
    search_cache.cache_results(query, "provider", sample_search_results, language="en")
    search_cache.cache_results(query, "provider", sample_search_results, language="nl")

    # Should have 2 different cache entries
    assert len(search_cache.cache_data) == 2

    # Retrieval should respect language
    cached_en = search_cache.get_cached_results(query, "provider", language="en")
    cached_nl = search_cache.get_cached_results(query, "provider", language="nl")

    assert cached_en is not None
    assert cached_nl is not None
