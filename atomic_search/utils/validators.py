"""
Input validation for Atomic Search.

Provides comprehensive input validation and sanitization.
"""

import re
import unicodedata
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class ValidationResult:
    """Result of validation."""
    valid: bool
    errors: List[str]
    sanitized: Any = None


class Validator:
    """Input validation class."""

    # Patterns
    URL_PATTERN = re.compile(
        r'^https?://'
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'
        r'localhost|'
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'
        r'(?::\d+)?'
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)

    EMAIL_PATTERN = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')

    USERNAME_PATTERN = re.compile(r'^[a-zA-Z0-9_-]{3,32}$')

    HASH_PATTERN = re.compile(r'^[a-fA-F0-9]{32,64}$')

    IPV4_PATTERN = re.compile(
        r'^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}'
        r'(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$')

    def __init__(self):
        self.max_query_length = 500
        self.max_results = 100
        self.blocked_terms = self._load_blocked_terms()

    def _load_blocked_terms(self) -> set:
        """Load blocked search terms."""
        return {
            # Add blocked terms here
        }

    def validate_query(self, query: str) -> ValidationResult:
        """Validate search query."""
        errors = []

        if not query:
            errors.append("Query cannot be empty")
            return ValidationResult(False, errors)

        if len(query) > self.max_query_length:
            errors.append(f"Query too long (max {self.max_query_length} chars)")

        if len(query) < 2:
            errors.append("Query too short (min 2 chars)")

        # Check for blocked terms
        query_lower = query.lower()
        for term in self.blocked_terms:
            if term in query_lower:
                errors.append(f"Query contains blocked term")
                break

        # Sanitize
        sanitized = self._sanitize_query(query)

        if errors:
            return ValidationResult(False, errors, sanitized)

        return ValidationResult(True, [], sanitized)

    def _sanitize_query(self, query: str) -> str:
        """Sanitize search query."""
        # Remove control characters
        query = ''.join(char for char in query if unicodedata.category(char)[0] != 'C' or char in '\n\t')

        # Normalize whitespace
        query = ' '.join(query.split())

        # Remove potentially dangerous characters
        query = re.sub(r'[<>"\';\\]', '', query)

        return query.strip()

    def validate_url(self, url: str) -> ValidationResult:
        """Validate URL."""
        errors = []

        if not url:
            errors.append("URL cannot be empty")
            return ValidationResult(False, errors)

        if len(url) > 2048:
            errors.append("URL too long")

        if not self.URL_PATTERN.match(url):
            errors.append("Invalid URL format")

        if errors:
            return ValidationResult(False, errors)

        return ValidationResult(True, [], url)

    def validate_email(self, email: str) -> ValidationResult:
        """Validate email address."""
        errors = []

        if not email:
            errors.append("Email cannot be empty")
            return ValidationResult(False, errors)

        if not self.EMAIL_PATTERN.match(email):
            errors.append("Invalid email format")

        return ValidationResult(not bool(errors), errors, email.lower())

    def validate_username(self, username: str) -> ValidationResult:
        """Validate username."""
        errors = []

        if not username:
            errors.append("Username cannot be empty")
            return ValidationResult(False, errors)

        if not self.USERNAME_PATTERN.match(username):
            errors.append("Username must be 3-32 alphanumeric characters")

        return ValidationResult(not bool(errors), errors, username.lower())

    def validate_hash(self, hash_str: str) -> ValidationResult:
        """Validate hash string."""
        errors = []

        if not hash_str:
            errors.append("Hash cannot be empty")
            return ValidationResult(False, errors)

        if not self.HASH_PATTERN.match(hash_str):
            errors.append("Invalid hash format")

        return ValidationResult(not bool(errors), errors, hash_str.lower())

    def validate_ip(self, ip: str) -> ValidationResult:
        """Validate IPv4 address."""
        errors = []

        if not ip:
            errors.append("IP cannot be empty")
            return ValidationResult(False, errors)

        if not self.IPV4_PATTERN.match(ip):
            errors.append("Invalid IPv4 address")

        return ValidationResult(not bool(errors), errors, ip)

    def validate_page(self, page: Any) -> Tuple[int, bool]:
        """Validate page number."""
        try:
            page = int(page)
            if page < 1:
                page = 1
            if page > 100:
                page = 100
            return page, True
        except (ValueError, TypeError):
            return 1, False

    def validate_results_count(self, count: Any) -> Tuple[int, bool]:
        """Validate results count."""
        try:
            count = int(count)
            if count < 1:
                count = 10
            if count > self.max_results:
                count = self.max_results
            return count, True
        except (ValueError, TypeError):
            return 10, False

    def validate_api_key(self, api_key: str) -> ValidationResult:
        """Validate API key format."""
        errors = []

        if not api_key:
            errors.append("API key cannot be empty")
            return ValidationResult(False, errors)

        if len(api_key) < 32:
            errors.append("API key too short")

        if not re.match(r'^[a-zA-Z0-9_-]+$', api_key):
            errors.append("API key contains invalid characters")

        return ValidationResult(not bool(errors), errors)

    def validate_config(self, config: Dict[str, Any]) -> ValidationResult:
        """Validate configuration dictionary."""
        errors = []

        required_fields = ['app_name', 'version']
        for field in required_fields:
            if field not in config:
                errors.append(f"Missing required field: {field}")

        # Validate app_name
        if 'app_name' in config:
            name = config['app_name']
            if not isinstance(name, str) or len(name) < 2 or len(name) > 100:
                errors.append("Invalid app_name")

        # Validate version
        if 'version' in config:
            version = config['version']
            if not re.match(r'^\d+\.\d+\.\d+$', version):
                errors.append("Invalid version format (use semver)")

        return ValidationResult(not bool(errors), errors)


# Global validator instance
validator = Validator()
