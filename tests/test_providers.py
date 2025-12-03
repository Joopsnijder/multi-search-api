"""Tests for search providers."""

from unittest.mock import MagicMock, patch

import pytest
import responses

from multi_search_api.exceptions import RateLimitError
from multi_search_api.providers import (
    BraveProvider,
    DuckDuckGoProvider,
    SearXNGProvider,
    SerperProvider,
)


class TestSerperProvider:
    """Tests for Serper provider."""

    def test_is_available_with_key(self):
        """Test provider is available with API key."""
        provider = SerperProvider(api_key="test_key")
        assert provider.is_available() is True

    def test_is_available_without_key(self):
        """Test provider is not available without API key."""
        provider = SerperProvider(api_key=None)
        assert provider.is_available() is False

    @responses.activate
    def test_successful_search(self, mock_serper_response):
        """Test successful search with Serper."""
        provider = SerperProvider(api_key="test_key")

        responses.add(
            responses.POST,
            "https://google.serper.dev/search",
            json=mock_serper_response,
            status=200,
        )

        results = provider.search("test query")

        assert len(results) == 2
        assert results[0]["title"] == "Serper Result 1"
        assert results[0]["source"] == "serper"
        assert "link" in results[0]
        assert "snippet" in results[0]

    @responses.activate
    def test_rate_limit_error(self):
        """Test rate limit error handling."""
        provider = SerperProvider(api_key="test_key")

        responses.add(responses.POST, "https://google.serper.dev/search", json={}, status=429)

        with pytest.raises(RateLimitError):
            provider.search("test query")

    @responses.activate
    def test_payment_required_error(self):
        """Test payment required error handling."""
        provider = SerperProvider(api_key="test_key")

        responses.add(responses.POST, "https://google.serper.dev/search", json={}, status=402)

        with pytest.raises(RateLimitError):
            provider.search("test query")


class TestBraveProvider:
    """Tests for Brave provider."""

    def test_is_available_with_key(self):
        """Test provider is available with API key."""
        provider = BraveProvider(api_key="test_key")
        assert provider.is_available() is True

    def test_is_available_without_key(self):
        """Test provider is not available without API key."""
        provider = BraveProvider(api_key=None)
        assert provider.is_available() is False

    @responses.activate
    def test_successful_search(self, mock_brave_response):
        """Test successful search with Brave."""
        provider = BraveProvider(api_key="test_key")

        responses.add(
            responses.GET,
            "https://api.search.brave.com/res/v1/web/search",
            json=mock_brave_response,
            status=200,
        )

        results = provider.search("test query")

        assert len(results) == 2
        assert results[0]["title"] == "Brave Result 1"
        assert results[0]["source"] == "brave"
        assert results[0]["snippet"] == "Description from Brave 1"

    @responses.activate
    def test_rate_limit_error(self):
        """Test rate limit error handling."""
        provider = BraveProvider(api_key="test_key")

        responses.add(
            responses.GET,
            "https://api.search.brave.com/res/v1/web/search",
            json={},
            status=429,
        )

        with pytest.raises(RateLimitError):
            provider.search("test query")


class TestSearXNGProvider:
    """Tests for SearXNG provider."""

    def test_is_available(self):
        """Test SearXNG is always available."""
        provider = SearXNGProvider()
        assert provider.is_available() is True

    def test_custom_instance(self):
        """Test custom instance URL."""
        provider = SearXNGProvider(instance_url="https://custom.searx.com")
        assert provider.instance_url == "https://custom.searx.com"

    @responses.activate
    def test_successful_search(self, mock_searxng_response):
        """Test successful search with SearXNG."""
        provider = SearXNGProvider(instance_url="https://searx.be")

        responses.add(
            responses.GET,
            "https://searx.be/search",
            json=mock_searxng_response,
            status=200,
        )

        results = provider.search("test query")

        assert len(results) == 2
        assert results[0]["title"] == "SearXNG Result 1"
        assert results[0]["source"] == "searxng"

    def test_instance_rotation(self):
        """Test instance rotation on failure."""
        provider = SearXNGProvider()
        initial_instance = provider.instance_url

        provider.rotate_instance()

        # Should have rotated to next instance
        assert provider.instance_url != initial_instance or len(provider.instances) == 1


class TestDuckDuckGoProvider:
    """Tests for DuckDuckGo provider."""

    def test_is_available(self):
        """Test provider is always available (duckduckgo-search is a required dependency)."""
        provider = DuckDuckGoProvider()
        assert provider.is_available() is True

    def test_default_rate_limit_settings(self):
        """Test default rate limit settings."""
        provider = DuckDuckGoProvider()
        assert provider.min_delay == 3.0
        assert provider.max_backoff == 60.0
        assert provider.consecutive_failures == 0

    def test_custom_rate_limit_settings(self):
        """Test custom rate limit settings."""
        provider = DuckDuckGoProvider(min_delay=5.0, max_backoff=120.0)
        assert provider.min_delay == 5.0
        assert provider.max_backoff == 120.0

    def test_backoff_calculation(self):
        """Test exponential backoff calculation."""
        provider = DuckDuckGoProvider(min_delay=2.0, max_backoff=30.0)

        # No failures = min_delay
        assert provider._get_backoff_time() == 2.0

        # 1 failure = min_delay * 2^1 = 4.0
        provider.consecutive_failures = 1
        assert provider._get_backoff_time() == 4.0

        # 2 failures = min_delay * 2^2 = 8.0
        provider.consecutive_failures = 2
        assert provider._get_backoff_time() == 8.0

        # 3 failures = min_delay * 2^3 = 16.0
        provider.consecutive_failures = 3
        assert provider._get_backoff_time() == 16.0

        # 4 failures = min_delay * 2^4 = 32.0, capped at max_backoff (30.0)
        provider.consecutive_failures = 4
        assert provider._get_backoff_time() == 30.0

    @patch("multi_search_api.providers.duckduckgo.DDGS")
    def test_successful_search(self, mock_ddgs_class):
        """Test successful search with DuckDuckGo."""
        # Setup mock
        mock_ddgs_instance = MagicMock()
        mock_ddgs_class.return_value.__enter__.return_value = mock_ddgs_instance
        mock_ddgs_instance.text.return_value = [
            {"title": "DDG Result 1", "body": "Snippet 1", "href": "https://example1.com"},
            {"title": "DDG Result 2", "body": "Snippet 2", "href": "https://example2.com"},
        ]

        provider = DuckDuckGoProvider(min_delay=0)  # No delay for tests
        provider.last_request_time = 0  # Reset to avoid waiting

        results = provider.search("test query")

        assert len(results) == 2
        assert results[0]["title"] == "DDG Result 1"
        assert results[0]["snippet"] == "Snippet 1"
        assert results[0]["link"] == "https://example1.com"
        assert results[0]["source"] == "duckduckgo"
        assert provider.consecutive_failures == 0

    @patch("multi_search_api.providers.duckduckgo.DDGS")
    def test_rate_limit_error(self, mock_ddgs_class):
        """Test rate limit error handling."""
        from duckduckgo_search.exceptions import RatelimitException

        mock_ddgs_instance = MagicMock()
        mock_ddgs_class.return_value.__enter__.return_value = mock_ddgs_instance
        mock_ddgs_instance.text.side_effect = RatelimitException("Rate limited")

        provider = DuckDuckGoProvider(min_delay=0)
        provider.last_request_time = 0

        with pytest.raises(RateLimitError):
            provider.search("test query")

        assert provider.consecutive_failures == 1
