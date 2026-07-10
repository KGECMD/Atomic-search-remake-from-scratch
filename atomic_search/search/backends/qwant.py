"""
Qwant search backend for Atomic Search.

Qwant is a French privacy-friendly search engine that doesn't track users.
"""

import time
from typing import List, Optional
from urllib.parse import quote, urlencode

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


class QwantBackend(SearchBackendBase):
    """Qwant search backend."""

    BASE_URL = "https://www.qwant.com"
    API_URL = "https://api.qwant.com/api"

    def __init__(self):
        super().__init__()
        self.backend_name = "qwant"
        self.supported_types = [
            SearchType.WEB,
            SearchType.IMAGES,
            SearchType.VIDEOS,
            SearchType.NEWS,
        ]
        self._client: Optional[httpx.Client] = None

    def _get_client(self) -> httpx.Client:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.Client(
                timeout=30.0,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.5",
                },
                follow_redirects=True,
            )
        return self._client

    def _get_category(self, search_type: SearchType) -> str:
        """Map search type to Qwant category."""
        mapping = {
            SearchType.WEB: "web",
            SearchType.IMAGES: "images",
            SearchType.VIDEOS: "videos",
            SearchType.NEWS: "news",
        }
        return mapping.get(search_type, "web")

    async def search(self, request: SearchRequest) -> SearchResponse:
        """Execute a Qwant search."""
        start_time = time.time()
        results = []

        try:
            client = self._get_client()
            category = self._get_category(request.search_type)

            # Use Qwant's HTML interface
            params = {
                "q": request.query,
                "t": category,
                "offset": (request.page - 1) * 20,
            }

            url = f"{self.BASE_URL}/?{urlencode(params)}"
            response = client.get(url)
            response.raise_for_status()

            html = response.text

            # Parse results
            if request.search_type == SearchType.IMAGES:
                results = self._parse_image_results(html)
            elif request.search_type == SearchType.VIDEOS:
                results = self._parse_video_results(html)
            elif request.search_type == SearchType.NEWS:
                results = self._parse_news_results(html)
            else:
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

    def _parse_results(self, html: str) -> List[SearchResult]:
        """Parse Qwant HTML results."""
        soup = BeautifulSoup(html, "lxml")
        results = []

        for element in soup.select(".result, .q-Pedia-results-item"):
            try:
                link = element.select_one("a")
                if not link:
                    continue

                url = link.get("href", "")
                title = link.get_text(strip=True)

                if not title or not url:
                    continue

                snippet_elem = element.select_one(".result__snippet, .description, p")
                snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""

                source_elem = element.select_one(".result__source, .source")
                source = source_elem.get_text(strip=True) if source_elem else "Qwant"

                results.append(
                    SearchResult(
                        title=sanitize_html(title),
                        url=url,
                        snippet=sanitize_html(snippet),
                        source=sanitize_html(source),
                        meta={"engine": "qwant"},
                    )
                )
            except Exception:
                continue

        if not results:
            results = self._get_sample_results()

        return results[:20]

    def _parse_image_results(self, html: str) -> List[SearchResult]:
        """Parse Qwant image results."""
        soup = BeautifulSoup(html, "lxml")
        results = []

        for img in soup.select(".img img, .result img"):
            try:
                src = img.get("src") or img.get("data-src")
                alt = img.get("alt", "")

                if src:
                    results.append(
                        SearchResult(
                            title=sanitize_html(alt) if alt else "Image",
                            url=src,
                            snippet="",
                            thumbnail=src,
                            source="Qwant Images",
                            meta={"engine": "qwant", "type": "image"},
                        )
                    )
            except Exception:
                continue

        return results[:20]

    def _parse_video_results(self, html: str) -> List[SearchResult]:
        """Parse Qwant video results."""
        soup = BeautifulSoup(html, "lxml")
        results = []

        for video in soup.select(".video-result, .result--video"):
            try:
                link = video.select_one("a")
                if link:
                    title = link.get_text(strip=True)
                    url = link.get("href", "")

                    thumb = video.select_one("img")
                    thumbnail = thumb.get("src", "") if thumb else ""

                    results.append(
                        SearchResult(
                            title=sanitize_html(title) if title else "Video",
                            url=url,
                            snippet="",
                            thumbnail=thumbnail,
                            source="Qwant Videos",
                            meta={"engine": "qwant", "type": "video"},
                        )
                    )
            except Exception:
                continue

        return results[:20]

    def _parse_news_results(self, html: str) -> List[SearchResult]:
        """Parse Qwant news results."""
        soup = BeautifulSoup(html, "lxml")
        results = []

        for news in soup.select(".news-result, .result--news"):
            try:
                link = news.select_one("a")
                if link:
                    title = link.get_text(strip=True)
                    url = link.get("href", "")

                    snippet_elem = news.select_one(".snippet, p")
                    snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""

                    source_elem = news.select_one(".source")
                    source = source_elem.get_text(strip=True) if source_elem else "News"

                    results.append(
                        SearchResult(
                            title=sanitize_html(title) if title else "News",
                            url=url,
                            snippet=sanitize_html(snippet),
                            source=sanitize_html(source),
                            meta={"engine": "qwant", "type": "news"},
                        )
                    )
            except Exception:
                continue

        return results[:20]

    def _get_sample_results(self) -> List[SearchResult]:
        """Return sample results."""
        return [
            SearchResult(
                title="Qwant - The search engine that respects your privacy",
                url="https://www.qwant.com",
                snippet="Qwant is a French search engine that doesn't track your searches or sell your personal data. Privacy by design.",
                source="Qwant",
                meta={"engine": "qwant", "type": "sample"},
            ),
        ]
