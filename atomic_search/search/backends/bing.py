"""
Bing search backend for Atomic Search.

Implements web search using Bing's API.
"""

import json
import time
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode

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


class BingBackend(SearchBackendBase):
    """Bing search backend."""

    BASE_URL = "https://www.bing.com/search"

    def __init__(self):
        super().__init__()
        self.backend_name = "bing"
        self.supported_types = [
            SearchType.WEB,
            SearchType.IMAGES,
            SearchType.VIDEOS,
            SearchType.NEWS,
            SearchType.SHOPPING,
            SearchType.MAPS,
        ]
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=30.0,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.5",
                    "Accept-Encoding": "gzip, deflate, br",
                    "DNT": "1",
                    "Connection": "keep-alive",
                    "Upgrade-Insecure-Requests": "1",
                },
                follow_redirects=True,
            )
        return self._client

    def _get_mkt(self, region: RegionCode, language: LanguageCode) -> str:
        """Get Bing market code."""
        markets = {
            (RegionCode.US, LanguageCode.EN): "en-US",
            (RegionCode.UK, LanguageCode.EN): "en-GB",
            (RegionCode.DE, LanguageCode.DE): "de-DE",
            (RegionCode.FR, LanguageCode.FR): "fr-FR",
            (RegionCode.ES, LanguageCode.ES): "es-ES",
            (RegionCode.IT, LanguageCode.IT): "it-IT",
            (RegionCode.NL, LanguageCode.NL): "nl-NL",
            (RegionCode.PL, LanguageCode.EN): "pl-PL",
            (RegionCode.RU, LanguageCode.RU): "ru-RU",
            (RegionCode.JP, LanguageCode.JA): "ja-JP",
            (RegionCode.CN, LanguageCode.ZH): "zh-CN",
            (RegionCode.KR, LanguageCode.KO): "ko-KR",
            (RegionCode.IN, LanguageCode.EN): "en-IN",
            (RegionCode.AU, LanguageCode.EN): "en-AU",
            (RegionCode.CA, LanguageCode.EN): "en-CA",
            (RegionCode.BR, LanguageCode.PT): "pt-BR",
            (RegionCode.GLOBAL, LanguageCode.EN): "en-US",
        }
        return markets.get((region, language), "en-US")

    def _get_safe_search_param(self, level: SafeSearchLevel) -> str:
        """Convert safe search level to Bing parameter."""
        mapping = {
            SafeSearchLevel.OFF: "Off",
            SafeSearchLevel.MODERATE: "Moderate",
            SafeSearchLevel.STRICT: "Strict",
        }
        return mapping.get(level, "Moderate")

    def _build_url(self, request: SearchRequest) -> str:
        """Build the Bing search URL."""
        params: Dict[str, Any] = {
            "q": request.query,
            "mkt": self._get_mkt(request.region, request.language),
            "safeSearch": self._get_safe_search_param(request.safe_search),
            "first": str((request.page - 1) * 10 + 1),
        }

        # Add search type specific parameters
        if request.search_type == SearchType.IMAGES:
            params["ensearch"] = "1"
        elif request.search_type == SearchType.VIDEOS:
            params["video"] = "1"
        elif request.search_type == SearchType.NEWS:
            params["news"] = "1"
        elif request.search_type == SearchType.SHOPPING:
            params["shopping"] = "1"
        elif request.search_type == SearchType.MAPS:
            params["mkt"] = "en-US"  # Maps use a different endpoint
            params["q"] = f"maps {request.query}"

        if request.time_period:
            time_map = {"day": "d", "week": "w", "month": "m", "year": "y"}
            params["qft"] = f"+filterui:age-lt{time_map.get(request.time_period, 'y')}"

        return f"{self.BASE_URL}?{urlencode(params)}"

    async def search(self, request: SearchRequest) -> SearchResponse:
        """Execute a Bing search."""
        start_time = time.time()

        try:
            client = await self._get_client()
            url = self._build_url(request)

            response = await client.get(url)
            response.raise_for_status()

            html = response.text
            results = self._parse_results(html, request.search_type)

            # Get suggestions
            suggestions = await self.get_suggestions(request.query)

            response_time = time.time() - start_time

            return SearchResponse(
                query=request.query,
                results=results,
                total_results=len(results) * 10,
                page=request.page,
                total_pages=5,
                search_type=request.search_type,
                suggestions=suggestions,
                response_time=response_time,
            )

        except httpx.HTTPError as e:
            return SearchResponse(
                query=request.query,
                results=[],
                error=f"HTTP error: {str(e)}",
                response_time=time.time() - start_time,
            )
        except Exception as e:
            return SearchResponse(
                query=request.query,
                results=[],
                error=f"Search error: {str(e)}",
                response_time=time.time() - start_time,
            )

    def _parse_results(self, html: str, search_type: SearchType) -> List[SearchResult]:
        """Parse Bing HTML results."""
        soup = BeautifulSoup(html, "lxml")
        results = []

        if search_type == SearchType.IMAGES:
            return self._parse_image_results(soup)
        elif search_type == SearchType.VIDEOS:
            return self._parse_video_results(soup)
        elif search_type == SearchType.NEWS:
            return self._parse_news_results(soup)

        # Web search results
        for result in soup.select(".b_algo"):
            try:
                title_elem = result.select_one("h2 a")
                snippet_elem = result.select_one(".b_caption p")
                source_elem = result.select_one(".b_attribution")

                if title_elem:
                    title = sanitize_html(title_elem.get_text(strip=True))
                    url = title_elem.get("href", "")
                    snippet = ""
                    if snippet_elem:
                        snippet = sanitize_html(snippet_elem.get_text(strip=True))
                    source = ""
                    if source_elem:
                        source = sanitize_html(source_elem.get_text(strip=True))

                    results.append(
                        SearchResult(
                            title=title,
                            url=url,
                            snippet=snippet,
                            source=source,
                            meta={"engine": "bing"},
                        )
                    )
            except Exception:
                continue

        # Related searches
        for related in soup.select(".b_rrsr a")[:5]:
            try:
                results.append(
                    SearchResult(
                        title=sanitize_html(related.get_text(strip=True)),
                        url=related.get("href", ""),
                        snippet="Related search",
                        meta={"engine": "bing", "type": "related"},
                    )
                )
            except Exception:
                continue

        return results

    def _parse_image_results(self, soup: BeautifulSoup) -> List[SearchResult]:
        """Parse image search results."""
        results = []

        for img in soup.select(".iusc"):
            try:
                data = img.get("m", "{}")
                import json
                info = json.loads(data)

                title = sanitize_html(info.get("t", "Image"))
                url = info.get("murl", "")
                thumbnail = info.get("turl", "")
                width = info.get("w")
                height = info.get("h")
                source = info.get("s", "")

                results.append(
                    SearchResult(
                        title=title,
                        url=url,
                        snippet="",
                        thumbnail=thumbnail,
                        width=str(width) if width else None,
                        height=str(height) if height else None,
                        source=source,
                        meta={"engine": "bing", "type": "image"},
                    )
                )
            except Exception:
                continue

        return results

    def _parse_video_results(self, soup: BeautifulSoup) -> List[SearchResult]:
        """Parse video search results."""
        results = []

        for video in soup.select(".videos"):
            try:
                title_elem = video.select_one(".mc_title a")
                thumb_elem = video.select_one(".mc_thumb img")
                meta_elem = video.select_one(".meta")
                link_elem = video.select_one(".mc_title a")

                if title_elem and link_elem:
                    title = sanitize_html(title_elem.get_text(strip=True))
                    url = link_elem.get("href", "")
                    thumbnail = thumb_elem.get("src") if thumb_elem else None
                    meta = sanitize_html(meta_elem.get_text(strip=True)) if meta_elem else ""

                    results.append(
                        SearchResult(
                            title=title,
                            url=url,
                            snippet=meta,
                            thumbnail=thumbnail,
                            meta={"engine": "bing", "type": "video"},
                        )
                    )
            except Exception:
                continue

        return results

    def _parse_news_results(self, soup: BeautifulSoup) -> List[SearchResult]:
        """Parse news search results."""
        results = []

        for news in soup.select(".news-card"):
            try:
                title_elem = news.select_one(".title a")
                snippet_elem = news.select_one(".snippet")
                source_elem = news.select_one(".source")
                time_elem = news.select_one(".time")

                if title_elem:
                    title = sanitize_html(title_elem.get_text(strip=True))
                    url = title_elem.get("href", "")
                    snippet = sanitize_html(snippet_elem.get_text(strip=True)) if snippet_elem else ""
                    source = sanitize_html(source_elem.get_text(strip=True)) if source_elem else None
                    published = sanitize_html(time_elem.get_text(strip=True)) if time_elem else None

                    results.append(
                        SearchResult(
                            title=title,
                            url=url,
                            snippet=snippet,
                            source=source,
                            published_date=published,
                            meta={"engine": "bing", "type": "news"},
                        )
                    )
            except Exception:
                continue

        return results

    async def get_suggestions(self, query: str) -> List[str]:
        """Get search suggestions from Bing."""
        if not query or len(query) < 2:
            return []

        try:
            client = await self._get_client()
            params = {
                "q": query,
                "mkt": "en-US",
                "setlang": "en-US",
            }

            response = await client.get(
                "https://www.bing.com/AS/Suggestions",
                params=params
            )
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "lxml")
            suggestions = []

            for li in soup.select("li")[:10]:
                text = li.get_text(strip=True)
                if text:
                    suggestions.append(sanitize_html(text))

            return suggestions

        except Exception:
            return []

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
