"""
DuckDuckGo search backend for Atomic Search.

Uses the DuckDuckGo Instant Answer API which provides:
- Abstract text (Wikipedia-style summaries)
- Related topics
- Definition answers
- Quick answers
"""

import time
from typing import Any, Dict, List, Optional
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


class DuckDuckGoBackend(SearchBackendBase):
    """DuckDuckGo search backend using JSON API."""

    API_URL = "https://api.duckduckgo.com/"
    SUGGEST_URL = "https://duckduckgo.com/ac/"

    def __init__(self):
        super().__init__()
        self.backend_name = "duckduckgo"
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
                    "User-Agent": "AtomicSearch/1.0 (privacy-focused search engine)",
                    "Accept": "application/json",
                    "Accept-Language": "en-US,en;q=0.5",
                },
                follow_redirects=True,
            )
        return self._client

    async def search(self, request: SearchRequest) -> SearchResponse:
        """Execute a DuckDuckGo search using the JSON API."""
        start_time = time.time()
        results = []
        instant_answer = None

        try:
            client = self._get_client()
            
            # Use the full DuckDuckGo API
            params = {
                "q": request.query,
                "format": "json",
                "no_html": 0,
                "skip_disambig": 0,
            }

            response = client.get(self.API_URL, params=params)
            response.raise_for_status()

            data = response.json()

            # Extract instant answer
            if data.get("Definition"):
                instant_answer = data["Definition"]
            elif data.get("Answer"):
                instant_answer = data["Answer"]
            elif data.get("AbstractText"):
                instant_answer = data["AbstractText"]

            # Extract main abstract result
            if data.get("AbstractText") and data.get("AbstractURL"):
                results.append(
                    SearchResult(
                        title=sanitize_html(data.get("Heading", request.query.title())),
                        url=data["AbstractURL"],
                        snippet=sanitize_html(data["AbstractText"]),
                        source=sanitize_html(data.get("AbstractSource", "DuckDuckGo")),
                        thumbnail=data.get("Image"),
                        meta={"engine": "duckduckgo", "type": "abstract"},
                    )
                )

            # Extract definition result
            if data.get("Definition") and data.get("DefinitionURL"):
                results.append(
                    SearchResult(
                        title=sanitize_html(data.get("Heading", "Definition")),
                        url=data["DefinitionURL"],
                        snippet=sanitize_html(data["Definition"]),
                        source=sanitize_html(data.get("DefinitionSource", "Dictionary")),
                        meta={"engine": "duckduckgo", "type": "definition"},
                    )
                )

            # Extract Answer result
            if data.get("Answer"):
                results.append(
                    SearchResult(
                        title=sanitize_html(f"Quick Answer: {request.query}"),
                        url=data.get("AnswerURL", ""),
                        snippet=sanitize_html(data["Answer"]),
                        source=sanitize_html(data.get("AnswerType", "Quick Answer")),
                        meta={"engine": "duckduckgo", "type": "answer"},
                    )
                )

            # Extract related topics (these are often the most useful)
            for topic in data.get("RelatedTopics", [])[:20]:
                if topic.get("Text") and topic.get("FirstURL"):
                    text = topic.get("Text", "")
                    url = topic.get("FirstURL", "")
                    
                    # Skip if it's just a category header
                    if text.startswith("Category:"):
                        continue
                    
                    # Extract icon source for better titles
                    icon = topic.get("Icon", {})
                    icon_url = icon.get("URL", "") if icon else ""
                    
                    # Clean and format the result
                    results.append(
                        SearchResult(
                            title=sanitize_html(text[:100] + ("..." if len(text) > 100 else "")),
                            url=url,
                            snippet=sanitize_html(text),
                            source=sanitize_html(icon_url.split("/")[-1].replace(".png", "").replace(".ico", "").title() if icon_url else "DuckDuckGo"),
                            meta={"engine": "duckduckgo", "type": "related"},
                        )
                    )

            # Extract results from Results array (often Wikipedia/external)
            for item in data.get("Results", [])[:15]:
                if item.get("Text") and item.get("FirstURL"):
                    text = item.get("Text", "")
                    url = item.get("FirstURL", "")
                    
                    # Extract source from Result if available
                    result_html = item.get("Result", "")
                    source = "DuckDuckGo"
                    if ">" in result_html and "<" in result_html:
                        parts = result_html.split(">")
                        if len(parts) > 1:
                            source = parts[1].split("<")[0] if parts[1] else "DuckDuckGo"
                    
                    results.append(
                        SearchResult(
                            title=sanitize_html(text[:100] + ("..." if len(text) > 100 else "")),
                            url=url,
                            snippet=sanitize_html(text),
                            source=sanitize_html(source),
                            meta={"engine": "duckduckgo", "type": "result"},
                        )
                    )

            # Get suggestions
            suggestions = await self.get_suggestions(request.query)

            response_time = time.time() - start_time

            # If no results, get sample results
            if not results:
                results = self._get_sample_results(request.query)

            return SearchResponse(
                query=request.query,
                results=results,
                total_results=len(results) * 10 if results else 0,
                page=request.page,
                total_pages=max(1, (len(results) + 9) // 10) if results else 1,
                search_type=request.search_type,
                suggestions=suggestions,
                instant_answer=instant_answer,
                response_time=response_time,
            )

        except httpx.HTTPError as e:
            return SearchResponse(
                query=request.query,
                results=self._get_sample_results(request.query),
                error=f"HTTP error: {str(e)}",
                response_time=time.time() - start_time,
            )
        except Exception as e:
            return SearchResponse(
                query=request.query,
                results=self._get_sample_results(request.query),
                error=f"Search error: {str(e)}",
                response_time=time.time() - start_time,
            )

    async def get_suggestions(self, query: str) -> List[str]:
        """Get search suggestions from DuckDuckGo."""
        if not query or len(query) < 2:
            return []

        try:
            client = self._get_client()
            url = f"{self.SUGGEST_URL}?q={quote(query)}&format=json"
            response = client.get(url, timeout=5.0)

            if response.status_code == 200:
                data = response.json()
                return [item.get("phrase", "") for item in data if item.get("phrase")]
        except Exception:
            pass

        return []

    def _get_sample_results(self, query: str) -> List[SearchResult]:
        """Return sample results based on query."""
        return [
            SearchResult(
                title=f"Search results for: {query}" if query else "Welcome to Atomic Search",
                url=f"https://duckduckgo.com/?q={quote(query) if query else 'search'}",
                snippet=f"No results found for '{query}'. Try a different search term.",
                source="DuckDuckGo",
                meta={"engine": "duckduckgo", "type": "sample"},
            ),
        ]
