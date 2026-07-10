"""
SearXNG backend for Atomic Search.

Uses public SearXNG instances to aggregate search results.
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


# SearXNG instances - tried in order until one works
SEARXNG_INSTANCES = [
    "https://searxng.org",
    "https://searx.privacytech.io",
    "https://searx.de",
    "https://darmet.ovh",
]


class SearxngBackend(SearchBackendBase):
    """SearXNG search backend using public instances."""

    def __init__(self, instance_url: str = None):
        super().__init__()
        self.backend_name = "searxng"
        self.instance_url = instance_url
        self.supported_types = [SearchType.WEB, SearchType.IMAGES, SearchType.VIDEOS, SearchType.NEWS]
        self._client: Optional[httpx.Client] = None
        self._available_instance: Optional[str] = None

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
        """Execute a SearXNG search."""
        start_time = time.time()
        results = []

        try:
            # Try to find an available instance
            instance = self._find_available_instance()
            if not instance:
                return SearchResponse(
                    query=request.query,
                    results=self._get_fallback_results(),
                    error="No SearXNG instance available",
                    response_time=time.time() - start_time,
                )

            self._available_instance = instance
            results = await self._search_instance(request, instance)

            # If no results, try another instance or fallback
            if not results:
                for other_instance in SEARXNG_INSTANCES:
                    if other_instance != instance:
                        results = await self._search_instance(request, other_instance)
                        if results:
                            break

            # If still no results, use fallback
            if not results:
                results = self._get_fallback_results()

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

    def _find_available_instance(self) -> Optional[str]:
        """Find an available SearXNG instance."""
        if self.instance_url:
            return self.instance_url

        client = self._get_client()
        
        for instance in SEARXNG_INSTANCES:
            try:
                response = client.get(f"{instance}/search?q=test&format=json", timeout=5.0)
                if response.status_code == 200:
                    return instance
            except Exception:
                continue

        return None

    async def _search_instance(self, request: SearchRequest, instance: str) -> List[SearchResult]:
        """Search using a specific SearXNG instance."""
        try:
            client = self._get_client()
            
            params = {
                "q": request.query,
                "format": "json",
                "engines": "bing,duckduckgo,wikipedia",
                "language": "en",
                "pageno": request.page,
            }

            response = client.get(
                f"{instance}/search",
                params=params,
                timeout=15.0
            )

            if response.status_code != 200:
                return []

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

            return results[:20]

        except Exception:
            return []

    async def _get_suggestions(self, query: str) -> List[str]:
        """Get search suggestions."""
        if not query or len(query) < 2:
            return []

        try:
            client = self._get_client()
            
            if self._available_instance:
                response = client.get(
                    f"{self._available_instance}/search?q={quote(query)}&format=json",
                    timeout=5.0
                )

                if response.status_code == 200:
                    data = response.json()
                    suggestions = data.get("suggestions", [])
                    return suggestions[:8]
        except Exception:
            pass

        return []

    async def get_suggestions(self, query: str) -> List[str]:
        """Get search suggestions."""
        return await self._get_suggestions(query)

    def _get_fallback_results(self) -> List[SearchResult]:
        """Return fallback results."""
        return [
            SearchResult(
                title="Search with SearXNG",
                url="https://searxng.org",
                snippet="Try your search on SearXNG",
                source="SearXNG",
                meta={"engine": "searxng", "type": "fallback"},
            ),
        ]
