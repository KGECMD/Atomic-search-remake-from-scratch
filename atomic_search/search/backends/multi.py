"""
Multi-source search backend for Atomic Search.

Combines results from multiple sources:
- Bing HTML (primary)
- DuckDuckGo HTML 
- Wikipedia API
- Brave Search HTML
- Startpage
- SearXNG
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


# SearXNG instances
SEARXNG_INSTANCES = [
    "https://searxng.org",
    "https://searx.space",
    "https://searx.privacytech.io",
]


class MultiSourceBackend(SearchBackendBase):
    """Multi-source search backend combining Bing, DuckDuckGo, Wikipedia, Brave, Startpage, SearXNG."""

    def __init__(self):
        super().__init__()
        self.backend_name = "multi"
        self.supported_types = [SearchType.WEB, SearchType.IMAGES, SearchType.VIDEOS, SearchType.NEWS]
        self._client: Optional[httpx.Client] = None

    def _get_client(self) -> httpx.Client:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.Client(
                timeout=30.0,
                headers={
                    "Accept-Language": "en-US,en;q=0.9",
                },
                follow_redirects=True,
            )
        return self._client

    async def search(self, request: SearchRequest) -> SearchResponse:
        """Execute a multi-source search."""
        start_time = time.time()
        results = []

        # Primary: Bing HTML (most reliable)
        bing_results = await self._search_bing(request)
        if bing_results:
            results.extend(bing_results)

        # Secondary: DuckDuckGo HTML
        ddg_results = await self._search_duckduckgo(request)
        if ddg_results:
            results.extend(ddg_results)

        # Tertiary: Wikipedia
        wiki_results = await self._search_wikipedia(request)
        if wiki_results:
            results.extend(wiki_results)

        # Quaternary: Brave Search
        brave_results = await self._search_brave(request)
        if brave_results:
            results.extend(brave_results)

        # Quinary: Startpage
        startpage_results = await self._search_startpage(request)
        if startpage_results:
            results.extend(startpage_results)

        # Senary: SearXNG
        searxng_results = await self._search_searxng(request)
        if searxng_results:
            results.extend(searxng_results)

        # If no results, use fallback
        if not results:
            results = self._get_fallback_results(request.query)

        # Deduplicate by URL
        seen_urls = set()
        unique_results = []
        for r in results:
            if r.url not in seen_urls:
                seen_urls.add(r.url)
                unique_results.append(r)

        response_time = time.time() - start_time

        return SearchResponse(
            query=request.query,
            results=unique_results[:30],
            total_results=len(unique_results) * 10 if unique_results else 0,
            page=request.page,
            total_pages=max(1, (len(unique_results) + 9) // 10) if unique_results else 1,
            search_type=request.search_type,
            suggestions=await self._get_suggestions(request.query),
            response_time=response_time,
        )

    async def _search_bing(self, request: SearchRequest) -> List[SearchResult]:
        """Search using Bing HTML."""
        try:
            client = self._get_client()
            url = f"https://www.bing.com/search?q={quote(request.query)}&mkt=en-US"
            response = client.get(url, timeout=15.0)
            
            if response.status_code != 200:
                return []

            soup = BeautifulSoup(response.text, "lxml")
            results = []

            for element in soup.select("li.b_algo"):
                try:
                    title_elem = element.select_one("h2 a")
                    if not title_elem:
                        continue

                    url = title_elem.get("href", "")
                    title = title_elem.get_text(strip=True)

                    if not url or not title:
                        continue

                    # Clean title and extract source
                    source = "Bing"
                    for sep in [" - ", " | ", " – "]:
                        if sep in title:
                            parts = title.split(sep)
                            potential_source = parts[-1].strip()
                            if "." in potential_source or len(potential_source) < 30:
                                source = potential_source
                                title = sep.join(parts[:-1]).strip()
                            break

                    # Get snippet
                    snippet = ""
                    for selector in ["p", ".b_paractl", ".b_snippet"]:
                        snippet_elem = element.select_one(selector)
                        if snippet_elem:
                            text = snippet_elem.get_text(strip=True)
                            if text and len(text) > 20:
                                snippet = text
                                break

                    results.append(
                        SearchResult(
                            title=sanitize_html(title),
                            url=url,
                            snippet=sanitize_html(snippet) if snippet else "",
                            source=sanitize_html(source),
                            meta={"engine": "bing", "type": "web"},
                        )
                    )
                except Exception:
                    continue

            return results[:15]
        except Exception:
            return []

    async def _search_duckduckgo(self, request: SearchRequest) -> List[SearchResult]:
        """Search using DuckDuckGo HTML."""
        try:
            client = self._get_client()
            url = f"https://html.duckduckgo.com/html/?q={quote(request.query)}&kl=us-en"
            response = client.get(url, timeout=15.0)
            
            if response.status_code != 200:
                return []

            soup = BeautifulSoup(response.text, "lxml")
            results = []

            for result in soup.select("div.result"):
                try:
                    title_elem = result.select_one("a.result__a, h2 a")
                    if not title_elem:
                        continue

                    url = title_elem.get("href", "")
                    title = title_elem.get_text(strip=True)

                    if not url or "duckduckgo" in url.lower():
                        continue

                    snippet_elem = result.select_one(".result__snippet, p")
                    snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""

                    results.append(
                        SearchResult(
                            title=sanitize_html(title),
                            url=url,
                            snippet=sanitize_html(snippet) if snippet else "",
                            source=self._extract_domain(url),
                            meta={"engine": "duckduckgo", "type": "web"},
                        )
                    )
                except Exception:
                    continue

            return results[:10]
        except Exception:
            return []

    async def _search_wikipedia(self, request: SearchRequest) -> List[SearchResult]:
        """Search using Wikipedia API."""
        try:
            client = self._get_client()
            params = {
                "action": "query",
                "list": "search",
                "srsearch": request.query,
                "format": "json",
                "srlimit": 8,
            }

            response = client.get(
                "https://en.wikipedia.org/w/api.php",
                params=params,
                timeout=15.0
            )

            if response.status_code != 200:
                return []

            data = response.json()
            results = []

            for item in data.get("query", {}).get("search", []):
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

    async def _search_brave(self, request: SearchRequest) -> List[SearchResult]:
        """Search using Brave Search."""
        try:
            client = self._get_client()
            url = f"https://search.brave.com/search?q={quote(request.query)}&source=web"
            response = client.get(url, timeout=15.0)
            
            if response.status_code != 200:
                return []

            soup = BeautifulSoup(response.text, "lxml")
            results = []

            for element in soup.select("[data-type='web'], .snippet, article"):
                try:
                    a = element.select_one("a[href^='http']")
                    if not a:
                        continue

                    url = a.get("href", "")
                    if "brave.com" in url:
                        continue

                    title = element.select_one(".snippet-title, h2, h3, .title")
                    title_text = title.get_text(strip=True) if title else a.get_text(strip=True)

                    snippet = element.select_one(".snippet-description, .description, p")
                    snippet_text = snippet.get_text(strip=True) if snippet else ""

                    if title_text and url.startswith("http"):
                        results.append(
                            SearchResult(
                                title=sanitize_html(title_text),
                                url=url,
                                snippet=sanitize_html(snippet_text) if snippet_text else "",
                                source=self._extract_domain(url),
                                meta={"engine": "brave", "type": "web"},
                            )
                        )
                except Exception:
                    continue

            return results[:8]
        except Exception:
            return []

    async def _search_startpage(self, request: SearchRequest) -> List[SearchResult]:
        """Search using Startpage."""
        try:
            client = self._get_client()
            url = f"https://www.startpage.com/do/search?q={quote(request.query)}&cat=web"
            response = client.get(url, timeout=15.0)
            
            if response.status_code != 200:
                return []

            soup = BeautifulSoup(response.text, "lxml")
            results = []

            for element in soup.select("section.w-gl__result, .w-gl__result, article"):
                try:
                    a = element.select_one("a.w-gl__result-title, h3 a, a[href^='http']")
                    if not a:
                        continue

                    url = a.get("href", "")
                    if not url.startswith("http"):
                        continue

                    title = a.get_text(strip=True)
                    snippet = element.select_one(".w-gl__description, .description, p")
                    snippet_text = snippet.get_text(strip=True) if snippet else ""

                    if title:
                        results.append(
                            SearchResult(
                                title=sanitize_html(title),
                                url=url,
                                snippet=sanitize_html(snippet_text) if snippet_text else "",
                                source=self._extract_domain(url),
                                meta={"engine": "startpage", "type": "web"},
                            )
                        )
                except Exception:
                    continue

            return results[:8]
        except Exception:
            return []

    async def _search_searxng(self, request: SearchRequest) -> List[SearchResult]:
        """Search using SearXNG."""
        try:
            client = self._get_client()
            
            for instance in SEARXNG_INSTANCES:
                try:
                    params = {
                        "q": request.query,
                        "format": "json",
                        "language": "en",
                        "engines": "bing,duckduckgo",
                    }

                    response = client.get(
                        f"{instance}/search",
                        params=params,
                        timeout=10.0
                    )

                    if response.status_code == 200:
                        data = response.json()
                        results = []

                        for item in data.get("results", []):
                            if not item.get("url") or not item.get("title"):
                                continue

                            results.append(
                                SearchResult(
                                    title=sanitize_html(item.get("title", "")),
                                    url=item.get("url", ""),
                                    snippet=sanitize_html(item.get("content", "")) if item.get("content") else "",
                                    source=sanitize_html(item.get("engine", "SearXNG")),
                                    meta={"engine": "searxng", "type": "web"},
                                )
                            )

                        if results:
                            return results[:10]
                except Exception:
                    continue

            return []
        except Exception:
            return []

    async def _get_suggestions(self, query: str) -> List[str]:
        """Get search suggestions."""
        if not query or len(query) < 2:
            return []

        try:
            client = self._get_client()
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

    def _get_fallback_results(self, query: str) -> List[SearchResult]:
        """Get fallback results."""
        return [
            SearchResult(
                title=f"Search for: {query}",
                url=f"https://searxng.org/search?q={quote(query)}",
                snippet=f"Try searching for '{query}' on SearXNG",
                source="SearXNG",
                meta={"engine": "fallback", "type": "search"},
            ),
        ]

    async def get_suggestions(self, query: str) -> List[str]:
        """Get search suggestions."""
        return await self._get_suggestions(query)
