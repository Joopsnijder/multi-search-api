"""SearXNG search provider with dynamic instance management."""

import json
import logging
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import requests

from multi_search_api.exceptions import RateLimitError
from multi_search_api.providers.base import SearchProvider

logger = logging.getLogger(__name__)


class SearXNGInstanceManager:
    """Manages SearXNG instances with dynamic discovery and caching."""

    INSTANCES_API_URL = "https://searx.space/data/instances.json"
    CACHE_FILE = Path.home() / ".cache" / "multi-search-api" / "searxng_instances.json"
    CACHE_DURATION = timedelta(days=1)

    # Fallback instances if API fails
    FALLBACK_INSTANCES = [
        "https://searx.be",
        "https://searx.work",
        "https://search.bus-hit.me",
        "https://search.sapti.me",
        "https://searx.tiekoetter.com",
    ]

    def __init__(self):
        self.CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        self.instances = []
        self._load_instances()

    def _load_instances(self):
        """Load instances from cache or fetch from API."""
        try:
            # Try to load from cache first
            if self.CACHE_FILE.exists():
                with open(self.CACHE_FILE) as f:
                    cache_data = json.load(f)

                # Check if cache is still valid
                cache_time = datetime.fromisoformat(cache_data.get("cached_at", ""))
                if datetime.now() - cache_time < self.CACHE_DURATION:
                    self.instances = cache_data.get("instances", [])
                    logger.info(f"Loaded {len(self.instances)} SearXNG instances from cache")
                    return

            # Cache is stale or doesn't exist, fetch from API
            self._fetch_and_cache_instances()

        except Exception as e:
            logger.warning(f"Failed to load instances: {e}")
            self.instances = self.FALLBACK_INSTANCES.copy()
            logger.info(f"Using fallback instances: {len(self.instances)}")

    def _fetch_and_cache_instances(self):
        """Fetch instances from API and cache them."""
        try:
            logger.info("Fetching SearXNG instances from API...")
            response = requests.get(self.INSTANCES_API_URL, timeout=10)

            if response.status_code == 200:
                data = response.json()
                instances_data = data.get("instances", {})
                logger.info(f"API returned {len(instances_data)} instances")

                # Filter instances with 100% daily uptime
                good_instances = []
                high_uptime_instances = []
                total_with_uptime = 0

                for url, instance_data in instances_data.items():
                    if isinstance(instance_data, dict):
                        uptime = instance_data.get("uptime", {})
                        if uptime is None:
                            continue  # Skip instances without uptime data
                        uptime_day = uptime.get("uptimeDay")

                        if uptime_day is not None:
                            total_with_uptime += 1
                            # Debug: collect instances with high uptime for fallback
                            if uptime_day >= 99.0:
                                high_uptime_instances.append((url, uptime_day))

                            # Primary filter: 100% uptime
                            if uptime_day == 100.0:
                                if url and url.startswith("http"):
                                    good_instances.append(url)

                logger.info(f"Found {total_with_uptime} instances with uptime data")
                logger.info(f"Found {len(high_uptime_instances)} instances with 99%+ uptime")
                logger.info(f"Found {len(good_instances)} instances with 100% uptime")

                # If no 100% uptime instances, use 99%+ as fallback
                if not good_instances and high_uptime_instances:
                    logger.info("No 100% uptime instances found, using 99%+ uptime instances")
                    good_instances = [
                        url
                        for url, _ in sorted(
                            high_uptime_instances, key=lambda x: x[1], reverse=True
                        )[:10]
                    ]

                if good_instances:
                    self.instances = good_instances

                    # Cache the results
                    cache_data = {
                        "instances": self.instances,
                        "cached_at": datetime.now().isoformat(),
                        "count": len(self.instances),
                    }

                    with open(self.CACHE_FILE, "w") as f:
                        json.dump(cache_data, f, indent=2)

                    logger.info(f"Cached {len(self.instances)} instances with 100% uptime")
                else:
                    raise ValueError("No instances with 100% uptime found")

            else:
                raise ValueError(f"API returned {response.status_code}")

        except Exception as e:
            logger.warning(f"Failed to fetch instances from API: {e}")
            # Fall back to cached instances or fallback list
            if not self.instances:
                self.instances = self.FALLBACK_INSTANCES.copy()
                logger.info("Using hardcoded fallback instances")

    def get_instances(self) -> list[str]:
        """Get list of available instances."""
        return self.instances.copy()

    def refresh_instances(self):
        """Force refresh instances from API."""
        self._fetch_and_cache_instances()


class SearXNGProvider(SearchProvider):
    """SearXNG search provider (free, open source).

    Rate limiting strategy:
    - Tracks rate-limited instances with cooldown period
    - Instances that return 429 are blocked for 5 minutes
    - Raises RateLimitError when all instances are rate-limited
    """

    # Cooldown period for rate-limited instances (5 minutes)
    RATE_LIMIT_COOLDOWN = 300

    def __init__(self, instance_url: str | None = None):
        self.instance_manager = SearXNGInstanceManager()
        self.instances = self.instance_manager.get_instances()
        self.instance_url = instance_url or (
            self.instances[0] if self.instances else "https://searx.be"
        )
        self.current_instance_idx = 0
        # Track rate-limited instances: {url: timestamp_when_blocked}
        self.rate_limited_instances: dict[str, float] = {}

    def _is_instance_rate_limited(self, instance_url: str) -> bool:
        """Check if an instance is currently rate-limited."""
        if instance_url not in self.rate_limited_instances:
            return False

        blocked_time = self.rate_limited_instances[instance_url]
        if time.time() - blocked_time > self.RATE_LIMIT_COOLDOWN:
            # Cooldown expired, remove from rate-limited list
            del self.rate_limited_instances[instance_url]
            logger.info(f"SearXNG instance {instance_url} cooldown expired, available again")
            return False

        return True

    def _mark_instance_rate_limited(self, instance_url: str):
        """Mark an instance as rate-limited."""
        self.rate_limited_instances[instance_url] = time.time()
        logger.warning(
            f"SearXNG instance {instance_url} marked as rate-limited for "
            f"{self.RATE_LIMIT_COOLDOWN}s"
        )

    def _get_available_instances(self) -> list[str]:
        """Get list of instances that are not rate-limited."""
        return [url for url in self.instances if not self._is_instance_rate_limited(url)]

    def rotate_instance(self):
        """Rotate to next available (non-rate-limited) instance."""
        available = self._get_available_instances()
        if available:
            # Find next available instance
            self.current_instance_idx = (self.current_instance_idx + 1) % len(self.instances)
            # Skip rate-limited instances
            attempts = 0
            while self._is_instance_rate_limited(
                self.instances[self.current_instance_idx]
            ) and attempts < len(self.instances):
                self.current_instance_idx = (self.current_instance_idx + 1) % len(self.instances)
                attempts += 1

            self.instance_url = self.instances[self.current_instance_idx]
            logger.info(f"Rotated to SearXNG instance: {self.instance_url}")
        else:
            logger.warning("No available SearXNG instances (all rate-limited)")

    def is_available(self) -> bool:
        """Check if SearXNG is available (has non-rate-limited instances)."""
        return len(self._get_available_instances()) > 0

    def search(self, query: str, **kwargs) -> list[dict[str, Any]]:
        """Search via SearXNG.

        Raises:
            RateLimitError: When all instances are rate-limited
        """
        # Check if any instances are available
        available_instances = self._get_available_instances()
        if not available_instances:
            raise RateLimitError("All SearXNG instances are rate-limited")

        # Try up to the number of available instances
        max_retries = min(3, len(available_instances))

        for _attempt in range(max_retries):
            # Skip if current instance is rate-limited
            if self._is_instance_rate_limited(self.instance_url):
                self.rotate_instance()
                if not self._get_available_instances():
                    raise RateLimitError("All SearXNG instances are rate-limited")
                continue

            try:
                params = {
                    "q": query,
                    "format": "json",
                    "language": "nl",
                    "engines": "google,bing,duckduckgo",
                }

                response = requests.get(
                    f"{self.instance_url}/search",
                    params=params,
                    timeout=10,
                    headers={"User-Agent": "Mozilla/5.0"},
                )

                if response.status_code == 200:
                    data = response.json()
                    results = []

                    for item in data.get("results", [])[:10]:
                        results.append(
                            {
                                "title": item.get("title", ""),
                                "snippet": item.get("content", ""),
                                "link": item.get("url", ""),
                                "source": "searxng",
                            }
                        )

                    logger.info(f"SearXNG search successful: {len(results)} results")
                    return results
                elif response.status_code == 429:
                    # Rate limited - mark instance and rotate
                    self._mark_instance_rate_limited(self.instance_url)
                    self.rotate_instance()
                    # Check if all instances are now rate-limited
                    if not self._get_available_instances():
                        raise RateLimitError("All SearXNG instances are rate-limited")
                else:
                    logger.warning(
                        f"SearXNG instance {self.instance_url} returned {response.status_code}"
                    )
                    self.rotate_instance()

            except RateLimitError:
                # Re-raise RateLimitError
                raise
            except Exception as e:
                logger.warning(f"SearXNG instance {self.instance_url} failed: {e}")
                self.rotate_instance()

        return []
