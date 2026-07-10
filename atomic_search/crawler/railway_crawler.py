#!/usr/bin/env python3
"""
SuperNova Railway Crawler - Auto Indexing Script
Run this on Railway for 24/7 web indexing
"""
import asyncio
import aiohttp
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
import sqlite3
import random
import os
from datetime import datetime

DATABASE_PATH = os.environ.get("DATABASE_PATH", "supernova_index.db")

class RailwayCrawler:
    def __init__(self):
        self.visited = set()
        self.queue = asyncio.Queue()
        self.indexed_count = 0
        self.db_path = DATABASE_PATH
        self.init_db()
        
    def init_db(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("CREATE TABLE IF NOT EXISTS indexed_pages (url TEXT PRIMARY KEY, title TEXT, content TEXT, indexed_at TIMESTAMP, score INTEGER)")
        c.execute("CREATE TABLE IF NOT EXISTS crawl_stats (id INTEGER PRIMARY KEY, pages_crawled INTEGER, last_crawl TIMESTAMP)")
        conn.commit()
        conn.close()
        
    def save_to_db(self, url, title, content):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO indexed_pages (url, title, content, indexed_at, score) VALUES (?, ?, ?, ?, ?)",
            (url, title[:200], content[:5000], datetime.now().isoformat(), random.randint(1, 100)))
        conn.commit()
        conn.close()
        
    async def fetch_page(self, session, url):
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 200:
                    return await response.text()
        except:
            pass
        return None
        
    def extract_links(self, html, base_url):
        soup = BeautifulSoup(html, "html.parser")
        links = []
        for a in soup.find_all("a", href=True):
            href = a["href"]
            full_url = urljoin(base_url, href)
            parsed = urlparse(full_url)
            if parsed.netloc and full_url not in self.visited:
                links.append(full_url)
        return links[:20]
        
    async def crawl_page(self, session, url):
        if url in self.visited:
            return []
        self.visited.add(url)
        
        html = await self.fetch_page(session, url)
        if not html:
            return []
            
        soup = BeautifulSoup(html, "html.parser")
        title = soup.title.string if soup.title else url
        text = " ".join([t.text for t in soup.find_all(["p", "h1", "h2", "h3", "li"])])
        
        self.save_to_db(url, title, text)
        self.indexed_count += 1
        
        if self.indexed_count % 100 == 0:
            print(f"Indexed {self.indexed_count} pages...")
            
        return self.extract_links(html, url)
        
    async def worker(self, session):
        while True:
            url = await self.queue.get()
            try:
                links = await self.crawl_page(session, url)
                for link in links:
                    await self.queue.put(link)
            except:
                pass
            finally:
                self.queue.task_done()
                
    async def start_crawl(self, start_urls, workers=10):
        for url in start_urls:
            await self.queue.put(url)
            
        async with aiohttp.ClientSession() as session:
            tasks = [asyncio.create_task(self.worker(session)) for _ in range(workers)]
            await self.queue.join()
            
    def run(self):
        start_urls = [
            "https://wikipedia.org", "https://github.com", "https://stackoverflow.com",
            "https://reddit.com", "https://news.ycombinator.com", "https://medium.com",
            "https://dev.to", "https://news.google.com", "https://en.wikipedia.org", "https://arxiv.org",
        ]
        
        print("SuperNova Railway Crawler Starting...")
        print(f"Database: {self.db_path}")
        print("Starting indexing 100k+ web pages...")
        
        asyncio.run(self.start_crawl(start_urls))
        print(f"Indexed {self.indexed_count} pages!")

if __name__ == "__main__":
    RailwayCrawler().run()
