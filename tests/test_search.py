"""
Tests for search functionality.
"""

import pytest
from atomic_search.search.backends.multi import MultiSearchBackend


class TestSearchBackends:
    """Test search backends."""

    def test_multi_backend_initialization(self):
        """Test multi backend initializes."""
        backend = MultiSearchBackend()
        assert backend is not None
        assert hasattr(backend, 'engines')

    def test_multi_backend_search(self):
        """Test multi backend search."""
        backend = MultiSearchBackend()
        results = backend.search("python")
        assert isinstance(results, list)
        # May be empty if network unavailable

    def test_query_validation(self):
        """Test query validation."""
        backend = MultiSearchBackend()
        # Empty query should return empty
        results = backend.search("")
        assert results == []


class TestSearchIndex:
    """Test search indexer."""

    def test_indexer_initialization(self):
        """Test indexer initializes."""
        from atomic_search.search.indexer import SearchIndexer
        indexer = SearchIndexer(db_path=":memory:")
        assert indexer is not None

    def test_track_search(self):
        """Test tracking searches."""
        from atomic_search.search.indexer import SearchIndexer
        indexer = SearchIndexer(db_path=":memory:")
        indexer.track_search("test query")
        trending = indexer.get_trending(limit=5)
        assert isinstance(trending, list)

    def test_get_stats(self):
        """Test getting stats."""
        from atomic_search.search.indexer import SearchIndexer
        indexer = SearchIndexer(db_path=":memory:")
        stats = indexer.get_stats()
        assert isinstance(stats, dict)
        assert "total_results" in stats


class TestValidators:
    """Test input validators."""

    def test_validate_query(self):
        """Test query validation."""
        from atomic_search.utils.validators import validator
        
        result = validator.validate_query("test query")
        assert result.valid is True
        
        result = validator.validate_query("")
        assert result.valid is False

    def test_validate_url(self):
        """Test URL validation."""
        from atomic_search.utils.validators import validator
        
        result = validator.validate_url("https://example.com")
        assert result.valid is True
        
        result = validator.validate_url("not-a-url")
        assert result.valid is False

    def test_validate_email(self):
        """Test email validation."""
        from atomic_search.utils.validators import validator
        
        result = validator.validate_email("test@example.com")
        assert result.valid is True
        
        result = validator.validate_email("invalid")
        assert result.valid is False


class TestPrivacy:
    """Test privacy utilities."""

    def test_is_tracker(self):
        """Test tracker detection."""
        from atomic_search.utils.privacy import privacy_manager
        
        assert privacy_manager.is_tracker("https://google-analytics.com/script.js")
        assert not privacy_manager.is_tracker("https://example.com/page")

    def test_sanitize_url(self):
        """Test URL sanitization."""
        from atomic_search.utils.privacy import privacy_manager
        
        url = "https://example.com/page?utm_source=test&fbclid=123"
        sanitized = privacy_manager.sanitize_url(url)
        assert "utm_source" not in sanitized
        assert "fbclid" not in sanitized


class TestCrypto:
    """Test encryption utilities."""

    def test_hash_password(self):
        """Test password hashing."""
        from atomic_search.utils.encryption import crypto
        
        hashed, salt = crypto.hash_password("testpassword")
        assert hashed is not None
        assert salt is not None

    def test_verify_password(self):
        """Test password verification."""
        from atomic_search.utils.encryption import crypto
        
        hashed, salt = crypto.hash_password("testpassword")
        assert crypto.verify_password("testpassword", hashed, salt)
        assert not crypto.verify_password("wrongpassword", hashed, salt)


class TestCache:
    """Test caching utilities."""

    def test_lru_cache(self):
        """Test LRU cache."""
        from atomic_search.utils.cache import LRUCache
        
        cache = LRUCache(max_size=3)
        cache.set("a", 1)
        cache.set("b", 2)
        cache.set("c", 3)
        
        assert cache.get("a") == 1
        
        cache.set("d", 4)
        # "b" should be evicted
        assert cache.get("b") is None

    def test_cache_stats(self):
        """Test cache statistics."""
        from atomic_search.utils.cache import LRUCache
        
        cache = LRUCache()
        cache.set("key", "value")
        assert cache.get("key") == "value"
        
        stats = cache.get_stats()
        assert "hits" in stats
        assert "misses" in stats


class TestRateLimiter:
    """Test rate limiting."""

    def test_ip_rate_limit(self):
        """Test IP rate limiting."""
        from atomic_search.utils.rate_limiter import ip_limiter
        
        allowed, remaining = ip_limiter.check_ip("127.0.0.1")
        assert allowed is True
        assert isinstance(remaining, dict)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
