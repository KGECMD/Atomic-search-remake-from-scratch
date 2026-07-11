"""SuperNova Index Database Module."""
import sqlite3
import os
from datetime import datetime
from contextlib import contextmanager

DATABASE_PATH = os.environ.get("DATABASE_PATH", "supernova_index.db")

def get_db():
    """Get database connection."""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

@contextmanager
def get_db_cursor():
    """Context manager for database operations."""
    conn = get_db()
    try:
        cursor = conn.cursor()
        yield cursor
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def init_db():
    """Initialize the database schema."""
    with get_db_cursor() as c:
        # Pages table
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
                score REAL DEFAULT 1.0,
                status TEXT DEFAULT 'pending'
            )
        """)
        
        # Domains table
        c.execute("""
            CREATE TABLE IF NOT EXISTS domains (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                domain TEXT UNIQUE NOT NULL,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                page_count INTEGER DEFAULT 0,
                last_crawl TIMESTAMP,
                priority INTEGER DEFAULT 1
            )
        """)
        
        # Crawl queue
        c.execute("""
            CREATE TABLE IF NOT EXISTS crawl_queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT UNIQUE NOT NULL,
                priority INTEGER DEFAULT 1,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'pending'
            )
        """)
        
        # Stats
        c.execute("""
            CREATE TABLE IF NOT EXISTS stats (
                id INTEGER PRIMARY KEY,
                total_pages INTEGER DEFAULT 0,
                total_domains INTEGER DEFAULT 0,
                last_update TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Insert initial stats
        c.execute("INSERT OR IGNORE INTO stats (id, total_pages) VALUES (1, 0)")
        
        # Indexes
        c.execute("CREATE INDEX IF NOT EXISTS idx_url ON pages(url)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_domain ON pages(domain)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_crawl_queue ON crawl_queue(priority DESC, added_at)")
        
    print(f"Database initialized at {DATABASE_PATH}")

def add_page(url, title="", description="", content="", domain=""):
    """Add a page to the index."""
    if not domain:
        from urllib.parse import urlparse
        domain = urlparse(url).netloc
    
    with get_db_cursor() as c:
        c.execute("""
            INSERT OR REPLACE INTO pages (url, title, description, content, domain, last_crawled, crawl_count)
            VALUES (?, ?, ?, ?, ?, ?, COALESCE((SELECT crawl_count FROM pages WHERE url = ?), 0) + 1)
        """, (url, title, description, content, domain, datetime.now().isoformat(), url))
        
        c.execute("UPDATE stats SET total_pages = (SELECT COUNT(*) FROM pages), last_update = ? WHERE id = 1", (datetime.now().isoformat(),))
    
    return True

def add_to_queue(url, priority=1):
    """Add URL to crawl queue."""
    with get_db_cursor() as c:
        c.execute("INSERT OR IGNORE INTO crawl_queue (url, priority) VALUES (?, ?)", (url, priority))

def get_queue_item():
    """Get next item from crawl queue."""
    with get_db_cursor() as c:
        c.execute("SELECT * FROM crawl_queue WHERE status = 'pending' ORDER BY priority DESC, added_at LIMIT 1")
        row = c.fetchone()
        if row:
            c.execute("UPDATE crawl_queue SET status = 'processing' WHERE id = ?", (row["id"],))
        return dict(row) if row else None

def mark_processed(url, status="completed"):
    """Mark URL as processed."""
    with get_db_cursor() as c:
        c.execute("UPDATE crawl_queue SET status = ? WHERE url = ?", (status, url))

def get_stats():
    """Get indexing statistics."""
    with get_db_cursor() as c:
        c.execute("SELECT * FROM stats WHERE id = 1")
        row = c.fetchone()
        return dict(row) if row else {"total_pages": 0, "total_domains": 0}

def get_all_pages(limit=1000, offset=0):
    """Get all indexed pages."""
    with get_db_cursor() as c:
        c.execute("SELECT * FROM pages ORDER BY indexed_at DESC LIMIT ? OFFSET ?", (limit, offset))
        return [dict(row) for row in c.fetchall()]

def search_pages(query, limit=50):
    """Search indexed pages."""
    with get_db_cursor() as c:
        c.execute("""
            SELECT * FROM pages 
            WHERE url LIKE ? OR title LIKE ? OR content LIKE ?
            ORDER BY score DESC
            LIMIT ?
        """, (f"%{query}%", f"%{query}%", f"%{query}%", limit))
        return [dict(row) for row in c.fetchall()]

if __name__ == "__main__":
    init_db()
    print(f"Initialized database: {DATABASE_PATH}")
