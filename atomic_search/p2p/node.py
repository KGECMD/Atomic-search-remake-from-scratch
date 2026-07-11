"""
P2P Node for Atomic Search.

A decentralized node that contributes to the search network.
Each node can:
- Share search results with other nodes
- Cache results from other nodes
- Participate in distributed search
- Contribute to the collective search index
"""

import asyncio
import hashlib
import json
import logging
import random
import sqlite3
import threading
import time
import uuid
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set
from urllib.parse import urlparse

import requests

logger = logging.getLogger(__name__)


@dataclass
class NodeInfo:
    """Information about a P2P node."""
    node_id: str
    name: str
    host: str
    port: int
    version: str
    capabilities: List[str]
    score: float
    last_seen: datetime
    is_trusted: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "name": self.name,
            "host": self.host,
            "port": self.port,
            "version": self.version,
            "capabilities": self.capabilities,
            "score": self.score,
            "last_seen": self.last_seen.isoformat() if isinstance(self.last_seen, datetime) else self.last_seen,
            "is_trusted": self.is_trusted,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "NodeInfo":
        last_seen = data.get("last_seen")
        if isinstance(last_seen, str):
            last_seen = datetime.fromisoformat(last_seen)
        elif not isinstance(last_seen, datetime):
            last_seen = datetime.now()
        return cls(
            node_id=data["node_id"],
            name=data["name"],
            host=data["host"],
            port=data["port"],
            version=data["version"],
            capabilities=data.get("capabilities", []),
            score=data.get("score", 1.0),
            last_seen=last_seen,
            is_trusted=data.get("is_trusted", False),
        )


@dataclass
class SharedResult:
    """A search result shared by a node."""
    result_id: str
    query_hash: str
    url: str
    title: str
    snippet: str
    score: float
    source_node: str
    shared_at: datetime
    expires_at: datetime
    request_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "result_id": self.result_id,
            "query_hash": self.query_hash,
            "url": self.url,
            "title": self.title,
            "snippet": self.snippet,
            "score": self.score,
            "source_node": self.source_node,
            "shared_at": self.shared_at.isoformat() if isinstance(self.shared_at, datetime) else self.shared_at,
            "expires_at": self.expires_at.isoformat() if isinstance(self.expires_at, datetime) else self.expires_at,
            "request_count": self.request_count,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SharedResult":
        return cls(
            result_id=data["result_id"],
            query_hash=data["query_hash"],
            url=data["url"],
            title=data.get("title", ""),
            snippet=data.get("snippet", ""),
            score=data.get("score", 0.0),
            source_node=data["source_node"],
            shared_at=datetime.fromisoformat(data["shared_at"]) if isinstance(data["shared_at"], str) else datetime.now(),
            expires_at=datetime.fromisoformat(data["expires_at"]) if isinstance(data["expires_at"], str) else datetime.now() + timedelta(hours=24),
            request_count=data.get("request_count", 0),
        )


class P2PNode:
    """P2P Node for distributed search."""
    
    VERSION = "1.0.0"
    CAPABILITIES = ["search", "crawl", "cache", "vote", "ai"]
    
    def __init__(
        self,
        name: str = "AtomicNode",
        host: str = "0.0.0.0",
        port: int = 8765,
        db_path: str = "/tmp/atomic_search_p2p.db",
        bootstrap_nodes: List[str] = None,
        max_connections: int = 50,
        cache_ttl: int = 3600,
    ):
        self.node_id = str(uuid.uuid4())[:8]
        self.name = name
        self.host = host
        self.port = port
        self.db_path = db_path
        self.bootstrap_nodes = bootstrap_nodes or []
        self.max_connections = max_connections
        self.cache_ttl = cache_ttl
        
        self._lock = threading.Lock()
        self._running = False
        self._nodes: Dict[str, NodeInfo] = {}
        self._pending_requests: Set[str] = set()
        
        self._init_db()
    
    def _init_db(self):
        """Initialize the P2P database."""
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Known nodes table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS nodes (
                    node_id TEXT PRIMARY KEY,
                    name TEXT,
                    host TEXT,
                    port INTEGER,
                    version TEXT,
                    capabilities TEXT,
                    score REAL DEFAULT 1.0,
                    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_trusted INTEGER DEFAULT 0
                )
            """)
            
            # Shared results cache
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS shared_results (
                    result_id TEXT PRIMARY KEY,
                    query_hash TEXT,
                    url TEXT,
                    title TEXT,
                    snippet TEXT,
                    score REAL,
                    source_node TEXT,
                    shared_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP,
                    request_count INTEGER DEFAULT 0
                )
            """)
            
            # Query cache for P2P results
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS p2p_cache (
                    query_hash TEXT PRIMARY KEY,
                    results_json TEXT,
                    node_id TEXT,
                    cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP
                )
            """)
            
            # Network stats
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS network_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    node_id TEXT,
                    action TEXT,
                    success INTEGER,
                    latency_ms REAL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_query_hash ON shared_results(query_hash)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_expires ON shared_results(expires_at)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_p2p_cache_expires ON p2p_cache(expires_at)")
            
            conn.commit()
            conn.close()
    
    def get_node_info(self) -> NodeInfo:
        """Get this node's information."""
        return NodeInfo(
            node_id=self.node_id,
            name=self.name,
            host=self.host,
            port=self.port,
            version=self.VERSION,
            capabilities=self.CAPABILITIES,
            score=1.0,
            last_seen=datetime.now(),
            is_trusted=True,
        )
    
    def register_node(self, node_info: NodeInfo) -> bool:
        """Register a new node."""
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            try:
                cursor.execute("""
                    INSERT OR REPLACE INTO nodes 
                    (node_id, name, host, port, version, capabilities, score, last_seen, is_trusted)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    node_info.node_id,
                    node_info.name,
                    node_info.host,
                    node_info.port,
                    node_info.version,
                    json.dumps(node_info.capabilities),
                    node_info.score,
                    datetime.now().isoformat(),
                    1 if node_info.is_trusted else 0,
                ))
                conn.commit()
                self._nodes[node_info.node_id] = node_info
                return True
            except Exception as e:
                logger.error(f"Error registering node: {e}")
                return False
            finally:
                conn.close()
    
    def get_active_nodes(self) -> List[NodeInfo]:
        """Get list of active nodes."""
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT node_id, name, host, port, version, capabilities, score, last_seen, is_trusted
                FROM nodes
                WHERE last_seen > datetime('now', '-1 hour')
                ORDER BY score DESC
                LIMIT ?
            """, (self.max_connections,))
            
            rows = cursor.fetchall()
            conn.close()
            
            nodes = []
            for row in rows:
                nodes.append(NodeInfo(
                    node_id=row[0],
                    name=row[1],
                    host=row[2],
                    port=row[3],
                    version=row[4],
                    capabilities=json.loads(row[5]) if row[5] else [],
                    score=row[6],
                    last_seen=datetime.fromisoformat(row[7]) if row[7] else datetime.now(),
                    is_trusted=bool(row[8]),
                ))
            
            return nodes
    
    def share_result(self, query: str, result: Dict[str, Any], ttl: int = 86400) -> bool:
        """Share a search result with the network."""
        query_hash = hashlib.sha256(query.lower().strip().encode()).hexdigest()[:16]
        result_id = hashlib.sha256(f"{query_hash}:{result.get('url', '')}".encode()).hexdigest()[:16]
        
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            try:
                cursor.execute("""
                    INSERT OR REPLACE INTO shared_results
                    (result_id, query_hash, url, title, snippet, score, source_node, expires_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now', '+' || ? || ' seconds'))
                """, (
                    result_id,
                    query_hash,
                    result.get("url", ""),
                    result.get("title", ""),
                    result.get("snippet", ""),
                    result.get("score", 0.0),
                    self.node_id,
                    ttl,
                ))
                conn.commit()
                return True
            except Exception as e:
                logger.error(f"Error sharing result: {e}")
                return False
            finally:
                conn.close()
    
    def get_shared_results(self, query: str, limit: int = 10) -> List[SharedResult]:
        """Get shared results for a query from cache."""
        query_hash = hashlib.sha256(query.lower().strip().encode()).hexdigest()[:16]
        
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT result_id, query_hash, url, title, snippet, score, source_node, 
                       shared_at, expires_at, request_count
                FROM shared_results
                WHERE query_hash = ? AND expires_at > datetime('now')
                ORDER BY score DESC
                LIMIT ?
            """, (query_hash, limit))
            
            rows = cursor.fetchall()
            
            # Update request count
            cursor.execute("""
                UPDATE shared_results SET request_count = request_count + 1
                WHERE query_hash = ? AND expires_at > datetime('now')
            """, (query_hash,))
            
            conn.commit()
            conn.close()
            
            return [
                SharedResult(
                    result_id=row[0],
                    query_hash=row[1],
                    url=row[2],
                    title=row[3],
                    snippet=row[4],
                    score=row[5],
                    source_node=row[6],
                    shared_at=datetime.fromisoformat(row[7]) if row[7] else datetime.now(),
                    expires_at=datetime.fromisoformat(row[8]) if row[8] else datetime.now(),
                    request_count=row[9],
                )
                for row in rows
            ]
    
    def cache_p2p_results(self, query: str, results: List[Dict], ttl: int = None) -> bool:
        """Cache P2P results for a query."""
        ttl = ttl or self.cache_ttl
        query_hash = hashlib.sha256(query.lower().strip().encode()).hexdigest()[:32]
        
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            try:
                cursor.execute("""
                    INSERT OR REPLACE INTO p2p_cache
                    (query_hash, results_json, node_id, expires_at)
                    VALUES (?, ?, ?, datetime('now', '+' || ? || ' seconds'))
                """, (query_hash, json.dumps(results), self.node_id, ttl))
                conn.commit()
                return True
            except Exception as e:
                logger.error(f"Error caching P2P results: {e}")
                return False
            finally:
                conn.close()
    
    def get_cached_p2p_results(self, query: str) -> Optional[List[Dict]]:
        """Get cached P2P results for a query."""
        query_hash = hashlib.sha256(query.lower().strip().encode()).hexdigest()[:32]
        
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT results_json FROM p2p_cache
                WHERE query_hash = ? AND expires_at > datetime('now')
            """, (query_hash,))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return json.loads(row[0])
        return None
    
    async def discover_nodes(self, bootstrap_urls: List[str] = None) -> int:
        """Discover new nodes from bootstrap nodes."""
        bootstrap_urls = bootstrap_urls or self.bootstrap_nodes
        discovered = 0
        
        for url in bootstrap_urls:
            try:
                response = requests.get(
                    f"{url}/api/v1/nodes",
                    timeout=5,
                    headers={"User-Agent": f"AtomicSearch/{self.VERSION}"}
                )
                if response.status_code == 200:
                    data = response.json()
                    for node_data in data.get("nodes", []):
                        node = NodeInfo.from_dict(node_data)
                        if node.node_id != self.node_id:
                            self.register_node(node)
                            discovered += 1
            except Exception as e:
                logger.debug(f"Error discovering nodes from {url}: {e}")
        
        return discovered
    
    def request_search_from_network(self, query: str, timeout: int = 5) -> Optional[List[Dict]]:
        """Request search results from connected nodes."""
        # Check local cache first
        cached = self.get_cached_p2p_results(query)
        if cached:
            return cached
        
        # Get active nodes
        nodes = self.get_active_nodes()
        if not nodes:
            return None
        
        # Shuffle for load balancing
        random.shuffle(nodes)
        
        # Try up to 5 nodes
        for node in nodes[:5]:
            request_id = str(uuid.uuid4())
            if request_id in self._pending_requests:
                continue
            
            self._pending_requests.add(request_id)
            
            try:
                response = requests.post(
                    f"http://{node.host}:{node.port}/api/v1/search",
                    json={"query": query, "request_id": request_id},
                    timeout=timeout,
                    headers={"User-Agent": f"AtomicSearch/{self.VERSION}"}
                )
                
                if response.status_code == 200:
                    results = response.json().get("results", [])
                    self.cache_p2p_results(query, results)
                    return results
            except Exception as e:
                logger.debug(f"Error requesting search from {node.node_id}: {e}")
            finally:
                self._pending_requests.discard(request_id)
        
        return None
    
    def update_node_score(self, node_id: str, delta: float):
        """Update a node's score based on performance."""
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE nodes SET score = MAX(0.1, score + ?) WHERE node_id = ?
            """, (delta, node_id))
            
            conn.commit()
            conn.close()
    
    def cleanup_expired(self) -> int:
        """Clean up expired entries."""
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("DELETE FROM shared_results WHERE expires_at < datetime('now')")
            deleted_shared = cursor.rowcount
            
            cursor.execute("DELETE FROM p2p_cache WHERE expires_at < datetime('now')")
            deleted_cache = cursor.rowcount
            
            cursor.execute("DELETE FROM nodes WHERE last_seen < datetime('now', '-7 days')")
            deleted_nodes = cursor.rowcount
            
            conn.commit()
            conn.close()
            
            return deleted_shared + deleted_cache + deleted_nodes
    
    def get_network_stats(self) -> Dict[str, Any]:
        """Get network statistics."""
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            stats = {}
            
            cursor.execute("SELECT COUNT(*) FROM nodes WHERE last_seen > datetime('now', '-1 hour')")
            stats["active_nodes"] = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM shared_results WHERE expires_at > datetime('now')")
            stats["shared_results"] = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM p2p_cache WHERE expires_at > datetime('now')")
            stats["cached_queries"] = cursor.fetchone()[0]
            
            cursor.execute("SELECT AVG(latency_ms) FROM network_stats WHERE timestamp > datetime('now', '-1 hour')")
            avg_latency = cursor.fetchone()[0]
            stats["avg_latency_ms"] = round(avg_latency, 2) if avg_latency else 0
            
            cursor.execute("""
                SELECT source_node, COUNT(*) as cnt 
                FROM shared_results 
                GROUP BY source_node 
                ORDER BY cnt DESC 
                LIMIT 5
            """)
            stats["top_contributors"] = [{"node": r[0], "count": r[1]} for r in cursor.fetchall()]
            
            conn.close()
            
            return stats
    
    def start(self):
        """Start the P2P node."""
        self._running = True
        logger.info(f"P2P Node {self.node_id} started on {self.host}:{self.port}")
    
    def stop(self):
        """Stop the P2P node."""
        self._running = False
        logger.info(f"P2P Node {self.node_id} stopped")
    
    def is_running(self) -> bool:
        """Check if node is running."""
        return self._running


# Global P2P node instance
p2p_node = P2PNode()
