"""
Web Crawler for Atomic Search.

A privacy-focused web crawler that indexes pages for search.
"""

import asyncio
import hashlib
import logging
import re
import sqlite3
import threading
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Set
from urllib.parse import urljoin, urlparse
import ssl

import aiohttp
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class WebCrawler:
    """Privacy-focused web crawler for Atomic Search."""
    
    def __init__(
        self,
        db_path: str = "/tmp/atomic_search_crawl.db",
        max_depth: int = 3,
        max_pages: int = 1000,
        delay: float = 1.0,
        user_agent: str = None,
        timeout: int = 30,
    ):
        self.db_path = db_path
        self.max_depth = max_depth
        self.max_pages = max_pages
        self.delay = delay
        self.timeout = timeout
        self.user_agent = user_agent or (
            "AtomicSearch/1.0 (Privacy-First Search Engine)"
        )
        
        self._lock = threading.Lock()
        self._crawled_urls: Set[str] = set()
        self._session: Optional[aiohttp.ClientSession] = None
        self._running = False
        
        self._init_db()
    
    def _init_db(self):
        """Initialize the crawler database."""
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Crawled pages table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS pages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT NOT NULL UNIQUE,
                    url_hash TEXT NOT NULL UNIQUE,
                    title TEXT,
                    content TEXT,
                    meta_description TEXT,
                    headings TEXT,
                    language TEXT,
                    status_code INTEGER,
                    crawled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_updated TIMESTAMP,
                    crawl_depth INTEGER DEFAULT 0
                )
            """)
            
            # URLs to crawl table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS url_queue (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT NOT NULL UNIQUE,
                    url_hash TEXT NOT NULL UNIQUE,
                    depth INTEGER DEFAULT 0,
                    discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'pending'
                )
            """)
            
            # Index for full-text search
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS page_content (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    page_id INTEGER NOT NULL,
                    word TEXT NOT NULL,
                    frequency INTEGER DEFAULT 1,
                    FOREIGN KEY (page_id) REFERENCES pages(id) ON DELETE CASCADE
                )
            """)
            
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_word ON page_content(word)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_url_hash ON pages(url_hash)")
            
            conn.commit()
            conn.close()
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self._session is None or self._session.closed:
            connector = aiohttp.TCPConnector(limit_per_host=5, limit=10)
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            self._session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                headers={"User-Agent": self.user_agent},
            )
        return self._session
    
    def _is_valid_url(self, url: str) -> bool:
        """Check if URL is valid for crawling."""
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return False
        if not parsed.netloc:
            return False
        # Skip non-content files
        skip_patterns = [r"\.pdf$", r"\.zip$", r"\.mp3$", r"\.mp4$", r"javascript:", r"mailto:"]
        for pattern in skip_patterns:
            if re.search(pattern, url.lower()):
                return False
        return True
    
    def _extract_links(self, html: str, base_url: str) -> List[str]:
        """Extract links from HTML."""
        links = []
        soup = BeautifulSoup(html, "html.parser")
        for a in soup.find_all("a", href=True):
            href = a["href"]
            full_url = urljoin(base_url, href)
            if "#" in full_url:
                full_url = full_url.split("#")[0]
            if self._is_valid_url(full_url):
                links.append(full_url)
        return list(set(links))[:50]
    
    def _extract_metadata(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract metadata from page."""
        metadata = {"title": "", "meta_description": "", "headings": [], "language": "en"}
        
        title_tag = soup.find("title")
        if title_tag:
            metadata["title"] = title_tag.get_text().strip()[:200]
        
        desc_tag = soup.find("meta", attrs={"name": "description"})
        if desc_tag and desc_tag.get("content"):
            metadata["meta_description"] = desc_tag["content"].strip()[:500]
        
        html_tag = soup.find("html")
        if html_tag:
            lang = html_tag.get("lang")
            if lang:
                metadata["language"] = lang[:2]
        
        for i in range(1, 4):
            for h in soup.find_all(f"h{i}"):
                text = h.get_text().strip()
                if text:
                    metadata["headings"].append(text[:100])
        
        return metadata
    
    def _extract_text(self, soup: BeautifulSoup) -> str:
        """Extract main text content."""
        for tag in soup.find_all(["script", "style", "nav", "header", "footer"]):
            tag.decompose()
        text = soup.get_text(separator=" ", strip=True)
        text = re.sub(r"\s+", " ", text)
        return text[:30000]
    
    def _tokenize(self, text: str) -> List[tuple]:
        """Tokenize text and return word-frequency pairs."""
        words = re.findall(r"\b[a-zA-Z0-9]+\b", text.lower())
        stop_words = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
                      "of", "with", "by", "from", "as", "is", "was", "are", "this", "that"}
        word_freq = {}
        for word in words:
            if len(word) > 2 and word not in stop_words:
                word_freq[word] = word_freq.get(word, 0) + 1
        return [(word, freq) for word, freq in word_freq.items()]
    
    async def _crawl_page(self, url: str, depth: int = 0) -> Optional[Dict[str, Any]]:
        """Crawl a single page."""
        url_hash = hashlib.sha256(url.encode()).hexdigest()[:32]
        
        try:
            session = await self._get_session()
            async with session.get(url) as response:
                if response.status != 200:
                    return None
                
                content_type = response.headers.get("Content-Type", "")
                if "text/html" not in content_type:
                    return None
                
                html = await response.text()
                soup = BeautifulSoup(html, "html.parser")
                
                metadata = self._extract_metadata(soup)
                text = self._extract_text(soup)
                links = self._extract_links(html, url)
                tokens = self._tokenize(text)
                
                return {
                    "url": url,
                    "url_hash": url_hash,
                    "status_code": response.status,
                    "content": text,
                    **metadata,
                    "links": links,
                    "tokens": tokens,
                    "depth": depth,
                }
                
        except Exception as e:
            logger.debug(f"Error crawling {url}: {e}")
            return None
    
    def _save_page(self, page_data: Dict[str, Any]):
        """Save crawled page to database."""
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            try:
                cursor.execute("""
                    INSERT OR REPLACE INTO pages 
                    (url, url_hash, title, content, meta_description, headings,
                     language, status_code, crawl_depth, last_updated)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, (
                    page_data["url"],
                    page_data["url_hash"],
                    page_data.get("title", ""),
                    page_data.get("content", ""),
                    page_data.get("meta_description", ""),
                    ",".join(page_data.get("headings", [])[:5]),
                    page_data.get("language", "en"),
                    page_data.get("status_code"),
                    page_data.get("depth", 0),
                ))
                
                page_id = cursor.lastrowid
                cursor.execute("DELETE FROM page_content WHERE page_id = ?", (page_id,))
                for word, freq in page_data.get("tokens", [])[:500]:
                    cursor.execute("""
                        INSERT INTO page_content (page_id, word, frequency)
                        VALUES (?, ?, ?)
                    """, (page_id, word, freq))
                
                conn.commit()
            except Exception as e:
                logger.error(f"Error saving page: {e}")
                conn.rollback()
            finally:
                conn.close()
    
    def _add_to_queue(self, urls: List[str], depth: int):
        """Add URLs to crawl queue."""
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            for url in urls:
                url_hash = hashlib.sha256(url.encode()).hexdigest()[:32]
                try:
                    cursor.execute("""
                        INSERT OR IGNORE INTO url_queue (url, url_hash, depth)
                        VALUES (?, ?, ?)
                    """, (url, url_hash, depth))
                except Exception:
                    pass
            conn.commit()
            conn.close()
    
    async def crawl(
        self,
        start_urls: List[str],
        max_pages: int = None,
        max_depth: int = None,
    ) -> Dict[str, Any]:
        """Crawl pages starting from seed URLs."""
        max_pages = max_pages or self.max_pages
        max_depth = max_depth or self.max_depth
        
        self._running = True
        stats = {"crawled": 0, "queued": 0, "start_time": datetime.now().isoformat()}
        
        for url in start_urls:
            if self._is_valid_url(url):
                self._add_to_queue([url], depth=0)
        
        while stats["crawled"] < max_pages and self._running:
            with self._lock:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, url, depth FROM url_queue
                    WHERE status = 'pending' AND depth <= ?
                    ORDER BY depth ASC LIMIT 5
                """, (max_depth,))
                queue_items = cursor.fetchall()
                conn.close()
            
            if not queue_items:
                break
            
            for queue_id, url, depth in queue_items:
                if stats["crawled"] >= max_pages:
                    break
                if url in self._crawled_urls:
                    continue
                
                self._crawled_urls.add(url)
                
                page_data = await self._crawl_page(url, depth)
                
                with self._lock:
                    conn = sqlite3.connect(self.db_path)
                    cursor = conn.cursor()
                    if page_data:
                        self._save_page(page_data)
                        if depth < max_depth:
                            self._add_to_queue(page_data.get("links", []), depth + 1)
                        cursor.execute("UPDATE url_queue SET status = 'completed' WHERE id = ?", (queue_id,))
                        stats["crawled"] += 1
                    else:
                        cursor.execute("UPDATE url_queue SET status = 'failed' WHERE id = ?", (queue_id,))
                    conn.commit()
                    conn.close()
                
                await asyncio.sleep(self.delay)
        
        stats["end_time"] = datetime.now().isoformat()
        return stats
    
    def search_index(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search the crawled pages."""
        query_words = [w.lower() for w in re.findall(r"\b\w+\b", query) if len(w) > 2]
        if not query_words:
            return []
        
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            placeholders = ",".join(["?" for _ in query_words])
            cursor.execute(f"""
                SELECT p.url, p.title, p.meta_description,
                       SUM(pc.frequency) as relevance
                FROM pages p
                JOIN page_content pc ON p.id = pc.page_id
                WHERE pc.word IN ({placeholders})
                GROUP BY p.id
                ORDER BY relevance DESC
                LIMIT ?
            """, (*query_words, limit))
            
            rows = cursor.fetchall()
            conn.close()
            
            return [{"url": r[0], "title": r[1] or "", "description": r[2] or "", "relevance": r[3]} for r in rows]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get crawler statistics."""
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            stats = {}
            cursor.execute("SELECT COUNT(*) FROM pages")
            stats["total_pages"] = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM page_content")
            stats["indexed_words"] = cursor.fetchone()[0]
            conn.close()
            return stats
    
    def stop(self):
        """Stop the crawler."""
        self._running = False
    
    async def close(self):
        """Close resources."""
        if self._session and not self._session.closed:
            await self._session.close()


# Global crawler instance
web_crawler = WebCrawler()
