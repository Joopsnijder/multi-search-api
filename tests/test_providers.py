"""Tests for search providers."""

import pytest
import responses

from multi_search_api.exceptions import RateLimitError
from multi_search_api.providers import (
    BraveProvider,
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
