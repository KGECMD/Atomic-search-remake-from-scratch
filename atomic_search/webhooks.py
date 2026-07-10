"""
Webhooks for Atomic Search.

Provides webhook notifications for events.
"""

import hashlib
import hmac
import json
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
from urllib.parse import urlparse

import httpx


class WebhookEvent(Enum):
    """Webhook event types."""
    SEARCH = "search"
    VOTE = "vote"
    BOOKMARK = "bookmark"
    ERROR = "error"
    USER_SIGNUP = "user.signup"
    USER_LOGIN = "user.login"
    ADMIN_ACTION = "admin.action"
    SYSTEM_ERROR = "system.error"
    RATE_LIMIT = "rate.limit"


@dataclass
class Webhook:
    """Webhook configuration."""
    id: str
    url: str
    secret: str
    events: List[WebhookEvent] = field(default_factory=list)
    enabled: bool = True
    created_at: float = field(default_factory=time.time)
    last_triggered: Optional[float] = None
    failure_count: int = 0


class WebhookManager:
    """Manages webhook subscriptions and deliveries."""

    def __init__(self):
        self._webhooks: Dict[str, Webhook] = {}
        self._lock = threading.RLock()
        self._queue: List[Dict] = []
        self._worker_thread: Optional[threading.Thread] = None
        self._running = False

    def add_webhook(
        self,
        url: str,
        secret: str,
        events: List[WebhookEvent],
        webhook_id: Optional[str] = None
    ) -> str:
        """Add a webhook."""
        with self._lock:
            webhook_id = webhook_id or hashlib.sha256(
                f"{url}{time.time()}".encode()
            ).hexdigest()[:16]

            self._webhooks[webhook_id] = Webhook(
                id=webhook_id,
                url=url,
                secret=secret,
                events=events
            )

            return webhook_id

    def remove_webhook(self, webhook_id: str) -> bool:
        """Remove a webhook."""
        with self._lock:
            if webhook_id in self._webhooks:
                del self._webhooks[webhook_id]
                return True
            return False

    def get_webhook(self, webhook_id: str) -> Optional[Webhook]:
        """Get webhook by ID."""
        return self._webhooks.get(webhook_id)

    def list_webhooks(self) -> List[Webhook]:
        """List all webhooks."""
        return list(self._webhooks.values())

    def trigger(self, event: WebhookEvent, data: Dict[str, Any]) -> int:
        """Trigger webhooks for an event."""
        triggered = 0

        with self._lock:
            webhooks = [
                w for w in self._webhooks.values()
                if w.enabled and event in w.events
            ]

        for webhook in webhooks:
            payload = {
                "event": event.value,
                "timestamp": time.time(),
                "data": data
            }

            self._queue.append({
                "webhook_id": webhook.id,
                "url": webhook.url,
                "secret": webhook.secret,
                "payload": payload
            })

            webhook.last_triggered = time.time()
            triggered += 1

        self._ensure_worker()

        return triggered

    def _ensure_worker(self):
        """Ensure worker thread is running."""
        if not self._running:
            self._running = True
            self._worker_thread = threading.Thread(
                target=self._worker,
                daemon=True
            )
            self._worker_thread.start()

    def _worker(self):
        """Process webhook queue."""
        while self._running:
            if self._queue:
                item = self._queue.pop(0)
                self._deliver(item)
            else:
                time.sleep(0.1)

    def _deliver(self, item: Dict):
        """Deliver webhook payload."""
        try:
            payload_bytes = json.dumps(item["payload"]).encode()
            signature = hmac.new(
                item["secret"].encode(),
                payload_bytes,
                hashlib.sha256
            ).hexdigest()

            response = httpx.post(
                item["url"],
                content=payload_bytes,
                headers={
                    "Content-Type": "application/json",
                    "X-Webhook-Signature": signature,
                    "X-Webhook-Event": item["payload"]["event"],
                    "User-Agent": "AtomicSearch-Webhook/1.0"
                },
                timeout=10.0
            )

            if response.status_code >= 400:
                self._record_failure(item["webhook_id"])

        except Exception:
            self._record_failure(item["webhook_id"])

    def _record_failure(self, webhook_id: str):
        """Record webhook delivery failure."""
        with self._lock:
            webhook = self._webhooks.get(webhook_id)
            if webhook:
                webhook.failure_count += 1
                if webhook.failure_count >= 5:
                    webhook.enabled = False

    def stop(self):
        """Stop the webhook worker."""
        self._running = False

    def get_stats(self) -> Dict:
        """Get webhook statistics."""
        with self._lock:
            total = len(self._webhooks)
            enabled = sum(1 for w in self._webhooks.values() if w.enabled)
            queue_size = len(self._queue)

            return {
                "total_webhooks": total,
                "enabled_webhooks": enabled,
                "queue_size": queue_size,
                "running": self._running
            }


# Global webhook manager
webhook_manager = WebhookManager()
