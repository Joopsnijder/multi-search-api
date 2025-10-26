"""Basic usage examples for multi-search-api."""

import os

from multi_search_api import SmartSearchTool


def basic_search():
    """Basic search example."""
    print("=" * 60)
    print("BASIC SEARCH EXAMPLE")
    print("=" * 60)

    # Initialize (uses environment variables for API keys)
    search = SmartSearchTool()

    # Perform a search
    result = search.search("Python programming tutorials")

    print(f"\nQuery: {result['query']}")
    print(f"Provider used: {result['provider']}")
    print(f"Cache hit: {result['cache_hit']}")
    print(f"Results found: {len(result['results'])}\n")

    # Display top 3 results
    for i, item in enumerate(result["results"][:3], 1):
        print(f"{i}. {item['title']}")
        print(f"   {item['snippet'][:100]}...")
        print(f"   {item['link']}\n")


def search_with_api_keys():
    """Search with explicit API keys."""
    print("=" * 60)
    print("SEARCH WITH EXPLICIT API KEYS")
    print("=" * 60)

    # Initialize with explicit API keys
    search = SmartSearchTool(
        serper_api_key=os.getenv("SERPER_API_KEY"),
        brave_api_key=os.getenv("BRAVE_API_KEY"),
    )

    result = search.search("AI news 2025", num_results=5)

    print(f"\nProvider: {result['provider']}")
    print(f"Found {len(result['results'])} results\n")

    for i, item in enumerate(result["results"], 1):
        print(f"{i}. {item['title']}")


def check_status():
    """Check provider and cache status."""
    print("=" * 60)
    print("PROVIDER AND CACHE STATUS")
    print("=" * 60)

    search = SmartSearchTool()

    # Get status
    status = search.get_status()

    print("\nActive Providers:")
    for provider in status["providers"]:
        print(f"  - {provider}")

    if status["rate_limited_providers"]:
        print("\nRate Limited Providers:")
        for provider in status["rate_limited_providers"]:
            print(f"  - {provider}")

    if "cache" in status:
        print("\nCache Statistics:")
        print(f"  Entries: {status['cache']['total_entries']}")
        print(f"  File size: {status['cache']['cache_file_size']} bytes")


def cache_management():
    """Cache management examples."""
    print("=" * 60)
    print("CACHE MANAGEMENT")
    print("=" * 60)

    search = SmartSearchTool()

    # First search (will be cached)
    print("\n1. First search (will be cached)...")
    result1 = search.search("machine learning basics")
    print(f"   Provider: {result1['provider']}, Cache hit: {result1['cache_hit']}")

    # Second search (should hit cache)
    print("\n2. Second search (should hit cache)...")
    result2 = search.search("machine learning basics")
    print(f"   Provider: {result2['provider']}, Cache hit: {result2['cache_hit']}")

    # Clear cache
    print("\n3. Clearing expired cache entries...")
    search.clear_cache()
    print("   Cache cleared")

    # Disable caching
    print("\n4. Disabling cache...")
    search.disable_cache()
    result3 = search.search("machine learning basics")
    print(f"   Provider: {result3['provider']}, Cache hit: {result3['cache_hit']}")


if __name__ == "__main__":
    # Run examples
    basic_search()
    print("\n")

    search_with_api_keys()
    print("\n")

    check_status()
    print("\n")

    cache_management()
