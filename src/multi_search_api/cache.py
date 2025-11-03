"""Search result caching functionality."""

import hashlib
import json
import logging
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class SearchResultCache:
    """Cache search results for 1 day to reduce rate limits and improve performance.

    Thread-safe implementation using threading.Lock for concurrent access.
    """

    def __init__(self, cache_file: str | None = None):
        if cache_file:
            self.cache_file = Path(cache_file)
        else:
            # Default to user cache directory
            self.cache_file = Path.home() / ".cache" / "multi-search-api" / "search_results.json"

        self.cache_file.parent.mkdir(parents=True, exist_ok=True)
        self.cache_duration = timedelta(days=1)
        self._lock = threading.Lock()
        self.cache_data = self.load_cache()

    def load_cache(self) -> dict:
        """Load cached search results."""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, encoding="utf-8") as f:
                    return json.load(f)
            except (OSError, json.JSONDecodeError) as e:
                logger.warning(f"Failed to load search cache: {e}")
        return {}

    def save_cache(self):
        """Save cache data to file."""
        try:
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(self.cache_data, f, indent=2, ensure_ascii=False)
        except OSError as e:
            logger.error(f"Failed to save search cache: {e}")

    def _generate_cache_key(self, query: str, provider: str, **kwargs) -> str:
        """Generate a unique cache key for a search query."""
        # Create a consistent string from query, provider and relevant kwargs
        key_components = [
            query.lower().strip(),
            provider,
            str(kwargs.get("num_results", 10)),
            str(kwargs.get("language", "nl")),
        ]

        key_string = "|".join(key_components)
        return hashlib.md5(key_string.encode("utf-8")).hexdigest()

    def get_cached_results(
        self, query: str, provider: str, **kwargs
    ) -> list[dict[str, Any]] | None:
        """Get cached results if available and not expired.

        Thread-safe method using lock to prevent concurrent modifications.
        """
        cache_key = self._generate_cache_key(query, provider, **kwargs)

        with self._lock:
            if cache_key not in self.cache_data:
                return None

            cached_entry = self.cache_data[cache_key]
            cached_time = datetime.fromisoformat(cached_entry["timestamp"])

            # Check if cache is still valid (within 1 day)
            if datetime.now() - cached_time > self.cache_duration:
                # Remove expired entry
                del self.cache_data[cache_key]
                self.save_cache()
                return None

            result_count = len(cached_entry["results"])
            logger.info(
                f"Cache hit for query '{query}' with provider '{provider}' - {result_count} results"
            )
            return cached_entry["results"]

    def cache_results(self, query: str, provider: str, results: list[dict[str, Any]], **kwargs):
        """Cache search results.

        Thread-safe method using lock to prevent concurrent modifications.
        """
        cache_key = self._generate_cache_key(query, provider, **kwargs)

        with self._lock:
            self.cache_data[cache_key] = {
                "timestamp": datetime.now().isoformat(),
                "query": query,
                "provider": provider,
                "results": results,
                "result_count": len(results),
            }

            self.save_cache()
            logger.info(
                f"Cached {len(results)} results for query '{query}' with provider '{provider}'"
            )

    def clear_expired_entries(self):
        """Remove all expired cache entries.

        Thread-safe method using lock to prevent concurrent modifications
        during dictionary iteration.
        """
        current_time = datetime.now()

        with self._lock:
            # Create a copy of keys to avoid modifying dict during iteration
            expired_keys = []

            for key, entry in list(self.cache_data.items()):
                try:
                    cached_time = datetime.fromisoformat(entry["timestamp"])
                    if current_time - cached_time > self.cache_duration:
                        expired_keys.append(key)
                except (ValueError, KeyError):
                    # Invalid timestamp or entry, mark for deletion
                    expired_keys.append(key)

            for key in expired_keys:
                del self.cache_data[key]

            if expired_keys:
                self.save_cache()
                logger.info(f"Removed {len(expired_keys)} expired cache entries")

    def get_cache_stats(self) -> dict:
        """Get cache statistics.

        Thread-safe method using lock to prevent concurrent access.
        """
        self.clear_expired_entries()  # Clean up first (already thread-safe)

        with self._lock:
            stats = {
                "total_entries": len(self.cache_data),
                "cache_file_size": (
                    self.cache_file.stat().st_size if self.cache_file.exists() else 0
                ),
                "oldest_entry": None,
                "newest_entry": None,
            }

            if self.cache_data:
                timestamps = []
                for entry in self.cache_data.values():
                    try:
                        timestamps.append(datetime.fromisoformat(entry["timestamp"]))
                    except (ValueError, KeyError):
                        continue

                if timestamps:
                    stats["oldest_entry"] = min(timestamps).isoformat()
                    stats["newest_entry"] = max(timestamps).isoformat()

            return stats
