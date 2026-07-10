"""
Atomic Search Database Models.

SQLAlchemy models for:
- Search history
- Votes
- Bookmarks
- Collections
- Sessions
- Admin users
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    JSON,
    UniqueConstraint,
)
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker

from atomic_search.config import config

Base = declarative_base()


class SearchHistory(Base):
    """User search history model."""

    __tablename__ = "search_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    query = Column(String(500), nullable=False, index=True)
    search_type = Column(String(50), default="web")
    region = Column(String(10), default="global")
    language = Column(String(10), default="en")
    safe_search = Column(String(20), default="moderate")
    result_count = Column(Integer, default=0)
    ip_hash = Column(String(64), index=True)
    user_agent = Column(String(500))
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

    __table_args__ = (
        Index("idx_search_timestamp", "timestamp"),
        Index("idx_search_query_timestamp", "query", "timestamp"),
    )

    def __repr__(self) -> str:
        return f"<SearchHistory(id={self.id}, query='{self.query}')>"


class Vote(Base):
    """Community voting model for search results."""

    __tablename__ = "votes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    result_url = Column(String(2000), nullable=False, index=True)
    result_title = Column(String(1000))
    result_snippet = Column(Text)
    vote_type = Column(Integer, nullable=False)  # 1 = upvote, -1 = downvote
    ip_hash = Column(String(64), index=True)
    session_id = Column(String(64), index=True)
    user_id = Column(String(64), index=True, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

    __table_args__ = (
        UniqueConstraint("result_url", "ip_hash", name="uq_vote_url_ip"),
        UniqueConstraint("result_url", "session_id", name="uq_vote_url_session"),
        Index("idx_vote_timestamp", "timestamp"),
    )

    def __repr__(self) -> str:
        vote_str = "upvote" if self.vote_type == 1 else "downvote"
        return f"<Vote(id={self.id}, type={vote_str})>"


class VoteStats(Base):
    """Aggregated vote statistics for search results."""

    __tablename__ = "vote_stats"

    id = Column(Integer, primary_key=True, autoincrement=True)
    result_url = Column(String(2000), nullable=False, unique=True, index=True)
    result_title = Column(String(1000))
    upvotes = Column(Integer, default=0)
    downvotes = Column(Integer, default=0)
    score = Column(Integer, default=0)
    trending_score = Column(Float, default=0.0)
    first_seen = Column(DateTime, default=datetime.utcnow)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def update_score(self) -> None:
        """Update the aggregated score."""
        self.score = self.upvotes - self.downvotes
        # Trending score based on time-decay formula
        hours_age = (datetime.utcnow() - self.first_seen).total_seconds() / 3600
        self.trending_score = self.score / ((hours_age + 2) ** 1.5)
        self.last_updated = datetime.utcnow()

    def __repr__(self) -> str:
        return f"<VoteStats(url='{self.result_url[:50]}...', score={self.score})>"


class Bookmark(Base):
    """User bookmarks for search results."""

    __tablename__ = "bookmarks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(64), nullable=False, index=True)
    result_url = Column(String(2000), nullable=False)
    result_title = Column(String(1000), nullable=False)
    result_snippet = Column(Text)
    result_thumbnail = Column(String(500))
    result_source = Column(String(100))
    tags = Column(JSON, default=list)
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("session_id", "result_url", name="uq_bookmark_session_url"),
        Index("idx_bookmark_session", "session_id"),
    )

    def __repr__(self) -> str:
        return f"<Bookmark(id={self.id}, title='{self.result_title[:30]}...')>"


class Collection(Base):
    """User-created search result collections."""

    __tablename__ = "collections"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(64), nullable=False, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    is_public = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    bookmarks = relationship("CollectionBookmark", back_populates="collection", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Collection(id={self.id}, name='{self.name}')>"


class CollectionBookmark(Base):
    """Bookmark within a collection."""

    __tablename__ = "collection_bookmarks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    collection_id = Column(Integer, ForeignKey("collections.id", ondelete="CASCADE"), nullable=False)
    bookmark_id = Column(Integer, ForeignKey("bookmarks.id", ondelete="CASCADE"), nullable=False)
    position = Column(Integer, default=0)
    added_at = Column(DateTime, default=datetime.utcnow)

    collection = relationship("Collection", back_populates="bookmarks")
    bookmark = relationship("Bookmark")

    def __repr__(self) -> str:
        return f"<CollectionBookmark(collection_id={self.collection_id}, bookmark_id={self.bookmark_id})>"


class AdminUser(Base):
    """Admin user model."""

    __tablename__ = "admin_users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    password_hash = Column(String(256), nullable=False)
    email = Column(String(255), unique=True, nullable=True)
    role = Column(String(50), default="admin")
    two_factor_enabled = Column(Boolean, default=False)
    two_factor_secret = Column(String(64), nullable=True)
    is_active = Column(Boolean, default=True)
    last_login = Column(DateTime)
    login_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<AdminUser(id={self.id}, username='{self.username}')>"


class Session(Base):
    """User session model."""

    __tablename__ = "sessions"

    id = Column(String(64), primary_key=True)
    session_id = Column(String(64), unique=True, nullable=False, index=True)
    data = Column(JSON, default=dict)
    ip_hash = Column(String(64))
    user_agent = Column(String(500))
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False, index=True)
    is_active = Column(Boolean, default=True)

    __table_args__ = (
        Index("idx_session_expires", "expires_at"),
    )

    def __repr__(self) -> str:
        return f"<Session(id='{self.session_id[:8]}...')>"


class Plugin(Base):
    """Plugin configuration model."""

    __tablename__ = "plugins"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False)
    version = Column(String(20))
    description = Column(Text)
    author = Column(String(200))
    config = Column(JSON, default=dict)
    is_enabled = Column(Boolean, default=False)
    is_builtin = Column(Boolean, default=False)
    settings = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<Plugin(name='{self.name}', enabled={self.is_enabled})>"


class Theme(Base):
    """Theme configuration model."""

    __tablename__ = "themes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False)
    version = Column(String(20))
    author = Column(String(200))
    config = Column(JSON, default=dict)
    is_active = Column(Boolean, default=False)
    is_builtin = Column(Boolean, default=False)
    custom_css = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<Theme(name='{self.name}', active={self.is_active})>"


class AISession(Base):
    """AI chat session model."""

    __tablename__ = "ai_sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(64), nullable=False, index=True)
    conversation_id = Column(String(64), unique=True, nullable=False)
    messages = Column(JSON, default=list)
    context = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_message_at = Column(DateTime)
    message_count = Column(Integer, default=0)

    def __repr__(self) -> str:
        return f"<AISession(id={self.id}, conversation='{self.conversation_id[:8]}...')>"


class TrendingSearch(Base):
    """Trending search queries model."""

    __tablename__ = "trending_searches"

    id = Column(Integer, primary_key=True, autoincrement=True)
    query = Column(String(500), nullable=False, index=True)
    query_hash = Column(String(64), unique=True, nullable=False)
    search_count = Column(Integer, default=0)
    score = Column(Float, default=0.0)
    region = Column(String(10), default="global")
    category = Column(String(100))
    first_seen = Column(DateTime, default=datetime.utcnow)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("idx_trending_score", "score"),
        Index("idx_trending_region", "region", "score"),
    )

    def update_score(self) -> None:
        """Update trending score."""
        hours_age = (datetime.utcnow() - self.first_seen).total_seconds() / 3600
        self.score = self.search_count / ((hours_age + 2) ** 1.2)
        self.last_updated = datetime.utcnow()

    def __repr__(self) -> str:
        return f"<TrendingSearch(query='{self.query}', score={self.score})>"


class AuditLog(Base):
    """Security audit log model."""

    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_type = Column(String(100), nullable=False, index=True)
    severity = Column(String(20), default="info")
    message = Column(Text)
    ip_hash = Column(String(64))
    user_id = Column(String(64))
    session_id = Column(String(64))
    endpoint = Column(String(500))
    method = Column(String(10))
    status_code = Column(Integer)
    details = Column(JSON)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

    __table_args__ = (
        Index("idx_audit_timestamp", "timestamp"),
        Index("idx_audit_severity", "severity", "timestamp"),
    )

    def __repr__(self) -> str:
        return f"<AuditLog(id={self.id}, type='{self.event_type}', severity='{self.severity}')>"


# Database engine and session management
engine = None
async_session_maker = None


def get_database_url() -> str:
    """Get the database URL from configuration."""
    url = config.DATABASE_URL
    # Convert sync URL to async URL for aiosqlite
    if url.startswith("sqlite:///"):
        url = url.replace("sqlite:///", "sqlite+aiosqlite:///")
    return url


async def init_db() -> None:
    """Initialize the database."""
    global engine, async_session_maker

    engine = create_async_engine(
        get_database_url(),
        echo=config.DATABASE_ECHO,
        pool_pre_ping=True,
        pool_recycle=3600,
    )

    async_session_maker = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db() -> AsyncSession:
    """Get a database session."""
    if async_session_maker is None:
        await init_db()
    async with async_session_maker() as session:
        yield session


# SQLAlchemy db instance for Flask-SQLAlchemy compatibility
# Using direct SQLAlchemy for async operations
db = None


async def init_flask_db(app) -> None:
    """Initialize database for Flask application."""
    pass  # Database initialization handled by async_session_maker
