"""Pytest configuration and fixtures for multi-search-api tests."""

import tempfile
from pathlib import Path

import pytest

from multi_search_api import SearchResultCache, SmartSearchTool


@pytest.fixture
def temp_cache_file():
    """Create a temporary cache file for testing."""
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
        temp_path = f.name

    yield temp_path

    # Cleanup
    Path(temp_path).unlink(missing_ok=True)


@pytest.fixture
def search_cache(temp_cache_file):
    """Create a SearchResultCache instance with temporary file."""
    return SearchResultCache(cache_file=temp_cache_file)


@pytest.fixture
def smart_search_tool(temp_cache_file):
    """Create a SmartSearchTool instance with caching disabled for testing."""
    return SmartSearchTool(enable_cache=False)


@pytest.fixture
def smart_search_tool_with_cache(temp_cache_file):
    """Create a SmartSearchTool instance with caching enabled."""
    return SmartSearchTool(enable_cache=True, cache_file=temp_cache_file)


@pytest.fixture
def sample_search_results():
    """Sample search results for testing."""
    return [
        {
            "title": "Test Result 1",
            "snippet": "This is a test snippet for result 1",
            "link": "https://example.com/1",
            "source": "test",
        },
        {
            "title": "Test Result 2",
            "snippet": "This is a test snippet for result 2",
            "link": "https://example.com/2",
            "source": "test",
        },
        {
            "title": "Test Result 3",
            "snippet": "This is a test snippet for result 3",
            "link": "https://example.com/3",
            "source": "test",
        },
    ]


@pytest.fixture
def mock_serper_response():
    """Mock Serper API response."""
    return {
        "organic": [
            {
                "title": "Serper Result 1",
                "snippet": "Snippet from Serper 1",
                "link": "https://example.com/serper1",
            },
            {
                "title": "Serper Result 2",
                "snippet": "Snippet from Serper 2",
                "link": "https://example.com/serper2",
            },
        ]
    }


@pytest.fixture
def mock_brave_response():
    """Mock Brave API response."""
    return {
        "web": {
            "results": [
                {
                    "title": "Brave Result 1",
                    "description": "Description from Brave 1",
                    "url": "https://example.com/brave1",
                },
                {
                    "title": "Brave Result 2",
                    "description": "Description from Brave 2",
                    "url": "https://example.com/brave2",
                },
            ]
        }
    }


@pytest.fixture
def mock_searxng_response():
    """Mock SearXNG API response."""
    return {
        "results": [
            {
                "title": "SearXNG Result 1",
                "content": "Content from SearXNG 1",
                "url": "https://example.com/searxng1",
            },
            {
                "title": "SearXNG Result 2",
                "content": "Content from SearXNG 2",
                "url": "https://example.com/searxng2",
            },
        ]
    }
