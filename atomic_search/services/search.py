"""
Search service for Atomic Search.

Orchestrates search operations across backends, with support for:
- Multiple backends
- Caching
- Result enhancement
- Community voting integration
"""

import asyncio
import hashlib
import time
from typing import Any, Dict, List, Optional

from atomic_search.config import (
    LanguageCode,
    RegionCode,
    SafeSearchLevel,
    SearchBackend,
    config,
)
from atomic_search.search.backends import (
    SearchBackendBase,
    SearchRequest,
    SearchResponse,
    SearchResult,
    SearchType,
    backend_manager,
)
from atomic_search.search.backends.duckduckgo import DuckDuckGoBackend
from atomic_search.search.backends.bing import BingBackend


class SearchService:
    """Main search service class."""

    def __init__(self):
        self._cache: Dict[str, SearchResponse] = {}
        self._cache_ttl: Dict[str, float] = {}
        self._lock = asyncio.Lock()
        self._initialized = False
        self._backends_initialized = False

    def _initialize_backends(self) -> None:
        """Initialize backends synchronously."""
        if self._backends_initialized:
            return

        # Register DuckDuckGo JSON API backend
        try:
            backend_manager.register(SearchBackend.DUCKDUCKGO, DuckDuckGoBackend())
        except Exception:
            pass
        
        # Register Bing API backend
        try:
            backend_manager.register(SearchBackend.BING, BingBackend())
        except Exception:
            pass
        
        # Register Multi-source backend (primary)
        try:
            from atomic_search.search.backends.multi import MultiSourceBackend
            backend_manager.register("multi", MultiSourceBackend())
        except Exception:
            pass
        
        # Register Startpage backend
        try:
            from atomic_search.search.backends.startpage import StartpageBackend
            backend_manager.register(SearchBackend.STARTPAGE, StartpageBackend())
        except Exception:
            pass
        
        # Register Mwmbl backend
        try:
            from atomic_search.search.backends.mwmbl import MwmblBackend
            backend_manager.register(SearchBackend.MWMBL, MwmblBackend())
        except Exception:
            pass
        
        # Register Searx backend
        try:
            from atomic_search.search.backends.searx import SearxBackend
            backend_manager.register(SearchBackend.SEARX, SearxBackend())
        except Exception:
            pass
        
        # Register Bing HTML backend
        try:
            from atomic_search.search.backends.bing_html import BingHTMLBackend
            backend_manager.register("bing_html", BingHTMLBackend())
        except Exception:
            pass
        
        # Register Wikipedia backend
        try:
            from atomic_search.search.backends.wikipedia import WikipediaBackend
            backend_manager.register("wikipedia", WikipediaBackend())
        except Exception:
            pass
        
        # Register Qwant backend
        try:
            from atomic_search.search.backends.qwant import QwantBackend
            backend_manager.register("qwant", QwantBackend())
        except Exception:
            pass

        # Register Brave Search backend
        try:
            from atomic_search.search.backends.brave import brave_search
            backend_manager.register("brave", brave_search)
        except Exception:
            pass

        # Register Ecosia backend
        try:
            from atomic_search.search.backends.ecosia import ecosia_search
            backend_manager.register("ecosia", ecosia_search)
        except Exception:
            pass

        # Register Mojeek backend
        try:
            from atomic_search.search.backends.mojeek import mojeek_search
            backend_manager.register("mojeek", mojeek_search)
        except Exception:
            pass

        # Register Swisscows backend
        try:
            from atomic_search.search.backends.swisscows import swisscows_search
            backend_manager.register("swisscows", swisscows_search)
        except Exception:
            pass

        self._backends_initialized = True

    async def initialize(self) -> None:
        """Initialize the search service and register backends."""
        self._initialize_backends()
        self._initialized = True

    def _get_cache_key(self, request: SearchRequest) -> str:
        """Generate a cache key for a search request."""
        key_data = f"{request.query}:{request.search_type.value}:{request.page}:{request.language.value}:{request.region.value}:{request.safe_search.value}"
        return hashlib.md5(key_data.encode()).hexdigest()

    def _is_cache_valid(self, key: str) -> bool:
        """Check if a cache entry is still valid."""
        if key not in self._cache_ttl:
            return False
        return time.time() < self._cache_ttl[key]

    async def _get_from_cache(self, key: str) -> Optional[SearchResponse]:
        """Get a cached response."""
        async with self._lock:
            if self._is_cache_valid(key):
                return self._cache.get(key)
        return None

    async def _save_to_cache(self, key: str, response: SearchResponse) -> None:
        """Save a response to cache."""
        async with self._lock:
            self._cache[key] = response
            self._cache_ttl[key] = time.time() + config.SEARCH_CACHE_TIMEOUT

    async def search(
        self,
        query: str,
        search_type: SearchType = SearchType.WEB,
        page: int = 1,
        language: LanguageCode = None,
        region: RegionCode = None,
        safe_search: SafeSearchLevel = None,
        time_period: Optional[str] = None,
        use_cache: bool = True,
    ) -> SearchResponse:
        """Execute a search with the configured backend."""
        self._initialize_backends()

        # Use defaults from config
        language = language or config.DEFAULT_LANGUAGE
        region = region or config.DEFAULT_REGION
        safe_search = safe_search or config.SAFE_SEARCH

        # Create search request
        request = SearchRequest(
            query=query,
            search_type=search_type,
            page=page,
            language=language,
            region=region,
            safe_search=safe_search,
            time_period=time_period,
        )

        # Check cache
        if use_cache and config.ENABLE_RESPONSE_CACHE:
            cache_key = self._get_cache_key(request)
            cached_response = await self._get_from_cache(cache_key)
            if cached_response:
                return cached_response

        # Get backend - handle both string and enum
        backend_name = config.SEARCH_BACKEND
        if isinstance(backend_name, str):
            backend = backend_manager.get(backend_name)
        else:
            backend = backend_manager.get(backend_name.value if hasattr(backend_name, 'value') else backend_name)
        
        if not backend:
            backend = backend_manager.get(SearchBackend.DUCKDUCKGO)

        # Execute search
        response = await backend.search(request)

        # Enhance results with vote statistics
        if response.results:
            response = await self._enhance_results(response)

        # Cache response
        if use_cache and config.ENABLE_RESPONSE_CACHE and not response.error:
            cache_key = self._get_cache_key(request)
            await self._save_to_cache(cache_key, response)

        return response

    async def search_all(
        self,
        query: str,
        search_types: List[SearchType] = None,
        page: int = 1,
    ) -> Dict[SearchType, SearchResponse]:
        """Execute searches across multiple types in parallel."""
        if search_types is None:
            search_types = [SearchType.WEB]

        tasks = [self.search(query, st, page) for st in search_types]
        responses = await asyncio.gather(*tasks)

        return dict(zip(search_types, responses))

    async def get_suggestions(self, query: str) -> List[str]:
        """Get search suggestions."""
        self._initialize_backends()

        backend = backend_manager.get(config.SEARCH_BACKEND)
        if not backend:
            backend = backend_manager.get(SearchBackend.DUCKDUCKGO)

        return await backend.get_suggestions(query)

    async def _enhance_results(self, response: SearchResponse) -> SearchResponse:
        """Enhance search results with vote statistics and metadata."""
        # This would integrate with the voting service in a real implementation
        # For now, we'll just pass through the results
        for result in response.results:
            if result.votes is None:
                result.votes = 0
            if result.upvotes is None:
                result.upvotes = 0
            if result.downvotes is None:
                result.downvotes = 0

        return response

    def clear_cache(self) -> None:
        """Clear the search cache."""
        self._cache.clear()
        self._cache_ttl.clear()

    async def close(self) -> None:
        """Close all backend connections."""
        for backend in backend_manager._backends.values():
            if hasattr(backend, "close"):
                await backend.close()


# Global search service instance
search_service = SearchService()
