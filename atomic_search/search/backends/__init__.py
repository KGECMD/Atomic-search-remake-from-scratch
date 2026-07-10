"""
Search backends package for Atomic Search.

Provides abstraction for multiple search engines:
- DuckDuckGo (default)
- Bing
- Google (limited)
- Searx (self-hosted)
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, TYPE_CHECKING
from urllib.parse import urlencode

if TYPE_CHECKING:
    from atomic_search.config import SearchBackend, SafeSearchLevel, RegionCode, LanguageCode


class SearchType(str, Enum):
    """Types of searches supported."""
    WEB = "web"
    IMAGES = "images"
    VIDEOS = "videos"
    NEWS = "news"
    SHOPPING = "shopping"
    BOOKS = "books"
    MAPS = "maps"
    ACADEMIC = "academic"
    PROGRAMMING = "programming"
    DOCS = "docs"
    FILES = "files"
    PDF = "pdf"
    RSS = "rss"
    ANSWERS = "answers"


@dataclass
class SearchResult:
    """Individual search result."""
    title: str
    url: str
    snippet: str
    thumbnail: Optional[str] = None
    source: Optional[str] = None
    source_icon: Optional[str] = None
    rating: Optional[float] = None
    votes: Optional[int] = None
    upvotes: Optional[int] = None
    downvotes: Optional[int] = None
    published_date: Optional[str] = None
    author: Optional[str] = None
    duration: Optional[str] = None
    width: Optional[str] = None
    height: Optional[str] = None
    file_type: Optional[str] = None
    file_size: Optional[str] = None
    meta: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "title": self.title,
            "url": self.url,
            "snippet": self.snippet,
            "thumbnail": self.thumbnail,
            "source": self.source,
            "source_icon": self.source_icon,
            "rating": self.rating,
            "votes": self.votes,
            "upvotes": self.upvotes,
            "downvotes": self.downvotes,
            "published_date": self.published_date,
            "author": self.author,
            "duration": self.duration,
            "width": self.width,
            "height": self.height,
            "file_type": self.file_type,
            "file_size": self.file_size,
            "meta": self.meta,
        }


@dataclass
class SearchResponse:
    """Response from a search query."""
    query: str
    results: List[SearchResult]
    total_results: Optional[int] = None
    page: int = 1
    total_pages: int = 1
    search_type: SearchType = SearchType.WEB
    suggestions: List[str] = field(default_factory=list)
    related_queries: List[str] = field(default_factory=list)
    instant_answer: Optional[str] = None
    error: Optional[str] = None
    response_time: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "query": self.query,
            "results": [r.to_dict() for r in self.results],
            "total_results": self.total_results,
            "page": self.page,
            "total_pages": self.total_pages,
            "search_type": self.search_type.value,
            "suggestions": self.suggestions,
            "related_queries": self.related_queries,
            "instant_answer": self.instant_answer,
            "error": self.error,
            "response_time": self.response_time,
        }


@dataclass
class SearchRequest:
    """Search request parameters."""
    query: str
    search_type: SearchType = SearchType.WEB
    page: int = 1
    language: "LanguageCode" = None  # type: ignore
    region: "RegionCode" = None  # type: ignore
    safe_search: "SafeSearchLevel" = None  # type: ignore
    time_period: Optional[str] = None  # day, week, month, year
    sort_by: Optional[str] = None
    price_range: Optional[str] = None
    file_type: Optional[str] = None
    domain: Optional[str] = None
    country: Optional[str] = None
    location: Optional[str] = None

    def __post_init__(self):
        from atomic_search.config import LanguageCode, RegionCode, SafeSearchLevel
        if self.language is None:
            self.language = LanguageCode.EN
        if self.region is None:
            self.region = RegionCode.GLOBAL
        if self.safe_search is None:
            self.safe_search = SafeSearchLevel.MODERATE

    def to_url_params(self) -> Dict[str, Any]:
        """Convert to URL parameters."""
        params = {
            "q": self.query,
            "kl": f"{self.region.value}-{self.language.value}",
        }

        if self.page > 1:
            params["start"] = (self.page - 1) * 10

        if self.safe_search.value != "moderate":
            params["safe"] = self.safe_search.value

        if self.time_period:
            params["tbs"] = f"qdr:{self.time_period[0]}"

        if self.sort_by:
            params["sort"] = self.sort_by

        return params


class SearchBackendBase(ABC):
    """Abstract base class for search backends."""

    def __init__(self):
        self.backend_name = "base"
        self.supported_types = [SearchType.WEB]

    @abstractmethod
    async def search(self, request: SearchRequest) -> SearchResponse:
        """Execute a search and return results."""
        pass

    @abstractmethod
    async def get_suggestions(self, query: str) -> List[str]:
        """Get search suggestions for a query."""
        pass

    def supports_type(self, search_type: SearchType) -> bool:
        """Check if this backend supports a search type."""
        return search_type in self.supported_types

    def build_url(self, request: SearchRequest) -> str:
        """Build the search URL."""
        return ""

    def _get_time_range(self, time_period: Optional[str]) -> str:
        """Convert time period to backend-specific format."""
        mapping = {
            "day": "d",
            "week": "w",
            "month": "m",
            "year": "y",
        }
        return mapping.get(time_period, "")

    def _get_safe_search_param(self, level: "SafeSearchLevel") -> str:  # type: ignore
        """Convert safe search level to backend parameter."""
        from atomic_search.config import SafeSearchLevel
        mapping = {
            SafeSearchLevel.OFF: "-2",
            SafeSearchLevel.MODERATE: "-1",
            SafeSearchLevel.STRICT: "1",
        }
        return mapping.get(level, "-1")


class SearchBackendManager:
    """Manager for search backends."""

    def __init__(self):
        self._backends: Dict[str, SearchBackendBase] = {}

    def register(self, backend_type, backend: SearchBackendBase) -> None:
        """Register a search backend."""
        # Handle both string and enum types
        if hasattr(backend_type, 'value'):
            self._backends[backend_type.value] = backend
        else:
            self._backends[str(backend_type)] = backend

    def get(self, backend_type) -> Optional[SearchBackendBase]:
        """Get a search backend by type."""
        # Handle both string and enum types
        if hasattr(backend_type, 'value'):
            return self._backends.get(backend_type.value)
        return self._backends.get(str(backend_type))

    def get_default(self) -> Optional[SearchBackendBase]:
        """Get the default search backend."""
        from atomic_search.config import config
        backend_name = config.SEARCH_BACKEND
        if hasattr(backend_name, 'value'):
            return self._backends.get(backend_name.value)
        return self._backends.get(str(backend_name))


# Global backend manager
backend_manager = SearchBackendManager()
