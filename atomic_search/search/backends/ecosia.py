"""
Ecosia Search integration - privacy-friendly search engine that plants trees.
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
class EcosiaSearchBackend:
    """Ecosia Search backend - eco-friendly privacy search."""
    
    name: str = "ecosia"
    display_name: str = "Ecosia"
    
    def __post_init__(self):
        self.base_url = "https://www.ecosia.org/search"
    
    def search(
        self,
        query: str,
        page: int = 1,
        safe_search: bool = True,
        **kwargs
    ) -> List[SearchResult]:
        """Execute search using Ecosia."""
        results = []
        
        headers = {
            "User-Agent": ua.random,
            "Accept": "text/html",
        }
        
        params = {
            "q": query,
            "page": page,
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
                
                # Find result cards
                result_cards = soup.select(".result-card")
                if not result_cards:
                    result_cards = soup.select(".result")
                
                for card in result_cards[:10]:
                    title_elem = card.select_one(".result-title, .js-result-title, h2 a, a.title")
                    desc_elem = card.select_one(".result-snippet, .js-result-snippet, .snippet, p")
                    link_elem = card.select_one("a")
                    
                    if title_elem and link_elem:
                        url = link_elem.get("href", "")
                        if url and not url.startswith("http"):
                            url = "https://www.ecosia.org" + url
                        
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


ecosia_search = EcosiaSearchBackend()
