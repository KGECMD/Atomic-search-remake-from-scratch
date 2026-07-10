"""
Wikipedia search backend for Atomic Search.

Uses the Wikipedia API for direct answers and knowledge search.
"""

import time
from typing import List, Optional
from urllib.parse import quote

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


class WikipediaBackend(SearchBackendBase):
    """Wikipedia search backend using their REST API."""

    API_URL = "https://en.wikipedia.org/api/rest_v1"
    SEARCH_URL = "https://en.wikipedia.org/w/api.php"

    def __init__(self):
        super().__init__()
        self.backend_name = "wikipedia"
        self.supported_types = [
            SearchType.WEB,
            SearchType.NEWS,  # For recent articles
        ]
        self._client: Optional[httpx.Client] = None

    def _get_client(self) -> httpx.Client:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.Client(
                timeout=30.0,
                headers={
                    "User-Agent": "AtomicSearch/1.0 (privacy-focused search engine)",
                    "Accept": "application/json",
                },
                follow_redirects=True,
            )
        return self._client

    async def search(self, request: SearchRequest) -> SearchResponse:
        """Execute a Wikipedia search."""
        start_time = time.time()
        results = []

        try:
            client = self._get_client()

            # Use the search API
            params = {
                "action": "query",
                "list": "search",
                "srsearch": request.query,
                "format": "json",
                "srlimit": 20,
                "srprop": "snippet",
            }

            # Adjust for language
            if request.language.value == "zh":
                self.SEARCH_URL = "https://zh.wikipedia.org/w/api.php"
            elif request.language.value == "de":
                self.SEARCH_URL = "https://de.wikipedia.org/w/api.php"
            elif request.language.value == "fr":
                self.SEARCH_URL = "https://fr.wikipedia.org/w/api.php"
            elif request.language.value == "es":
                self.SEARCH_URL = "https://es.wikipedia.org/w/api.php"
            elif request.language.value == "ja":
                self.SEARCH_URL = "https://ja.wikipedia.org/w/api.php"
            elif request.language.value == "ru":
                self.SEARCH_URL = "https://ru.wikipedia.org/w/api.php"
            else:
                self.SEARCH_URL = "https://en.wikipedia.org/w/api.php"

            response = client.get(self.SEARCH_URL, params=params)
            response.raise_for_status()

            data = response.json()
            search_results = data.get("query", {}).get("search", [])

            for item in search_results:
                # Clean HTML from snippet
                snippet = item.get("snippet", "")
                snippet = snippet.replace("<span class=\"searchmatch\">", "")
                snippet = snippet.replace("</span>", "")
                snippet = snippet.replace("&quot;", '"').replace("&amp;", "&")
                snippet = snippet.replace("&lt;", "<").replace("&gt;", ">")

                page_id = item.get("pageid")
                url = f"https://en.wikipedia.org/wiki?curid={page_id}"

                # Try to get summary
                summary = await self._get_summary(page_id)

                results.append(
                    SearchResult(
                        title=sanitize_html(item.get("title", "")),
                        url=url,
                        snippet=sanitize_html(snippet) if snippet else (summary[:200] + "..." if summary else ""),
                        source="Wikipedia",
                        meta={
                            "engine": "wikipedia",
                            "page_id": page_id,
                            "word_count": item.get("wordcount", 0),
                        },
                    )
                )

            response_time = time.time() - start_time

            return SearchResponse(
                query=request.query,
                results=results,
                total_results=len(results),
                page=request.page,
                total_pages=max(1, (len(results) + 9) // 10),
                search_type=request.search_type,
                instant_answer=results[0].snippet if results else None,
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

    async def _get_summary(self, page_id: int) -> Optional[str]:
        """Get a summary for a Wikipedia page."""
        try:
            client = self._get_client()
            url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{page_id}"
            response = client.get(url, timeout=5.0)

            if response.status_code == 200:
                data = response.json()
                return data.get("extract", "")
        except Exception:
            pass
        return None

    async def get_suggestions(self, query: str) -> List[str]:
        """Get search suggestions from Wikipedia."""
        if not query or len(query) < 2:
            return []

        try:
            client = self._get_client()
            params = {
                "action": "opensearch",
                "search": query,
                "limit": 10,
                "namespace": 0,
                "format": "json",
            }

            response = client.get(self.SEARCH_URL, params=params, timeout=5.0)

            if response.status_code == 200:
                data = response.json()
                if len(data) > 1:
                    return data[1]  # List of suggestions
        except Exception:
            pass

        return []

    def _get_sample_results(self) -> List[SearchResult]:
        """Return sample results."""
        return [
            SearchResult(
                title="Wikipedia - The Free Encyclopedia",
                url="https://en.wikipedia.org/wiki/Main_Page",
                snippet="Wikipedia is a multilingual free online encyclopedia written and maintained by a community of volunteers, known as Wikipedians, through open collaboration.",
                source="Wikipedia",
                meta={"engine": "wikipedia", "type": "sample"},
            ),
        ]
