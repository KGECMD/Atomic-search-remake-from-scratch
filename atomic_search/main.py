"""
Atomic Search - Main Entry Point

Run with: python -m atomic_search.main
"""

import asyncio
import os
import sys

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from atomic_search.app import create_app
from atomic_search.config import config


def main():
    """Run the Atomic Search application."""
    app = create_app()
    
    # Get host and port from config
    host = config.HOST
    port = config.PORT
    debug = config.DEBUG
    
    print(f"""
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║     🔬 Atomic Search - Privacy-First Search Engine            ║
║                                                              ║
║     Version: {config.APP_VERSION:<44}║
║     Mode: {'Production' if not debug else 'Development':<44}║
║                                                              ║
║     Running at: http://{host}:{port}                        ║
║                                                              ║
║     Press Ctrl+C to stop                                     ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
    """)
    
    app.run(
        host=host,
        port=port,
        debug=debug,
        threaded=True
    )


if __name__ == "__main__":
    main()
