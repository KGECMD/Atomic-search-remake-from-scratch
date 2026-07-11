#!/usr/bin/env python3
"""
SuperNova Production Crawler - Real URL Indexing
Stores indexed URLs in SQLite database
"""
import asyncio
import aiohttp
import sqlite3
import os
import time
import random
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

DATABASE_PATH = os.environ.get("DATABASE_PATH", "supernova_index.db")
MAX_WORKERS = int(os.environ.get("MAX_WORKERS", "10"))
MAX_PAGES = int(os.environ.get("MAX_PAGES", "100000"))
SEED_FILE = os.environ.get("SEED_FILE", "atomic_search/crawler/seeds.txt")

def init_db():
    """Initialize database."""
    conn = sqlite3.connect(DATABASE_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS pages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT UNIQUE NOT NULL,
            title TEXT,
            description TEXT,
            content TEXT,
            domain TEXT,
            indexed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_crawled TIMESTAMP,
            crawl_count INTEGER DEFAULT 1,
            score REAL DEFAULT 1.0
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS domains (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            domain TEXT UNIQUE NOT NULL,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            page_count INTEGER DEFAULT 0
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS stats (
            id INTEGER PRIMARY KEY,
            total_pages INTEGER DEFAULT 0,
            total_domains INTEGER DEFAULT 0,
            last_update TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    c.execute("INSERT OR IGNORE INTO stats (id) VALUES (1)")
    conn.commit()
    conn.close()
    print(f"Database initialized: {DATABASE_PATH}")

def add_page(conn, url, title, description, content, domain):
    """Add page to database."""
    c = conn.cursor()
    c.execute("""
        INSERT OR REPLACE INTO pages (url, title, description, content, domain, last_crawled, crawl_count)
        VALUES (?, ?, ?, ?, ?, ?, COALESCE((SELECT crawl_count FROM pages WHERE url = ?), 0) + 1)
    """, (url, title, description, content[:2000], domain, datetime.now().isoformat(), url))
    c.execute("UPDATE stats SET total_pages = (SELECT COUNT(*) FROM pages), total_domains = (SELECT COUNT(*) FROM domains), last_update = ? WHERE id = 1", (datetime.now().isoformat(),))
    conn.commit()

def add_domain(conn, domain):
    """Track domain."""
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO domains (domain) VALUES (?)", (domain,))
    c.execute("UPDATE domains SET page_count = (SELECT COUNT(*) FROM pages WHERE domain = ?), last_crawl = ? WHERE domain = ?", (domain, datetime.now().isoformat(), domain))
    conn.commit()

def get_stats(conn):
    """Get stats."""
    c = conn.cursor()
    c.execute("SELECT * FROM stats WHERE id = 1")
    row = c.fetchone()
    return {"total_pages": row[1] if row else 0, "total_domains": row[2] if row else 0}

class SuperNovaCrawler:
    def __init__(self):
        self.visited = set()
        self.queue = asyncio.Queue()
        self.indexed = 0
        self.session = None
        self.db_path = DATABASE_PATH
        
    async def fetch(self, url):
        """Fetch a page."""
        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; SuperNovaBot/1.0; +https://supernova.search)",
            "Accept": "text/html,application/xhtml+xml",
        }
        try:
            async with self.session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                if resp.status == 200:
                    return await resp.text()
        except:
            pass
        return None
    
    def parse(self, html, base_url):
        """Parse HTML and extract links."""
        soup = BeautifulSoup(html, "html.parser")
        
        # Get title
        title = soup.title.string if soup.title else ""
        
        # Get description
        desc_tag = soup.find("meta", attrs={"name": "description"})
        description = desc_tag["content"] if desc_tag else ""
        
        # Get content
        text_tags = soup.find_all(["p", "h1", "h2", "h3", "h4", "li"])
        content = " ".join([t.get_text() for t in text_tags[:50]])
        
        # Extract links
        links = []
        for a in soup.find_all("a", href=True):
            try:
                full_url = urljoin(base_url, a["href"])
                parsed = urlparse(full_url)
                if parsed.netloc and parsed.scheme in ["http", "https"]:
                    if full_url not in self.visited:
                        links.append(full_url)
            except:
                pass
        
        return title[:200], description[:500], content[:2000], links[:30]
    
    async def crawl(self, url):
        """Crawl a single URL."""
        if url in self.visited:
            return []
        self.visited.add(url)
        
        html = await self.fetch(url)
        if not html:
            return []
        
        parsed = urlparse(url)
        domain = parsed.netloc
        
        try:
            title, desc, content, links = self.parse(html, url)
        except:
            return []
        
        # Save to database
        conn = sqlite3.connect(self.db_path)
        try:
            add_page(conn, url, title, desc, content, domain)
            add_domain(conn, domain)
        finally:
            conn.close()
        
        self.indexed += 1
        if self.indexed % 10 == 0:
            print(f"Indexed: {self.indexed}")
        
        return links
    
    async def worker(self):
        """Worker coroutine."""
        while True:
            url = await self.queue.get()
            try:
                if self.indexed >= MAX_PAGES:
                    break
                links = await self.crawl(url)
                for link in links:
                    await self.queue.put(link)
            except Exception as e:
                pass
            finally:
                self.queue.task_done()
    
    async def start(self, seeds):
        """Start crawling."""
        for url in seeds:
            await self.queue.put(url)
        
        connector = aiohttp.TCPConnector(limit=MAX_WORKERS * 2)
        async with aiohttp.ClientSession(connector=connector) as session:
            self.session = session
            tasks = [asyncio.create_task(self.worker()) for _ in range(MAX_WORKERS)]
            await self.queue.join()
            for t in tasks:
                t.cancel()

def load_seeds():
    """Load seed URLs."""
    seeds = []
    if os.path.exists(SEED_FILE):
        with open(SEED_FILE) as f:
            seeds = [line.strip() for line in f if line.strip()]
    if not seeds:
        # Default seeds
        seeds = [
            "https://github.com", "https://stackoverflow.com", "https://reddit.com",
            "https://wikipedia.org", "https://medium.com", "https://dev.to",
            "https://news.ycombinator.com", "https://arxiv.org",
        ]
    return seeds

def run_crawler():
    """Run the crawler."""
    init_db()
    
    seeds = load_seeds()
    print(f"Starting SuperNova Crawler with {len(seeds)} seeds...")
    print(f"Target: {MAX_PAGES} pages")
    print(f"Workers: {MAX_WORKERS}")
    
    crawler = SuperNovaCrawler()
    asyncio.run(crawler.start(seeds))
    
    # Print final stats
    conn = sqlite3.connect(DATABASE_PATH)
    stats = get_stats(conn)
    conn.close()
    
    print(f"\n✅ Crawling complete!")
    print(f"Indexed: {stats['total_pages']} pages")
    print(f"Domains: {stats['total_domains']} domains")

if __name__ == "__main__":
    run_crawler()
