"""
Swisscows Search integration - privacy-focused European search engine.
"""

from typing import List
from dataclasses import dataclass
import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent

from atomic_search.config import config
from atomic_search.search.backends import SearchResult


ua = UserAgent()


@dataclass
class SwisscowsSearchBackend:
    """Swisscows Search backend - private European search engine."""
    
    name: str = "swisscows"
    display_name: str = "Swisscows"
    
    def __post_init__(self):
        self.base_url = "https://swisscows.com/search"
    
    def search(
        self,
        query: str,
        page: int = 1,
        safe_search: bool = True,
        **kwargs
    ) -> List[SearchResult]:
        """Execute search using Swisscows."""
        results = []
        
        headers = {
            "User-Agent": ua.random,
            "Accept": "text/html",
        }
        
        params = {
            "query": query,
            "page": page,
            "safeSearch": "1" if safe_search else "0",
        }
        
        try:
            response = requests.get(
                self.base_url,
                headers=headers,
                params=params,
                timeout=10
            )
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, "lxml")
                
                # Find result items
                result_items = soup.select(".result-item, .web-results li, .results .result")
                
                for item in result_items[:10]:
                    title_elem = item.select_one("h3 a, .title a, a.title")
                    desc_elem = item.select_one(".description, .snippet, .result-description")
                    link_elem = item.select_one("a")
                    
                    if title_elem and link_elem:
                        url = link_elem.get("href", "")
                        
                        results.append(SearchResult(
                            title=title_elem.get_text(strip=True),
                            url=url,
                            description=desc_elem.get_text(strip=True) if desc_elem else "",
                            source=self.name,
                        ))
        except Exception:
            pass
        
        return results
    
    def is_available(self) -> bool:
        """Always available."""
        return True


swisscows_search = SwisscowsSearchBackend()
