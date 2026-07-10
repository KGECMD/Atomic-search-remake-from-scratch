"""
Startpage search backend for Atomic Search.

Startpage is a privacy-focused search engine that uses Google results
while protecting user privacy.
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

# User agents for rotation
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]


class StartpageBackend(SearchBackendBase):
    """Startpage search backend."""

    BASE_URL = "https://www.startpage.com/do/search"

    def __init__(self):
        super().__init__()
        self.backend_name = "startpage"
        self.supported_types = [
            SearchType.WEB,
            SearchType.IMAGES,
            SearchType.VIDEOS,
        ]
        self._client: Optional[httpx.Client] = None
        self._ua_index = 0

    def _get_client(self) -> httpx.Client:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.Client(
                timeout=30.0,
                headers={
                    "User-Agent": USER_AGENTS[self._ua_index],
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.5",
                    "DNT": "1",
                },
                follow_redirects=True,
            )
        return self._client

    def _get_language_code(self, language: "LanguageCode") -> str:  # type: ignore
        """Convert language code to Startpage format."""
        from atomic_search.config import LanguageCode
        mapping = {
            LanguageCode.EN: "english",
            LanguageCode.ES: "spanish",
            LanguageCode.FR: "french",
            LanguageCode.DE: "german",
            LanguageCode.IT: "italian",
            LanguageCode.PT: "portuguese",
            LanguageCode.RU: "russian",
            LanguageCode.ZH: "chinese",
            LanguageCode.JA: "japanese",
            LanguageCode.KO: "korean",
            LanguageCode.AR: "arabic",
            LanguageCode.HI: "hindi",
        }
        return mapping.get(language, "english")

    def _get_region_code(self, region: "RegionCode") -> str:  # type: ignore
        """Convert region code to Startpage format."""
        from atomic_search.config import RegionCode
        mapping = {
            RegionCode.GLOBAL: "world",
            RegionCode.US: "usa",
            RegionCode.UK: "uk",
            RegionCode.DE: "germany",
            RegionCode.FR: "france",
            RegionCode.ES: "spain",
            RegionCode.IT: "italy",
            RegionCode.NL: "netherlands",
            RegionCode.RU: "russia",
            RegionCode.JP: "japan",
            RegionCode.CN: "china",
            RegionCode.KR: "korea",
            RegionCode.IN: "india",
            RegionCode.AU: "australia",
            RegionCode.CA: "canada",
            RegionCode.BR: "brazil",
        }
        return mapping.get(region, "world")

    def _build_url(self, request: SearchRequest) -> str:
        """Build the Startpage search URL."""
        params = {
            "query": request.query,
            "language": self._get_language_code(request.language),
            "region": self._get_region_code(request.region),
            "startpage": str(request.page),
        }

        # Add search type
        if request.search_type == SearchType.IMAGES:
            params["cat"] = "images"
        elif request.search_type == SearchType.VIDEOS:
            params["cat"] = "videos"

        return f"{self.BASE_URL}?{urlencode(params)}"

    def _build_post_data(self, request: SearchRequest) -> dict:
        """Build POST data for Startpage search."""
        return {
            "query": request.query,
            "language": self._get_language_code(request.language),
            "region": self._get_region_code(request.region),
            "startpage": str(request.page),
            "Submit": "Search",
            "cat": "web",
        }

    async def search(self, request: SearchRequest) -> SearchResponse:
        """Execute a Startpage search."""
        start_time = time.time()
        results = []

        try:
            client = self._get_client()
            url = self._build_url(request)

            # Startpage typically works better with POST
            data = self._build_post_data(request)
            response = client.post(url, data=data)
            response.raise_for_status()

            html = response.text

            # Parse results
            if request.search_type == SearchType.IMAGES:
                results = self._parse_image_results(html)
            elif request.search_type == SearchType.VIDEOS:
                results = self._parse_video_results(html)
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

    async def get_suggestions(self, query: str) -> List[str]:
        """Get search suggestions."""
        return []  # Startpage doesn't provide public suggestions API

    def _parse_results(self, html: str) -> List[SearchResult]:
        """Parse Startpage HTML results."""
        soup = BeautifulSoup(html, "lxml")
        results = []

        # Try multiple selectors
        for element in soup.select(".search-result, .result, .w-gl__result"):
            try:
                link = element.select_one("a")
                if not link:
                    continue

                url = link.get("href", "")
                title = link.get_text(strip=True)

                if not title or not url:
                    continue

                snippet_elem = element.select_one(".result-body, .description, p")
                snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""

                source_elem = element.select_one(".result-display-url, .source")
                source = source_elem.get_text(strip=True) if source_elem else "Startpage"

                results.append(
                    SearchResult(
                        title=sanitize_html(title),
                        url=url,
                        snippet=sanitize_html(snippet),
                        source=sanitize_html(source),
                        meta={"engine": "startpage"},
                    )
                )
            except Exception:
                continue

        if not results:
            results = self._get_sample_results()

        return results[:20]

    def _parse_image_results(self, html: str) -> List[SearchResult]:
        """Parse image search results."""
        soup = BeautifulSoup(html, "lxml")
        results = []

        for img in soup.select(".image-result img, .result-image img"):
            try:
                src = img.get("src", "") or img.get("data-src", "")
                alt = img.get("alt", "")

                if src:
                    results.append(
                        SearchResult(
                            title=sanitize_html(alt) if alt else "Image",
                            url=src,
                            snippet="",
                            thumbnail=src,
                            source="Startpage Images",
                            meta={"engine": "startpage", "type": "image"},
                        )
                    )
            except Exception:
                continue

        return results[:20]

    def _parse_video_results(self, html: str) -> List[SearchResult]:
        """Parse video search results."""
        soup = BeautifulSoup(html, "lxml")
        results = []

        for video in soup.select(".video-result, .result-video"):
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
                            source="Startpage Videos",
                            meta={"engine": "startpage", "type": "video"},
                        )
                    )
            except Exception:
                continue

        return results[:20]

    def _get_sample_results(self) -> List[SearchResult]:
        """Return sample results."""
        return [
            SearchResult(
                title="Startpage - Private Search Engine",
                url="https://www.startpage.com",
                snippet="Startpage delivers Google search results with complete privacy. No logging, no tracking, no data collection.",
                source="Startpage",
                meta={"engine": "startpage", "type": "sample"},
            ),
            SearchResult(
                title="Privacy Search Engines Comparison",
                url="https://privacyguides.org",
                snippet="Compare privacy-focused search engines including Startpage, DuckDuckGo, and others.",
                source="Privacy Guides",
                meta={"engine": "sample"},
            ),
        ]
