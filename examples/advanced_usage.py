"""Advanced usage examples for multi-search-api."""

import asyncio

from multi_search_api import SmartSearchTool


async def search_recent_content_example():
    """Example of searching for recent content."""
    print("=" * 60)
    print("RECENT CONTENT SEARCH")
    print("=" * 60)

    search = SmartSearchTool()

    # Search for content from last 14 days
    print("\nSearching for AI breakthroughs from last 14 days...")
    results = await search.search_recent_content(
        query="AI breakthroughs", max_results=10, days_back=14, language="en"
    )

    print(f"\nFound {len(results)} recent results:\n")

    for i, result in enumerate(results[:5], 1):
        print(f"{i}. {result['title']}")
        print(f"   {result['snippet'][:80]}...")
        print(f"   {result['link']}\n")


def rate_limit_handling():
    """Demonstrate rate limit handling."""
    print("=" * 60)
    print("RATE LIMIT HANDLING")
    print("=" * 60)

    search = SmartSearchTool()

    # Show initial status
    print("\nInitial provider status:")
    status = search.get_status()
    print(f"Active providers: {status['providers']}")
    print(f"Rate limited: {status['rate_limited_providers']}")

    # Perform multiple searches (might hit rate limits)
    queries = ["AI", "machine learning", "deep learning", "neural networks", "LLM"]

    for query in queries:
        result = search.search(query, num_results=5)
        print(f"\nQuery: '{query}' - Provider: {result['provider']}")

    # Show final status
    print("\n\nFinal provider status:")
    status = search.get_status()
    print(f"Active providers: {status['providers']}")
    print(f"Rate limited: {status['rate_limited_providers']}")

    # Reset rate limits
    print("\n\nResetting rate limits...")
    search.reset_rate_limits()
    status = search.get_status()
    print(f"Rate limited after reset: {status['rate_limited_providers']}")


def custom_configuration():
    """Example with custom configuration."""
    print("=" * 60)
    print("CUSTOM CONFIGURATION")
    print("=" * 60)

    # Custom cache file location
    search = SmartSearchTool(
        enable_cache=True,
        cache_file="/tmp/my_custom_cache.json",
        searxng_instance="https://searx.be",
    )

    print("\nSearch with custom configuration:")
    result = search.search("Python async programming")

    print(f"Provider: {result['provider']}")
    print(f"Results: {len(result['results'])}")

    # Check cache stats
    status = search.get_status()
    if "cache" in status:
        print(f"\nCache file size: {status['cache']['cache_file_size']} bytes")


def crewai_integration_example():
    """Example of CrewAI integration."""
    print("=" * 60)
    print("CREWAI INTEGRATION")
    print("=" * 60)

    search = SmartSearchTool()

    # Use the run() method which is CrewAI compatible
    print("\nUsing CrewAI-compatible run() method:")
    result_text = search.run("latest Python frameworks 2025")

    print(result_text)


def multiple_searches_comparison():
    """Compare results from multiple searches."""
    print("=" * 60)
    print("MULTIPLE SEARCHES COMPARISON")
    print("=" * 60)

    search = SmartSearchTool()

    queries = [
        "best Python IDE 2025",
        "Python web frameworks",
        "Python data science libraries",
    ]

    for query in queries:
        result = search.search(query, num_results=3)
        print(f"\n\nQuery: '{query}'")
        print(f"Provider: {result['provider']}")
        print(f"Cache hit: {result['cache_hit']}")
        print("\nTop results:")

        for i, item in enumerate(result["results"][:3], 1):
            print(f"  {i}. {item['title']}")


if __name__ == "__main__":
    # Run synchronous examples
    print("Running synchronous examples...\n")
    rate_limit_handling()
    print("\n")

    custom_configuration()
    print("\n")

    crewai_integration_example()
    print("\n")

    multiple_searches_comparison()
    print("\n")

    # Run async example
    print("Running async example...\n")
    asyncio.run(search_recent_content_example())
