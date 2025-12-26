"""Google search scraper (last resort fallback)."""

import logging
from typing import Any

import httpx
from justhtml import JustHTML

from multi_search_api.providers.base import SearchProvider

logger = logging.getLogger(__name__)


def _query_one(element, selector):
    """Get first matching element or None."""
    results = element.query(selector)
    return results[0] if results else None


class GoogleScraperProvider(SearchProvider):
    """Last resort: scrape Google search (use carefully!)."""

    def __init__(self):
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "nl-NL,nl;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }

    def is_available(self) -> bool:
        """Always available as last option."""
        return True

    def search(self, query: str, **kwargs) -> list[dict[str, Any]]:
        """Scrape Google search results (last resort)."""
        try:
            # Use httpx for better async support
            with httpx.Client() as client:
                response = client.get(
                    "https://www.google.com/search",
                    params={"q": query, "hl": "nl"},
                    headers=self.headers,
                    timeout=10,
                )

                if response.status_code == 200:
                    doc = JustHTML(response.text)
                    results = []

                    # Parse search results - try multiple selectors as Google changes them
                    search_divs = []

                    # Try different selectors Google uses
                    for selector in ["div.g", "div[data-ved]", ".g", ".tF2Cxc"]:
                        search_divs = doc.query(selector)
                        if search_divs:
                            break

                    if not search_divs:
                        logger.warning("No search result containers found")
                        return []

                    for g in search_divs[:5]:  # Only top 5
                        title_elem = _query_one(g, "h3")
                        if not title_elem:
                            # Try alternative selectors for title
                            title_elem = _query_one(g, "h3, .LC20lb, .DKV0Md")

                        link_elem = _query_one(g, "a")
                        if not link_elem:
                            # Try alternative selectors for link
                            link_elem = _query_one(g, "a[href]")

                        # Try multiple selectors for snippets
                        snippet_elem = None
                        for snippet_selector in [".aCOpRe", ".VwiC3b", ".s3v9rd", ".st"]:
                            snippet_elem = _query_one(g, snippet_selector)
                            if snippet_elem:
                                break

                        if title_elem and link_elem:
                            href = link_elem.attrs.get("href", "")
                            # Clean up href if it's a Google redirect
                            if href.startswith("/url?q="):
                                try:
                                    from urllib.parse import parse_qs, urlparse

                                    parsed = urlparse(href)
                                    href = parse_qs(parsed.query).get("q", [href])[0]
                                except Exception:
                                    pass  # Keep original href if parsing fails

                            results.append(
                                {
                                    "title": title_elem.to_text().strip(),
                                    "snippet": snippet_elem.to_text().strip()
                                    if snippet_elem
                                    else "",
                                    "link": href,
                                    "source": "google_scraper",
                                }
                            )

                    logger.info(f"Google scraper: {len(results)} results")
                    return results

        except Exception as e:
            logger.error(f"Google scraper failed: {e}")

        return []
