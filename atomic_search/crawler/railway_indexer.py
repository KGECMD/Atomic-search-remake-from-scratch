#!/usr/bin/env python3
"""
SuperNova Railway Crawler - 24/7 Auto Indexing
Pushes to GitHub .db branch
"""
import asyncio
import aiohttp
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
import sqlite3
import random
import os
import subprocess
from datetime import datetime

DB_PATH = os.environ.get("DATABASE_PATH", "supernova_index.db")

class SuperNovaCrawler:
    def __init__(self):
        self.visited = set()
        self.queue = asyncio.Queue()
        self.indexed = 0
        self.init_db()
        
    def init_db(self):
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("CREATE TABLE IF NOT EXISTS pages (url TEXT PRIMARY KEY, title TEXT, content TEXT, indexed_at TEXT, score INTEGER)")
        c.execute("CREATE TABLE IF NOT EXISTS stats (id INTEGER PRIMARY KEY, count INTEGER, updated TEXT)")
        conn.commit()
        conn.close()
        
    def save(self, url, title, content):
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO pages VALUES (?, ?, ?, ?, ?)",
            (url, title[:200], content[:5000], datetime.now().isoformat(), random.randint(1, 100)))
        conn.commit()
        conn.close()
        self.indexed += 1
        
    async def fetch(self, session, url):
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as r:
                if r.status == 200:
                    return await r.text()
        except:
            pass
        return None
        
    def get_links(self, html, base):
        soup = BeautifulSoup(html, "html.parser")
        links = []
        for a in soup.find_all("a", href=True):
            full = urljoin(base, a["href"])
            if urlparse(full).netloc and full not in self.visited:
                links.append(full)
        return links[:15]
        
    async def crawl(self, session, url):
        if url in self.visited: return []
        self.visited.add(url)
        
        html = await self.fetch(session, url)
        if not html: return []
        
        soup = BeautifulSoup(html, "html.parser")
        title = soup.title.string if soup.title else url
        text = " ".join([t.text for t in soup.find_all(["p","h1","h2","h3"])])
        
        self.save(url, title, text)
        if self.indexed % 50 == 0:
            print(f"Indexed: {self.indexed}")
        return self.get_links(html, url)
        
    async def worker(self, session):
        while True:
            url = await self.queue.get()
            try:
                for link in await self.crawl(session, url):
                    await self.queue.put(link)
            except:
                pass
            finally:
                self.queue.task_done()
                
    async def start(self, urls):
        for u in urls: await self.queue.put(u)
        async with aiohttp.ClientSession() as session:
            await asyncio.gather(*[self.worker(session) for _ in range(20)])
            
    def run(self):
        seeds = [
            "https://wikipedia.org", "https://github.com", "https://stackoverflow.com",
            "https://reddit.com", "https://medium.com", "https://dev.to",
            "https://news.ycombinator.com", "https://en.wikipedia.org",
        ]
        print(f"Starting SuperNova Crawler... DB: {DB_PATH}")
        asyncio.run(self.start(seeds))
        print(f"Done! Indexed {self.indexed} pages")
        
if __name__ == "__main__":
    SuperNovaCrawler().run()
