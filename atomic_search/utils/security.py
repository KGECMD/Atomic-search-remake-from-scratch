"""
Security utilities for Atomic Search.

Provides comprehensive security features including:
- Password hashing
- Input validation and sanitization
- Rate limiting
- CSRF protection
- XSS prevention
- Encryption utilities
"""

import hashlib
import hmac
import os
import re
import secrets
import string
from typing import Any, List, Optional, Tuple

import bleach
from cryptography.fernet import Fernet
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from passlib.hash import pbkdf2_sha256

from atomic_search.config import config


# Password hashing
def hash_password(password: str, rounds: int = 100000) -> str:
    """Hash a password using PBKDF2-SHA256."""
    return pbkdf2_sha256.hash(password, rounds=rounds)


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password against its hash."""
    try:
        return pbkdf2_sha256.verify(password, password_hash)
    except Exception:
        return False


def generate_password(length: int = 16) -> str:
    """Generate a secure random password."""
    alphabet = string.ascii_letters + string.digits + string.punctuation
    while True:
        password = ''.join(secrets.choice(alphabet) for _ in range(length))
        if (any(c.islower() for c in password)
                and any(c.isupper() for c in password)
                and any(c.isdigit() for c in password)
                and any(c in string.punctuation for c in password)):
            return password


# Encryption utilities
_encryption_key: Optional[bytes] = None


def get_encryption_key() -> bytes:
    """Get or generate the encryption key."""
    global _encryption_key
    if _encryption_key is None:
        key_file = config.DATA_DIR / ".encryption_key"
        if key_file.exists():
            _encryption_key = key_file.read_bytes()
        else:
            _encryption_key = Fernet.generate_key()
            key_file.parent.mkdir(parents=True, exist_ok=True)
            key_file.write_bytes(_encryption_key)
            key_file.chmod(0o600)
    return _encryption_key


def encrypt_data(data: str) -> str:
    """Encrypt sensitive data using Fernet symmetric encryption."""
    f = Fernet(get_encryption_key())
    return f.encrypt(data.encode()).decode()


def decrypt_data(encrypted_data: str) -> str:
    """Decrypt data encrypted with encrypt_data."""
    f = Fernet(get_encryption_key())
    return f.decrypt(encrypted_data.encode()).decode()


# Hashing utilities
def hash_ip(ip: str, salt: Optional[str] = None) -> str:
    """Hash an IP address for privacy-preserving storage."""
    if salt is None:
        salt = config.SECRET_KEY[:16]
    return hashlib.pbkdf2_hmac(
        'sha256',
        ip.encode(),
        salt.encode(),
        100000
    ).hex()


def hash_string(value: str, salt: Optional[str] = None) -> str:
    """Create a SHA-256 hash of a string."""
    if salt is None:
        salt = config.SECRET_KEY[:16]
    return hashlib.pbkdf2_hmac(
        'sha256',
        value.encode(),
        salt.encode(),
        100000
    ).hex()


def generate_session_id() -> str:
    """Generate a secure random session ID."""
    return secrets.token_hex(32)


def generate_api_key() -> str:
    """Generate a secure random API key."""
    return f"as_{secrets.token_hex(32)}"


# Input sanitization
ALLOWED_TAGS = [
    'a', 'abbr', 'acronym', 'address', 'b', 'blockquote', 'br', 'code',
    'div', 'em', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'hr', 'i', 'img',
    'li', 'ol', 'p', 'pre', 'span', 'strong', 'sub', 'sup', 'table',
    'tbody', 'td', 'th', 'thead', 'tr', 'ul', 'ruby', 'rp', 'rt'
]

ALLOWED_ATTRIBUTES = {
    '*': ['class', 'id', 'style'],
    'a': ['href', 'title', 'rel', 'target'],
    'img': ['src', 'alt', 'title', 'width', 'height'],
    'abbr': ['title'],
    'acronym': ['title'],
    'td': ['colspan', 'rowspan'],
    'th': ['colspan', 'rowspan'],
}

ALLOWED_PROTOCOLS = ['http', 'https', 'mailto']


def sanitize_html(html: str) -> str:
    """Sanitize HTML content to prevent XSS attacks."""
    return bleach.clean(
        html,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        protocols=ALLOWED_PROTOCOLS,
        strip=True,
        strip_comments=True
    )


def sanitize_search_query(query: str) -> str:
    """Sanitize and validate search query input."""
    if not query:
        return ""

    # Remove null bytes and control characters
    query = query.replace('\x00', '')

    # Limit length
    max_length = 500
    query = query[:max_length]

    # Remove potentially dangerous patterns
    dangerous_patterns = [
        r'<script[^>]*>.*?</script>',
        r'javascript:',
        r'on\w+\s*=',
        r'<iframe',
        r'<object',
        r'<embed',
        r'eval\s*\(',
        r'exec\s*\(',
    ]

    for pattern in dangerous_patterns:
        query = re.sub(pattern, '', query, flags=re.IGNORECASE)

    # Normalize whitespace
    query = ' '.join(query.split())

    return query.strip()


def sanitize_url(url: str) -> str:
    """Sanitize and validate URL input."""
    if not url:
        return ""

    # Remove dangerous protocols
    dangerous_protocols = ['javascript:', 'data:', 'vbscript:']
    for protocol in dangerous_protocols:
        if url.lower().startswith(protocol):
            return ""

    # Only allow http and https
    if not url.startswith(('http://', 'https://', '/')):
        return ""

    # Limit length
    max_length = 2000
    return url[:max_length]


def validate_email(email: str) -> bool:
    """Validate email address format."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def validate_username(username: str) -> bool:
    """Validate username format."""
    if not username or len(username) < 3 or len(username) > 50:
        return False
    pattern = r'^[a-zA-Z0-9_-]+$'
    return bool(re.match(pattern, username))


# 2FA utilities
def generate_2fa_secret() -> str:
    """Generate a TOTP secret for 2FA."""
    return secrets.token_hex(20)


def generate_2fa_qrcode(secret: str, username: str) -> str:
    """Generate a QR code for 2FA setup."""
    import base64
    import io

    from pyotp import ProvisioningUri

    otp_uri = ProvisioningUri(
        name=username,
        issuer=config.APP_NAME,
        secret=secret
    )

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(otp_uri)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)

    return base64.b64encode(buffer.getvalue()).decode()


def verify_2fa_code(secret: str, code: str) -> bool:
    """Verify a TOTP code."""
    import pyotp
    totp = pyotp.TOTP(secret)
    return totp.verify(code)


# Security headers
def get_security_headers() -> dict:
    """Get security headers for HTTP responses."""
    headers = {
        'X-Content-Type-Options': 'nosniff',
        'X-Frame-Options': 'DENY',
        'X-XSS-Protection': '1; mode=block' if config.XSS_PROTECTION else '0',
        'Referrer-Policy': 'strict-origin-when-cross-origin',
        'Permissions-Policy': 'geolocation=(), microphone=(), camera=(), payment=()',
    }

    if config.HSTS_ENABLED:
        headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains; preload'

    if config.CONTENT_SECURITY_POLICY:
        headers['Content-Security-Policy'] = config.get_csp_policy()

    return headers


# Rate limiting
class RateLimiter:
    """In-memory rate limiter."""

    def __init__(self):
        self._requests: dict = {}
        self._window_start: float = 0

    def check_rate_limit(
        self,
        key: str,
        max_requests: int,
        window_seconds: int = 60
    ) -> Tuple[bool, int]:
        """Check if a request is within rate limits.

        Returns:
            Tuple of (is_allowed, remaining_requests)
        """
        import time

        current_time = time.time()

        # Reset window if expired
        if current_time - self._window_start > window_seconds:
            self._requests = {}
            self._window_start = current_time

        # Get request count for this key
        count = self._requests.get(key, 0)

        if count >= max_requests:
            return False, 0

        self._requests[key] = count + 1
        return True, max_requests - count - 1

    def reset(self, key: str) -> None:
        """Reset rate limit for a key."""
        if key in self._requests:
            del self._requests[key]


# CSRF token utilities
def generate_csrf_token() -> str:
    """Generate a CSRF token."""
    return secrets.token_hex(32)


def verify_csrf_token(token: str, session_token: str) -> bool:
    """Verify a CSRF token."""
    if not token or not session_token:
        return False
    return hmac.compare_digest(token, session_token)


# Secure random utilities
def secure_random_string(length: int = 32) -> str:
    """Generate a cryptographically secure random string."""
    return secrets.token_hex(length)


def secure_random_int(min_val: int, max_val: int) -> int:
    """Generate a cryptographically secure random integer."""
    return secrets.randbelow(max_val - min_val + 1) + min_val


# IP blocking
_blocked_ips: set = set()


def block_ip(ip_hash: str) -> None:
    """Block an IP address."""
    _blocked_ips.add(ip_hash)


def unblock_ip(ip_hash: str) -> None:
    """Unblock an IP address."""
    _blocked_ips.discard(ip_hash)


def is_ip_blocked(ip_hash: str) -> bool:
    """Check if an IP is blocked."""
    return ip_hash in _blocked_ips


# Login attempt tracking
_login_attempts: dict = {}


def record_login_attempt(username: str, success: bool) -> None:
    """Record a login attempt."""
    import time

    if username not in _login_attempts:
        _login_attempts[username] = []

    # Clean old attempts (older than 1 hour)
    current_time = time.time()
    _login_attempts[username] = [
        (t, s) for t, s in _login_attempts[username]
        if current_time - t < 3600
    ]

    _login_attempts[username].append((current_time, success))


def get_failed_attempts(username: str) -> int:
    """Get the number of failed login attempts for a username."""
    import time

    if username not in _login_attempts:
        return 0

    current_time = time.time()
    return sum(
        1 for t, s in _login_attempts[username]
        if not s and current_time - t < 3600
    )


def is_account_locked(username: str, max_attempts: int = 5) -> bool:
    """Check if an account is locked due to too many failed attempts."""
    return get_failed_attempts(username) >= max_attempts
