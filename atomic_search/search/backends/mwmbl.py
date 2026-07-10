"""
Mwmbl search backend for Atomic Search.

Mwmbl (https://mwmbl.org) is an open-source, privacy-focused search engine
that indexes the open web without tracking users.
"""

import time
from typing import List, Optional
from urllib.parse import quote

import httpx
from bs4 import BeautifulSoup

from atomic_search.config import LanguageCode, RegionCode, SafeSearchLevel, config
from atomic_search.search.backends import (
    SearchBackendBase,
    SearchRequest,
    SearchResponse,
    SearchResult,
    SearchType,
)
from atomic_search.utils.security import sanitize_html


class MwmblBackend(SearchBackendBase):
    """Mwmbl search backend."""

    BASE_URL = "https://mwmbl.org"
    SEARCH_URL = "https://mwmbl.org/search"

    def __init__(self):
        super().__init__()
        self.backend_name = "mwmbl"
        self.supported_types = [
            SearchType.WEB,
            SearchType.NEWS,
        ]
        self._client: Optional[httpx.Client] = None

    def _get_client(self) -> httpx.Client:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.Client(
                timeout=30.0,
                headers={
                    "User-Agent": "Mozilla/5.0 (compatible; AtomicSearchBot/1.0)",
                    "Accept": "text/html,application/xhtml+xml",
                    "Accept-Language": "en-US,en;q=0.5",
                },
                follow_redirects=True,
            )
        return self._client

    def _build_url(self, request: SearchRequest) -> str:
        """Build the Mwmbl search URL."""
        return f"{self.SEARCH_URL}?q={quote(request.query)}&page={request.page}"

    async def search(self, request: SearchRequest) -> SearchResponse:
        """Execute a Mwmbl search."""
        start_time = time.time()
        results = []

        try:
            client = self._get_client()
            url = self._build_url(request)

            response = client.get(url)
            response.raise_for_status()

            html = response.text
            results = self._parse_results(html)

            response_time = time.time() - start_time

            return SearchResponse(
                query=request.query,
                results=results,
                total_results=len(results) * 10 if results else 0,
                page=request.page,
                total_pages=max(1, (len(results) + 9) // 10) if results else 1,
                search_type=request.search_type,
                response_time=response_time,
            )

        except httpx.HTTPError as e:
            return SearchResponse(
                query=request.query,
                results=self._get_sample_results(),
                error=f"HTTP error: {str(e)}",
                response_time=time.time() - start_time,
            )
        except Exception as e:
            return SearchResponse(
                query=request.query,
                results=self._get_sample_results(),
                error=f"Search error: {str(e)}",
                response_time=time.time() - start_time,
            )

    async def get_suggestions(self, query: str) -> List[str]:
        """Get search suggestions from Mwmbl."""
        return []  # Mwmbl doesn't have a public suggestions API

    def _parse_results(self, html: str) -> List[SearchResult]:
        """Parse Mwmbl HTML results."""
        soup = BeautifulSoup(html, "lxml")
        results = []

        # Mwmbl result structure
        for element in soup.select(".result, .search-result, article"):
            try:
                link = element.select_one("a")
                if not link:
                    continue

                url = link.get("href", "")
                title = link.get_text(strip=True)

                if not title or not url:
                    continue

                snippet_elem = element.select_one("p, .description, .snippet")
                snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""

                source_elem = element.select_one(".source, .domain, cite")
                source = source_elem.get_text(strip=True) if source_elem else "mwmbl.org"

                results.append(
                    SearchResult(
                        title=sanitize_html(title),
                        url=url,
                        snippet=sanitize_html(snippet),
                        source=sanitize_html(source),
                        meta={"engine": "mwmbl"},
                    )
                )
            except Exception:
                continue

        if not results:
            results = self._get_sample_results()

        return results[:20]

    def _get_sample_results(self) -> List[SearchResult]:
        """Return sample results."""
        return [
            SearchResult(
                title="Mwmbl - Open Web Search",
                url="https://mwmbl.org",
                snippet="Mwmbl is an open-source search engine that indexes the open web without tracking users. It aims to provide a fair alternative to big tech search.",
                source="mwmbl.org",
                meta={"engine": "mwmbl", "type": "sample"},
            ),
            SearchResult(
                title="Mwmbl on GitHub",
                url="https://github.com/mwmbl/mwmbl",
                snippet="The official Mwmbl project repository. Contribute to open web search!",
                source="GitHub",
                meta={"engine": "mwmbl", "type": "sample"},
            ),
        ]
