"""
SuperNova Search - Main Entry Point

Run with: python -m atomic_search.main
         or: gunicorn 'atomic_search.main:app' ...
"""

import os
import sys

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from atomic_search.app import create_app
from atomic_search.config import config

# Create the app instance for gunicorn
app = create_app()


def main():
    """Run the SuperNova Search application."""
    # Get host and port from config
    host = config.HOST
    port = config.PORT
    debug = config.DEBUG

    print("""
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║     ⭐ SuperNova Search - Privacy-First Search Engine        ║
║                                                              ║
║     Version: 1.0.0                                           ║
║     Mode: Production                                         ║
║                                                              ║
║     Running at: http://{0}:{1}                              ║
║                                                              ║
║     🔒 Zero Telemetry | 🔐 Privacy First                     ║
║                                                              ║
║     Press Ctrl+C to stop                                     ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
    """.format(host, port))

    app.run(
        host=host,
        port=port,
        debug=debug,
        threaded=True
    )


if __name__ == "__main__":
    main()
