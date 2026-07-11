#!/usr/bin/env python3
"""
SuperNova Database Sync Script
Pushes indexed URLs to GitHub database-backup branch
"""
import os
import sqlite3
import subprocess
from datetime import datetime

DATABASE_PATH = os.environ.get("DATABASE_PATH", "data/supernova_index.db")

def export_urls():
    """Export all URLs from database to text file."""
    conn = sqlite3.connect(DATABASE_PATH)
    c = conn.cursor()
    c.execute("SELECT url, title, domain, indexed_at FROM pages ORDER BY indexed_at DESC")
    rows = c.fetchall()
    conn.close()
    
    with open("data/indexed_urls.txt", "w") as f:
        f.write(f"# SuperNova Indexed URLs - Exported {datetime.now().isoformat()}\n")
        f.write(f"# Total: {len(rows)} URLs\n\n")
        for url, title, domain, indexed_at in rows:
            f.write(f"{url}|{title}|{domain}|{indexed_at}\n")
    
    return len(rows)

def sync_to_github():
    """Sync database to GitHub."""
    print("Exporting URLs...")
    count = export_urls()
    print(f"Exported {count} URLs")
    
    # Copy db to data folder
    import shutil
    os.makedirs("data", exist_ok=True)
    shutil.copy(DATABASE_PATH, "data/supernova_index.db")
    
    # Git operations
    try:
        subprocess.run(["git", "checkout", "database-backup"], check=True, capture_output=True)
    except:
        subprocess.run(["git", "checkout", "-b", "database-backup"], check=True, capture_output=True)
    
    subprocess.run(["git", "add", "data/"], check=True)
    subprocess.run(["git", "commit", "-m", f"Auto-sync: {count} indexed URLs - {datetime.now().isoformat()}"], check=True, capture_output=True)
    
    try:
        subprocess.run(["git", "push", "origin", "database-backup"], check=True)
        print("Synced to GitHub!")
    except Exception as e:
        print(f"Push failed: {e}")
    
    subprocess.run(["git", "checkout", "master"], check=True)

if __name__ == "__main__":
    sync_to_github()
