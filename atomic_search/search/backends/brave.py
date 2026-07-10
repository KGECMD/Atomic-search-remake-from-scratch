"""
Brave Search API integration.
"""

from typing import List, Optional
from dataclasses import dataclass
import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent

from atomic_search.config import config
from atomic_search.search.backends import SearchResult


ua = UserAgent()


@dataclass
class BraveSearchBackend:
    """Brave Search API backend."""
    
    name: str = "brave"
    display_name: str = "Brave Search"
    
    def __post_init__(self):
        self.api_key = getattr(config, 'BRAVE_API_KEY', None)
        self.base_url = "https://api.search.brave.com/res/v1/web/search"
    
    def search(
        self,
        query: str,
        page: int = 1,
        safe_search: bool = True,
        **kwargs
    ) -> List[SearchResult]:
        """Execute search using Brave Search API."""
        results = []
        
        headers = {
            "Accept": "application/json",
            "X-Subscription-Token": self.api_key or "",
            "User-Agent": ua.random,
        }
        
        params = {
            "q": query,
            "count": 10,
            "offset": (page - 1) * 10,
            "safesearch": "strict" if safe_search else "off",
        }
        
        try:
            response = requests.get(
                self.base_url,
                headers=headers,
                params=params,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                web_results = data.get("web", {}).get("results", [])
                
                for item in web_results:
                    results.append(SearchResult(
                        title=item.get("title", ""),
                        url=item.get("url", ""),
                        description=item.get("description", ""),
                        source=self.name,
                        thumbnail=item.get("thumbnail", {}).get("src"),
                    ))
        except Exception:
            pass
        
        return results
    
    def is_available(self) -> bool:
        """Check if Brave API is configured."""
        return bool(self.api_key)


brave_search = BraveSearchBackend()
