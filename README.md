# Multi-Search-API

**Intelligent multi-provider search API with automatic fallback and caching**

[![PyPI version](https://badge.fury.io/py/multi-search-api.svg)](https://badge.fury.io/py/multi-search-api)
[![Python Support](https://img.shields.io/pypi/pyversions/multi-search-api.svg)](https://pypi.org/project/multi-search-api/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Features

- 🔄 **Automatic Fallback**: Seamlessly switches between multiple search providers
- 💾 **Smart Caching**: 1-day result caching to reduce API calls
- 🚦 **Rate Limit Handling**: Automatic detection and provider rotation on HTTP 402/429
- 🔌 **Multiple Providers**: Support for Serper, SearXNG, Brave, DuckDuckGo, and Google scraping
- 🎯 **Zero Configuration**: Works out of the box with sensible defaults
- 📊 **Provider Management**: Track status, cache stats, and rate limits

## Supported Search Providers

| Provider | Type | Quality | Rate Limits | API Key Required |
|----------|------|---------|-------------|------------------|
| **Serper** | API | ⭐⭐⭐⭐⭐ Excellent | 2,500 free/month | Yes |
| **SearXNG** | Meta-search | ⭐⭐⭐⭐ Good | Unlimited | No |
| **Brave** | API | ⭐⭐⭐⭐⭐ Excellent | 1 req/sec free | Yes |
| **DuckDuckGo** | Scraping | ⭐⭐⭐⭐ Good | ~20 req/min | No |
| **Google Scraper** | Scraping | ⭐⭐⭐ Fair | Use sparingly | No |

## Installation

```bash
pip install multi-search-api
```

## Quick Start

### Basic Usage

```python
from multi_search_api import SmartSearchTool

# Initialize (uses environment variables for API keys)
search = SmartSearchTool()

# Perform a search
result = search.search("Python programming tutorials")

print(f"Provider used: {result['provider']}")
print(f"Results found: {len(result['results'])}")

for item in result['results'][:3]:
    print(f"\n{item['title']}")
    print(f"{item['snippet']}")
    print(f"{item['link']}")
```

### With API Keys

```python
from multi_search_api import SmartSearchTool

# Initialize with explicit API keys
search = SmartSearchTool(
    serper_api_key="your-serper-key",
    brave_api_key="your-brave-key"
)

result = search.search("AI news 2025", num_results=10)
```

### Environment Variables

Create a `.env` file:

```env
SERPER_API_KEY=your_serper_api_key_here
BRAVE_API_KEY=your_brave_api_key_here
```

The tool will automatically load these keys.

## Advanced Usage

### Recent Content Search

```python
import asyncio
from multi_search_api import SmartSearchTool

async def search_recent():
    search = SmartSearchTool()

    # Search for content from last 14 days
    results = await search.search_recent_content(
        query="AI breakthroughs",
        max_results=10,
        days_back=14,
        language="en"
    )

    return results

results = asyncio.run(search_recent())
```

### Cache Management

```python
search = SmartSearchTool()

# Get cache statistics
stats = search.get_status()
print(f"Cache entries: {stats['cache']['total_entries']}")

# Clear expired cache entries
search.clear_cache()

# Disable caching
search.disable_cache()

# Re-enable caching
search.enable_cache()
```

### Rate Limit Management

```python
search = SmartSearchTool()

# Check provider status
status = search.get_status()
print(f"Active providers: {status['providers']}")
print(f"Rate limited: {status['rate_limited_providers']}")

# Reset rate limit tracking (e.g., new day)
search.reset_rate_limits()
```

### CrewAI Integration

```python
from crewai import Agent, Task
from multi_search_api import SmartSearchTool

search_tool = SmartSearchTool()

researcher = Agent(
    role='Research Analyst',
    goal='Find relevant information on the web',
    tools=[search_tool],
    verbose=True
)

task = Task(
    description="Research the latest AI developments",
    agent=researcher
)
```

## How It Works

### Provider Priority

1. **Serper** - Best quality results, 2,500 free searches/month
2. **SearXNG** - Free unlimited searches, variable quality
3. **Brave** - Excellent quality, 1 req/sec limit on free tier
4. **DuckDuckGo** - Free, no API key, ~20 req/min with exponential backoff
5. **Google Scraper** - Last resort fallback

### Automatic Fallback

When a provider fails or hits rate limits (HTTP 402/429), the tool automatically:

1. Detects the failure
2. Marks the provider as rate-limited for the session
3. Tries the next available provider
4. Caches successful results to minimize future API calls

### Caching Strategy

- Results are cached for 24 hours
- Cache keys based on: query, num_results, language
- Automatic cleanup of expired entries
- Optional cache disable for real-time needs

## API Reference

### SmartSearchTool

```python
SmartSearchTool(
    ollama_api_key: str | None = None,
    serper_api_key: str | None = None,
    brave_api_key: str | None = None,
    searxng_instance: str | None = None,
    enable_cache: bool = True
)
```

#### Methods

- `search(query: str, **kwargs) -> dict`: Perform a search
- `search_recent_content(query: str, max_results: int, days_back: int, language: str) -> list`: Search recent content
- `get_status() -> dict`: Get provider and cache status
- `clear_cache()`: Clear expired cache entries
- `reset_rate_limits()`: Reset rate limit tracking
- `disable_cache()`: Disable caching
- `enable_cache()`: Enable caching
- `run(query: str) -> str`: CrewAI-compatible search method

### Search Result Format

```python
{
    "query": "search query",
    "provider": "SerperProvider",
    "cache_hit": False,
    "timestamp": "2025-10-26T10:30:00",
    "results": [
        {
            "title": "Result Title",
            "snippet": "Result description or snippet",
            "link": "https://example.com",
            "source": "serper"
        },
        # ... more results
    ]
}
```

## Getting API Keys

### Serper (Recommended)

1. Visit [serper.dev](https://serper.dev)
2. Sign up for free account
3. Get 2,500 free searches per month
4. Copy your API key

### Brave Search

1. Visit [brave.com/search/api](https://brave.com/search/api/)
2. Sign up for API access
3. Free tier: 1 request/second
4. Copy your subscription token

### SearXNG (No Key Needed)

SearXNG is automatically configured with public instances. No setup required!

### DuckDuckGo (No Key Needed)

DuckDuckGo is included by default. No setup required!

Features:

- No API key required
- Automatic rate limiting (~20 requests/minute)
- Exponential backoff on rate limit errors

## Configuration

### Custom Cache Directory

```python
from multi_search_api.cache import SearchResultCache

cache = SearchResultCache(cache_file="custom/path/cache.json")
```

### Custom SearXNG Instance

```python
search = SmartSearchTool(searxng_instance="https://your-searxng.com")
```

## Development

```bash
# Clone repository
git clone https://github.com/joop/multi-search-api.git
cd multi-search-api

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run with coverage
pytest --cov=multi_search_api --cov-report=html

# Format code
ruff format .

# Lint code
ruff check .
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Author

**Joop Snijder**

## Changelog

### 0.1.9 (2025-12-12)

- Success messages now always printed: `🔍 query → X results (Provider)`
- Makes search progress visible regardless of logging level

### 0.1.8 (2025-12-11)

- Warnings are now shown only once per session (subsequent occurrences logged as debug)
- Reduces log spam from repeated rate-limit and failure messages

### 0.1.7 (2025-12-11)

- Improved provider fallback: automatically tries next provider on errors or empty results
- Added exception handling for all provider errors (not just RateLimitError)
- SearXNG now raises RateLimitError when all instances exhausted (triggers proper fallback)
- Better logging with emojis to show fallback flow (✅ success, ⏭️ skip, ⚠️ rate limit)
- Added 4 new tests for provider fallback scenarios

### 0.1.6 (2025-12-03)

- Track failed/broken SearXNG instances (JSON errors, 500 errors) with 2 min cooldown
- Rate-limited instances (429) still use 5 min cooldown
- Increased max retries from 3 to 5 instances per search
- More efficient instance rotation skipping unavailable instances

### 0.1.5 (2025-12-03)

- Improved SearXNG rate limit handling with instance cooldown (5 min)
- Rate-limited SearXNG instances are now tracked and skipped
- Raises `RateLimitError` when all SearXNG instances are rate-limited

### 0.1.4 (2025-12-03)

- Updated DuckDuckGo dependency from `duckduckgo-search` to `ddgs` (package renamed)

### 0.1.3 (2025-12-03)

- DuckDuckGo is now a standard dependency (no longer optional)

### 0.1.2 (2025-12-03)

- Added DuckDuckGo search provider (free, no API key)
- Exponential backoff rate limiting for DuckDuckGo

### 0.1.1 (2025-11-03)

- Fixed thread-safety issues in SearchResultCache
- Added threading.Lock for concurrent cache operations
- Comprehensive thread-safety tests

### 0.1.0 (2025-10-26)

- Initial release
- Support for Serper, SearXNG, Brave, and Google scraping
- Automatic fallback and rate limit handling
- 24-hour result caching
- CrewAI integration support
