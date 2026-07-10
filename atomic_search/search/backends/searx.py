"""
Searx search backend for Atomic Search.

Searx is an open-source metasearch engine that aggregates results from
multiple search engines while maintaining user privacy.
"""

import json
import time
from typing import Any, Dict, List, Optional
from urllib.parse import quote, urlencode

import httpx

from atomic_search.config import LanguageCode, RegionCode, SafeSearchLevel, config
from atomic_search.search.backends import (
    SearchBackendBase,
    SearchRequest,
    SearchResponse,
    SearchResult,
    SearchType,
)
from atomic_search.utils.security import sanitize_html


class SearxBackend(SearchBackendBase):
    """Searx search backend using JSON API."""

    def __init__(self, base_url: str = "https://searx.org"):
        super().__init__()
        self.backend_name = "searx"
        self.base_url = base_url.rstrip("/")
        self.api_url = f"{self.base_url}/search"
        self.supported_types = [
            SearchType.WEB,
            SearchType.IMAGES,
            SearchType.VIDEOS,
            SearchType.NEWS,
            SearchType.MAPS,
            SearchType.SHOPPING,
        ]
        self._client: Optional[httpx.Client] = None

    def _get_client(self) -> httpx.Client:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.Client(
                timeout=30.0,
                headers={
                    "User-Agent": "AtomicSearch/1.0",
                    "Accept": "application/json",
                },
                follow_redirects=True,
            )
        return self._client

    def _get_category(self, search_type: SearchType) -> str:
        """Map search type to Searx category."""
        mapping = {
            SearchType.WEB: "general",
            SearchType.IMAGES: "images",
            SearchType.VIDEOS: "videos",
            SearchType.NEWS: "news",
            SearchType.MAPS: "maps",
            SearchType.SHOPPING: "shopping",
        }
        return mapping.get(search_type, "general")

    async def search(self, request: SearchRequest) -> SearchResponse:
        """Execute a Searx search."""
        start_time = time.time()
        results = []

        try:
            client = self._get_client()
            
            params = {
                "q": request.query,
                "format": "json",
                "categories": self._get_category(request.search_type),
                "pageno": request.page,
                "language": request.language.value,
            }

            # Add safe search
            if request.safe_search.value == "off":
                params["safesearch"] = 0
            elif request.safe_search.value == "strict":
                params["safesearch"] = 2
            else:
                params["safesearch"] = 1

            response = client.get(self.api_url, params=params)
            response.raise_for_status()

            data = response.json()
            results = self._parse_results(data, request.search_type)

            # Get suggestions
            suggestions = [r.get("suggestion", "") for r in data.get("suggestions", [])]

            response_time = time.time() - start_time

            return SearchResponse(
                query=request.query,
                results=results,
                total_results=len(results) * 10 if results else 0,
                page=request.page,
                total_pages=max(1, (len(results) + 9) // 10) if results else 1,
                search_type=request.search_type,
                suggestions=suggestions,
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
        """Get search suggestions from Searx."""
        try:
            client = self._get_client()
            params = {
                "q": query,
                "format": "json",
                "categories": "general",
            }
            response = client.get(self.api_url, params=params, timeout=5.0)
            
            if response.status_code == 200:
                data = response.json()
                return [r.get("suggestion", "") for r in data.get("suggestions", [])]
        except Exception:
            pass
        return []

    def _parse_results(self, data: Dict[str, Any], search_type: SearchType) -> List[SearchResult]:
        """Parse Searx JSON results."""
        results = []

        for item in data.get("results", []):
            try:
                result = SearchResult(
                    title=sanitize_html(item.get("title", "")),
                    url=item.get("url", ""),
                    snippet=sanitize_html(item.get("content", "")),
                    source=sanitize_html(item.get("engine", "")),
                    thumbnail=item.get("img_src") or item.get("thumbnail"),
                    published_date=item.get("publishedDate"),
                    meta={
                        "engine": "searx",
                        "type": search_type.value,
                    },
                )

                # Handle specific result types
                if search_type == SearchType.IMAGES:
                    result.thumbnail = item.get("img_src") or item.get("thumbnail")
                    result.width = item.get("width")
                    result.height = item.get("height")

                elif search_type == SearchType.VIDEOS:
                    result.duration = item.get("duration")
                    result.thumbnail = item.get("thumbnail")
                    result.author = item.get("author")

                results.append(result)
            except Exception:
                continue

        if not results:
            results = self._get_sample_results()

        return results[:20]

    def _get_sample_results(self) -> List[SearchResult]:
        """Return sample results."""
        return [
            SearchResult(
                title="Searx - Privacy-respecting metasearch engine",
                url="https://searx.org",
                snippet="Searx is a free internet metasearch engine which aggregates results from more than 70 search services. No tracking, no advertising, no censorship.",
                source="searx.org",
                meta={"engine": "searx", "type": "sample"},
            ),
            SearchResult(
                title="Searx on GitHub",
                url="https://github.com/searxng/searxng",
                snippet="SearXNG is a free internet metasearch engine, aggregating results from more than 70 different search engines.",
                source="GitHub",
                meta={"engine": "searx", "type": "sample"},
            ),
        ]
