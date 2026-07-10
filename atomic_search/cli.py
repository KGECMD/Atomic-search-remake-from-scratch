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

        parser = argparse.ArgumentParser(
            description="Atomic Search CLI",
            prog="atomic-search"
        )

        parser.add_argument(
            "command",
            choices=list(cls.COMMANDS.keys()) + ["help"],
            help="Command to run"
        )

        parser.add_argument(
            "args",
            nargs="*",
            help="Arguments for command"
        )

        parsed = parser.parse_args(args)

        if parsed.command == "help":
            cls.print_help()
            return

        command = cls.COMMANDS.get(parsed.command)
        if command:
            command["func"](parsed.args)

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
    print(f"Atomic Search v{config.version}")


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
