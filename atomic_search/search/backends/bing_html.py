"""
Bing HTML search backend for Atomic Search.

Scrapes Bing search results from the HTML interface.
"""

import time
from typing import List, Optional
from urllib.parse import quote

import httpx
from bs4 import BeautifulSoup

from atomic_search.search.backends import (
    SearchBackendBase,
    SearchRequest,
    SearchResponse,
    SearchResult,
    SearchType,
)
from atomic_search.utils.security import sanitize_html


# User agents for rotation
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
]


class BingHTMLBackend(SearchBackendBase):
    """Bing HTML search backend."""

    BASE_URL = "https://www.bing.com/search"

    def __init__(self):
        super().__init__()
        self.backend_name = "bing_html"
        self.supported_types = [
            SearchType.WEB,
            SearchType.IMAGES,
            SearchType.VIDEOS,
            SearchType.NEWS,
        ]
        self._client: Optional[httpx.Client] = None
        self._ua_index = 0
        self._request_count = 0

    def _get_client(self) -> httpx.Client:
        """Get or create HTTP client."""
        if self._client is None:
            # Use default httpx user agent to avoid Bing bot detection
            self._client = httpx.Client(
                timeout=30.0,
                headers={
                    "Accept-Language": "en-US,en;q=0.9",
                },
                follow_redirects=True,
            )
        return self._client

    def _rotate_user_agent(self) -> None:
        """Rotate user agent."""
        self._request_count += 1
        if self._request_count % 5 == 0:
            self._ua_index = (self._ua_index + 1) % len(USER_AGENTS)
            if self._client:
                self._client.headers["User-Agent"] = USER_AGENTS[self._ua_index]

    async def search(self, request: SearchRequest) -> SearchResponse:
        """Execute a Bing search."""
        start_time = time.time()
        results = []

        try:
            self._rotate_user_agent()
            client = self._get_client()
            url = f"{self.BASE_URL}?q={quote(request.query)}&mkt=en-US"
            
            if request.page > 1:
                url += f"&first={(request.page - 1) * 10 + 1}"

            response = client.get(url)
            response.raise_for_status()

            html = response.text
            results = self._parse_results(html)

            # If no results, try Wikipedia as fallback
            if not results:
                wiki_results = await self._search_wikipedia(request)
                if wiki_results:
                    results.extend(wiki_results)

            response_time = time.time() - start_time

            return SearchResponse(
                query=request.query,
                results=results,
                total_results=len(results) * 10 if results else 0,
                page=request.page,
                total_pages=max(1, (len(results) + 9) // 10) if results else 1,
                search_type=request.search_type,
                suggestions=await self._get_suggestions(request.query),
                response_time=response_time,
            )

        except Exception as e:
            return SearchResponse(
                query=request.query,
                results=self._get_fallback_results(),
                error=f"Search error: {str(e)}",
                response_time=time.time() - start_time,
            )

    def _parse_results(self, html: str) -> List[SearchResult]:
        """Parse Bing HTML search results."""
        soup = BeautifulSoup(html, "lxml")
        results = []

        # Try multiple selectors for Bing results
        selectors = [
            "li.b_algo",
            "div.b_algo",
        ]

        for selector in selectors:
            elements = soup.select(selector)
            if elements:
                for element in elements[:30]:
                    try:
                        result = self._parse_result_element(element)
                        if result:
                            results.append(result)
                    except Exception:
                        continue
                if results:
                    break

        return results

    def _parse_result_element(self, element) -> Optional[SearchResult]:
        """Parse a single result element."""
        try:
            # Find title and link
            title_elem = element.select_one("h2 a")
            if not title_elem:
                title_elem = element.select_one("a")

            if not title_elem:
                return None

            url = title_elem.get("href", "")
            title = title_elem.get_text(strip=True)

            if not url or not title:
                return None

            # Clean title - remove source suffix (like " - W3Schools.com")
            source = "Bing"
            for sep in [" - ", " | ", " – "]:
                if sep in title:
                    parts = title.split(sep)
                    potential_source = parts[-1].strip()
                    # Check if it looks like a domain name
                    if "." in potential_source or len(potential_source) < 30:
                        source = potential_source
                        title = sep.join(parts[:-1]).strip()
                    break

            # If source still not found, try to extract from element text
            if source == "Bing":
                element_text = element.get_text()
                # Look for domain patterns in text
                import re
                domain_match = re.search(r'([a-zA-Z0-9][-a-zA-Z0-9]*\.[a-zA-Z]{2,})', element_text)
                if domain_match:
                    potential = domain_match.group(1).replace('www.', '')
                    if len(potential) < 50 and 'http' not in potential:
                        source = potential

            # Get snippet
            snippet = ""
            for selector in ["p", ".b_paractl", ".b_snippet"]:
                snippet_elem = element.select_one(selector)
                if snippet_elem:
                    text = snippet_elem.get_text(strip=True)
                    if text and len(text) > 20:
                        snippet = text
                        break

            return SearchResult(
                title=sanitize_html(title),
                url=url,
                snippet=sanitize_html(snippet) if snippet else "",
                source=sanitize_html(source),
                meta={"engine": "bing", "type": "web"},
            )
        except Exception:
            return None

    async def _search_wikipedia(self, request: SearchRequest) -> List[SearchResult]:
        """Fallback to Wikipedia API."""
        try:
            client = self._get_client()
            
            params = {
                "action": "query",
                "list": "search",
                "srsearch": request.query,
                "format": "json",
                "srlimit": 10,
                "srprop": "snippet|titlesnippet|wordcount",
            }

            response = client.get(
                "https://en.wikipedia.org/w/api.php",
                params=params,
                timeout=15.0
            )

            if response.status_code != 200:
                return []

            data = response.json()
            search_results = data.get("query", {}).get("search", [])

            results = []
            for item in search_results:
                snippet = item.get("snippet", "").replace("<span class=\"searchmatch\">", "").replace("</span>", "")
                snippet = snippet.replace("&quot;", '"').replace("&amp;", "&")
                page_id = item.get("pageid")
                url = f"https://en.wikipedia.org/wiki?curid={page_id}"

                results.append(
                    SearchResult(
                        title=sanitize_html(item.get("title", "")),
                        url=url,
                        snippet=sanitize_html(snippet),
                        source="Wikipedia",
                        meta={"engine": "wikipedia", "type": "article"},
                    )
                )

            return results
        except Exception:
            return []

    async def _get_suggestions(self, query: str) -> List[str]:
        """Get search suggestions."""
        if not query or len(query) < 2:
            return []

        try:
            client = self._get_client()
            
            # Try DuckDuckGo autocomplete
            response = client.get(
                f"https://duckduckgo.com/ac/?q={quote(query)}&format=json",
                timeout=5.0
            )

            if response.status_code == 200:
                data = response.json()
                return [item.get("phrase", "") for item in data if item.get("phrase")][:8]
        except Exception:
            pass

        return []

    async def get_suggestions(self, query: str) -> List[str]:
        """Get search suggestions."""
        return await self._get_suggestions(query)

    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL."""
        if not url:
            return "Unknown"
        try:
            if "//" in url:
                domain = url.split("//")[1].split("/")[0]
                return domain.replace("www.", "")
        except Exception:
            pass
        return "Unknown"

    def _get_fallback_results(self) -> List[SearchResult]:
        """Return fallback results."""
        return [
            SearchResult(
                title="Search with Bing",
                url=f"https://www.bing.com/search?q=search",
                snippet="Try your search on Bing",
                source="Bing",
                meta={"engine": "bing", "type": "fallback"},
            ),
        ]
