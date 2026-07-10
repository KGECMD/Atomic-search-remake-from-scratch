"""
CLI commands for Atomic Search.

Provides command-line interface for management.
"""

import argparse
import sys
from typing import List, Optional


class CLI:
    """Command-line interface."""

    COMMANDS = {}

    @classmethod
    def command(cls, name: str, help_text: str = ""):
        """Decorator to register a command."""
        def decorator(func):
            cls.COMMANDS[name] = {
                "func": func,
                "help": help_text
            }
            return func
        return decorator

    @classmethod
    def run(cls, args: List[str] = None):
        """Run CLI with arguments."""
        if args is None:
            args = sys.argv[1:]

        if not args:
            cls.print_help()
            return

        command_name = args[0]
        command_args = args[1:]

        if command_name == "help":
            cls.print_help()
            return

        command = cls.COMMANDS.get(command_name)
        if command:
            command["func"](command_args)
        else:
            print(f"Unknown command: {command_name}")
            cls.print_help()

    @classmethod
    def print_help(cls):
        """Print help message."""
        print("Atomic Search CLI")
        print("\nCommands:")
        for name, cmd in cls.COMMANDS.items():
            print(f"  {name:15} {cmd['help']}")


@CLI.command("start", "Start the search server")
def cmd_start(args):
    """Start the search server."""
    from atomic_search.app import create_app
    app = create_app()
    app.run(host="0.0.0.0", port=5000, debug=False)


@CLI.command("dev", "Start in development mode")
def cmd_dev(args):
    """Start in development mode."""
    from atomic_search.app import create_app
    app = create_app()
    app.run(host="0.0.0.0", port=5000, debug=True)


@CLI.command("init", "Initialize the database")
def cmd_init(args):
    """Initialize the database."""
    from atomic_search.search.indexer import SearchIndexer
    indexer = SearchIndexer()
    print("Database initialized!")


@CLI.command("clean", "Clean old cache and logs")
def cmd_clean(args):
    """Clean old cache and logs."""
    from atomic_search.search.indexer import SearchIndexer
    
    indexer = SearchIndexer()
    result = indexer.cleanup_old_entries(30)
    print(f"Cleaned: {result}")


@CLI.command("stats", "Show statistics")
def cmd_stats(args):
    """Show search statistics."""
    from atomic_search.search.indexer import SearchIndexer
    
    indexer = SearchIndexer()
    stats = indexer.get_stats()
    
    print("Atomic Search Statistics:")
    print(f"  Total Results: {stats.get('total_results', 0)}")
    print(f"  Tracked Queries: {stats.get('tracked_queries', 0)}")
    print(f"  Total Votes: {stats.get('total_votes', 0)}")
    print(f"  Bookmarks: {stats.get('total_bookmarks', 0)}")
    print(f"  Collections: {stats.get('total_collections', 0)}")


@CLI.command("test", "Run tests")
def cmd_test(args):
    """Run tests."""
    import subprocess
    result = subprocess.run(
        ["python", "-m", "pytest", "tests/", "-v"],
        cwd="/workspace/project"
    )
    sys.exit(result.returncode)


@CLI.command("lint", "Run linter")
def cmd_lint(args):
    """Run linter."""
    import subprocess
    result = subprocess.run(
        ["python", "-m", "flake8", "atomic_search/"],
        cwd="/workspace/project"
    )
    sys.exit(result.returncode)


@CLI.command("format", "Format code")
def cmd_format(args):
    """Format code."""
    import subprocess
    result = subprocess.run(
        ["python", "-m", "black", "atomic_search/"],
        cwd="/workspace/project"
    )
    print("Code formatted!")


@CLI.command("gen-key", "Generate secret key")
def cmd_gen_key(args):
    """Generate a secret key."""
    import secrets
    key = secrets.token_hex(32)
    print(f"SECRET_KEY={key}")


@CLI.command("version", "Show version")
def cmd_version(args):
    """Show version."""
    from atomic_search.config import config
    print(f"Atomic Search v{config.APP_VERSION}")


@CLI.command("crawl", "Crawl URLs for indexing")
def cmd_crawl(args):
    """Crawl URLs and index them."""
    import asyncio
    import shlex
    from atomic_search.crawler.web_crawler import WebCrawler
    
    # Parse arguments manually
    max_pages = 100
    max_depth = 2
    delay = 1.0
    urls = []
    
    for arg in args:
        if arg.startswith("--max-pages="):
            max_pages = int(arg.split("=")[1])
        elif arg.startswith("--max-depth="):
            max_depth = int(arg.split("=")[1])
        elif arg.startswith("--delay="):
            delay = float(arg.split("=")[1])
        elif arg.startswith("http"):
            urls.append(arg)
    
    if not urls:
        urls = ["https://example.com"]
    
    async def run_crawl():
        crawler = WebCrawler(
            max_pages=max_pages,
            max_depth=max_depth,
            delay=delay,
        )
        
        print(f"Starting crawl of {len(urls)} URL(s)...")
        print(f"Max pages: {max_pages}, Max depth: {max_depth}")
        
        try:
            result = await crawler.crawl(urls)
            print(f"\nCrawl completed!")
            print(f"  Pages crawled: {result['crawled']}")
            print(f"  URLs queued: {result.get('queued', 0)}")
        except Exception as e:
            print(f"Crawl error: {e}")
        finally:
            await crawler.close()
    
    asyncio.run(run_crawl())


@CLI.command("crawl-stats", "Show crawler statistics")
def cmd_crawl_stats(args):
    """Show crawler statistics."""
    from atomic_search.crawler.web_crawler import web_crawler
    
    stats = web_crawler.get_stats()
    print("Crawler Statistics:")
    print(f"  Total pages: {stats.get('total_pages', 0)}")
    print(f"  Indexed words: {stats.get('indexed_words', 0)}")


@CLI.command("search-index", "Search the crawl index")
def cmd_search_index(args):
    """Search the crawl index."""
    import asyncio
    from atomic_search.crawler.web_crawler import web_crawler
    
    if not args:
        print("Usage: atomic-search search-index <query>")
        return
    
    query = " ".join(args)
    results = web_crawler.search_index(query)
    
    if not results:
        print(f"No results found for '{query}'")
        return
    
    print(f"Found {len(results)} result(s) for '{query}':\n")
    for i, result in enumerate(results, 1):
        print(f"{i}. {result['title']}")
        print(f"   {result['url']}")
        if result.get('description'):
            print(f"   {result['description'][:100]}...")
        print()


@CLI.command("export-data", "Export user data")
def cmd_export(args):
    """Export user data."""
    import json
    from atomic_search.search.indexer import SearchIndexer
    
    indexer = SearchIndexer()
    
    data = {
        "bookmarks": indexer.get_bookmarks(args[0] if args else "anonymous"),
        "collections": indexer.get_collections(args[0] if args else "anonymous"),
        "trending": indexer.get_trending(100)
    }
    
    print(json.dumps(data, indent=2))


def main():
    """Main entry point."""
    CLI.run()


if __name__ == "__main__":
    main()
