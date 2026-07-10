"""
Voting service for Atomic Search community voting system.

Implements Reddit-style voting for search results:
- Upvote/downvote
- Anonymous voting
- Vote statistics
- Trending algorithms
- Abuse prevention
"""

import hashlib
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from atomic_search.config import config


@dataclass
class VoteInfo:
    """Vote information."""
    url: str
    title: Optional[str]
    snippet: Optional[str]
    votes: int
    upvotes: int
    downvotes: int
    trending_score: float


class VotingService:
    """Community voting service."""

    def __init__(self):
        # In-memory storage (would use database in production)
        self._votes: Dict[str, List[dict]] = {}
        self._vote_stats: Dict[str, VoteInfo] = {}
        self._user_votes: Dict[str, Dict[str, int]] = {}  # user_hash -> url -> vote_type
        self._daily_votes: Dict[str, int] = {}  # user_hash -> count
        self._cooldowns: Dict[str, float] = {}  # user_hash -> last_vote_time
        self._initialized = False

    def initialize(self) -> None:
        """Initialize the voting service."""
        if self._initialized:
            return

        # Load existing stats from database if available
        # For now, we'll use in-memory storage

        self._initialized = True

    def _get_user_key(self, ip_hash: str, session_id: str, user_id: Optional[str] = None) -> str:
        """Get a unique user key for voting."""
        if user_id:
            return hashlib.sha256(f"{user_id}".encode()).hexdigest()[:16]
        if session_id:
            return hashlib.sha256(f"{session_id}".encode()).hexdigest()[:16]
        return ip_hash[:16]

    def _get_url_key(self, url: str) -> str:
        """Get a normalized URL key."""
        return hashlib.sha256(url.encode()).hexdigest()

    def _check_cooldown(self, user_key: str) -> Tuple[bool, int]:
        """Check if user is in cooldown period.

        Returns:
            Tuple of (can_vote, seconds_remaining)
        """
        if user_key not in self._cooldowns:
            return True, 0

        elapsed = time.time() - self._cooldowns[user_key]
        cooldown = config.VOTING_COOLDOWN_MINUTES * 60

        if elapsed < cooldown:
            return False, int(cooldown - elapsed)

        return True, 0

    def _check_daily_limit(self, user_key: str) -> Tuple[bool, int]:
        """Check if user has exceeded daily vote limit.

        Returns:
            Tuple of (can_vote, votes_remaining)
        """
        today = datetime.utcnow().strftime("%Y-%m-%d")
        key = f"{user_key}:{today}"

        votes_today = self._daily_votes.get(key, 0)
        max_votes = config.MAX_VOTES_PER_DAY

        if votes_today >= max_votes:
            return False, 0

        return True, max_votes - votes_today

    def _update_stats(self, url: str) -> None:
        """Update vote statistics for a URL."""
        url_key = self._get_url_key(url)

        if url_key not in self._votes:
            return

        votes = self._votes[url_key]
        upvotes = sum(1 for v in votes if v["vote_type"] == 1)
        downvotes = sum(1 for v in votes if v["vote_type"] == -1)
        total_votes = upvotes - downvotes

        # Calculate trending score
        hours_age = (datetime.utcnow() - datetime.fromtimestamp(
            min(v["timestamp"] for v in votes)
        )).total_seconds() / 3600
        trending_score = total_votes / ((hours_age + 2) ** 1.5)

        # Get title/snippet from most recent vote
        latest = max(votes, key=lambda x: x["timestamp"])

        self._vote_stats[url_key] = VoteInfo(
            url=url,
            title=latest.get("result_title"),
            snippet=latest.get("result_snippet"),
            votes=total_votes,
            upvotes=upvotes,
            downvotes=downvotes,
            trending_score=trending_score,
        )

    def vote(
        self,
        url: str,
        vote_type: int,
        ip_hash: str,
        session_id: str,
        user_id: Optional[str] = None,
        result_title: Optional[str] = None,
        result_snippet: Optional[str] = None,
    ) -> Tuple[bool, str, Dict[str, int]]:
        """Record a vote.

        Args:
            url: The URL being voted on
            vote_type: 1 for upvote, -1 for downvote
            ip_hash: Hash of user IP
            session_id: User session ID
            user_id: Optional authenticated user ID
            result_title: Title of the result
            result_snippet: Snippet of the result

        Returns:
            Tuple of (success, message, updated_stats)
        """
        if not config.VOTING_ENABLED:
            return False, "Voting is disabled", {}

        self.initialize()

        # Validate vote type
        if vote_type not in (1, -1):
            return False, "Invalid vote type", {}

        # Normalize URL
        url = url.strip()
        if not url or len(url) > 2000:
            return False, "Invalid URL", {}

        user_key = self._get_user_key(ip_hash, session_id, user_id)
        url_key = self._get_url_key(url)

        # Check cooldown
        can_vote, remaining = self._check_cooldown(user_key)
        if not can_vote:
            return False, f"Please wait {remaining} seconds before voting again", {}

        # Check daily limit
        can_vote, remaining = self._check_daily_limit(user_key)
        if not can_vote:
            return False, "Daily vote limit reached", {}

        # Check if user already voted on this URL
        if user_key in self._user_votes:
            existing_vote = self._user_votes[user_key].get(url_key)
            if existing_vote is not None:
                if existing_vote == vote_type:
                    return False, "You have already voted on this result", self._get_stats(url)
                # Remove existing vote
                self._remove_vote(url_key, user_key, existing_vote)

        # Record new vote
        timestamp = time.time()
        vote = {
            "vote_type": vote_type,
            "ip_hash": ip_hash,
            "session_id": session_id if config.VOTING_ANONYMOUS else None,
            "user_id": user_id if not config.VOTING_ANONYMOUS else None,
            "timestamp": timestamp,
            "result_title": result_title,
            "result_snippet": result_snippet,
        }

        if url_key not in self._votes:
            self._votes[url_key] = []

        self._votes[url_key].append(vote)

        # Track user's vote
        if user_key not in self._user_votes:
            self._user_votes[user_key] = {}
        self._user_votes[user_key][url_key] = vote_type

        # Update daily count
        today = datetime.utcnow().strftime("%Y-%m-%d")
        daily_key = f"{user_key}:{today}"
        self._daily_votes[daily_key] = self._daily_votes.get(daily_key, 0) + 1

        # Update cooldown
        self._cooldowns[user_key] = timestamp

        # Update statistics
        self._update_stats(url)

        return True, "Vote recorded", self._get_stats(url)

    def _remove_vote(self, url_key: str, user_key: str, vote_type: int) -> None:
        """Remove a vote."""
        if url_key in self._votes:
            self._votes[url_key] = [
                v for v in self._votes[url_key]
                if not (v["vote_type"] == vote_type and (
                    v["ip_hash"] == user_key or
                    (v.get("session_id") == user_key and config.VOTING_ANONYMOUS)
                ))
            ]

    def _get_stats(self, url: str) -> Dict[str, int]:
        """Get vote statistics for a URL."""
        url_key = self._get_url_key(url)

        if url_key in self._vote_stats:
            stats = self._vote_stats[url_key]
            return {
                "votes": stats.votes,
                "upvotes": stats.upvotes,
                "downvotes": stats.downvotes,
            }

        if url_key in self._votes:
            votes = self._votes[url_key]
            upvotes = sum(1 for v in votes if v["vote_type"] == 1)
            downvotes = sum(1 for v in votes if v["vote_type"] == -1)
            return {
                "votes": upvotes - downvotes,
                "upvotes": upvotes,
                "downvotes": downvotes,
            }

        return {"votes": 0, "upvotes": 0, "downvotes": 0}

    def get_user_vote(
        self,
        url: str,
        ip_hash: str,
        session_id: str,
        user_id: Optional[str] = None,
    ) -> Optional[int]:
        """Get a user's vote on a URL."""
        user_key = self._get_user_key(ip_hash, session_id, user_id)
        url_key = self._get_url_key(url)

        if user_key in self._user_votes:
            return self._user_votes[user_key].get(url_key)

        return None

    def get_trending(self, limit: int = 20, region: Optional[str] = None) -> List[VoteInfo]:
        """Get trending search results."""
        self.initialize()

        stats = list(self._vote_stats.values())

        # Filter by region if specified
        # (would need region data in vote info)

        # Sort by trending score
        stats.sort(key=lambda x: x.trending_score, reverse=True)

        return stats[:limit]

    def get_top_results(self, limit: int = 20) -> List[VoteInfo]:
        """Get top voted results."""
        self.initialize()

        stats = list(self._vote_stats.values())
        stats.sort(key=lambda x: x.votes, reverse=True)

        return stats[:limit]

    def get_stats_for_urls(self, urls: List[str]) -> Dict[str, Dict[str, int]]:
        """Get vote statistics for multiple URLs."""
        return {url: self._get_stats(url) for url in urls}

    def get_vote_count(self, ip_hash: str, session_id: str) -> Dict[str, int]:
        """Get user's remaining vote quota."""
        user_key = self._get_user_key(ip_hash, session_id)

        today = datetime.utcnow().strftime("%Y-%m-%d")
        daily_key = f"{user_key}:{today}"
        votes_today = self._daily_votes.get(daily_key, 0)

        can_vote, remaining = self._check_daily_limit(user_key)

        return {
            "votes_today": votes_today,
            "votes_remaining": max(0, config.MAX_VOTES_PER_DAY - votes_today),
            "in_cooldown": not can_vote,
        }


# Global voting service instance
voting_service = VotingService()
