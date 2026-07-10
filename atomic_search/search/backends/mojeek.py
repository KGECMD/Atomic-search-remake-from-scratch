"""
Mojeek Search integration - independent search engine with no tracking.
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
class MojeekSearchBackend:
    """Mojeek Search backend - independent, ethical search engine."""
    
    name: str = "mojeek"
    display_name: str = "Mojeek"
    
    def __post_init__(self):
        self.base_url = "https://www.mojeek.com/search"
    
    def search(
        self,
        query: str,
        page: int = 1,
        safe_search: bool = True,
        **kwargs
    ) -> List[SearchResult]:
        """Execute search using Mojeek."""
        results = []
        
        headers = {
            "User-Agent": ua.random,
            "Accept": "text/html",
        }
        
        params = {
            "q": query,
            "pg": page,
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
                result_cards = soup.select(".result, .results li")
                
                for card in result_cards[:10]:
                    title_elem = card.select_one("h2 a, .title a, a.title")
                    desc_elem = card.select_one(".t, .desc, .description, .snippet")
                    link_elem = card.select_one("a")
                    
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


mojeek_search = MojeekSearchBackend()
