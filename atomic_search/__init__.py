"""
Atomic Search - A privacy-focused search engine.

A modern, privacy-first search engine inspired by Whoogle, featuring:
- Zero telemetry and tracking
- AI-powered search summaries
- Community voting system
- Modern responsive UI with dark/light modes
- Advanced security features
- Plugin and theme support
"""

__version__ = "1.0.0"
__author__ = "Atomic Search Team"
__license__ = "MIT"

from atomic_search.app import create_app
from atomic_search.config import config, Config

__all__ = ["create_app", "Config", "config", "__version__"]


def main():
    """Main entry point for the application."""
    app = create_app()
    app.run(host=config.HOST, port=config.PORT, debug=config.DEBUG)


if __name__ == "__main__":
    main()
