"""
Encryption utilities for Atomic Search.

Provides encryption, decryption, and key management.
"""

import base64
import hashlib
import hmac
import os
import secrets
from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass
class EncryptedData:
    """Encrypted data container."""
    ciphertext: bytes
    nonce: bytes
    tag: Optional[bytes] = None


class CryptoManager:
    """Cryptographic operations manager."""

    def __init__(self, key: Optional[bytes] = None):
        self.key = key or self._generate_key()

    def _generate_key(self, length: int = 32) -> bytes:
        """Generate a random key."""
        return secrets.token_bytes(length)

    @staticmethod
    def generate_token(length: int = 32) -> str:
        """Generate a secure random token."""
        return secrets.token_urlsafe(length)

    @staticmethod
    def generate_salt(length: int = 16) -> str:
        """Generate a salt for hashing."""
        return secrets.token_hex(length)

    @staticmethod
    def hash_password(password: str, salt: Optional[str] = None) -> Tuple[str, str]:
        """Hash a password with salt."""
        if salt is None:
            salt = CryptoManager.generate_salt()

        # Use Argon2-like PBKDF2
        key = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt.encode('utf-8'),
            100000
        )

        return base64.b64encode(key).decode('utf-8'), salt

    @staticmethod
    def verify_password(password: str, hashed: str, salt: str) -> bool:
        """Verify a password against hash."""
        computed_hash, _ = CryptoManager.hash_password(password, salt)
        return secrets.compare_digest(computed_hash, hashed)

    @staticmethod
    def hash_data(data: str, algorithm: str = 'sha256') -> str:
        """Hash data with specified algorithm."""
        if algorithm == 'md5':
            return hashlib.md5(data.encode()).hexdigest()
        elif algorithm == 'sha1':
            return hashlib.sha1(data.encode()).hexdigest()
        elif algorithm == 'sha256':
            return hashlib.sha256(data.encode()).hexdigest()
        elif algorithm == 'sha512':
            return hashlib.sha512(data.encode()).hexdigest()
        elif algorithm == 'blake2b':
            return hashlib.blake2b(data.encode()).hexdigest()
        else:
            return hashlib.sha256(data.encode()).hexdigest()

    @staticmethod
    def hmac_sign(message: str, key: str) -> str:
        """Create HMAC signature."""
        return hmac.new(
            key.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

    @staticmethod
    def hmac_verify(message: str, signature: str, key: str) -> bool:
        """Verify HMAC signature."""
        expected = CryptoManager.hmac_sign(message, key)
        return secrets.compare_digest(expected, signature)

    @staticmethod
    def encode_base64(data: str) -> str:
        """Encode data to base64."""
        return base64.b64encode(data.encode()).decode()

    @staticmethod
    def decode_base64(encoded: str) -> Optional[str]:
        """Decode base64 data."""
        try:
            return base64.b64decode(encoded.encode()).decode()
        except Exception:
            return None

    @staticmethod
    def encode_base64_url(data: str) -> str:
        """URL-safe base64 encode."""
        return base64.urlsafe_b64encode(data.encode()).decode().rstrip('=')

    @staticmethod
    def decode_base64_url(encoded: str) -> Optional[str]:
        """URL-safe base64 decode."""
        try:
            # Add padding
            padding = 4 - len(encoded) % 4
            if padding != 4:
                encoded += '=' * padding
            return base64.urlsafe_b64decode(encoded.encode()).decode()
        except Exception:
            return None

    @staticmethod
    def xor_encrypt(data: str, key: str) -> str:
        """Simple XOR encryption (for non-sensitive data)."""
        key_bytes = key.encode()
        data_bytes = data.encode()
        result = bytearray()

        for i, byte in enumerate(data_bytes):
            result.append(byte ^ key_bytes[i % len(key_bytes)])

        return base64.b64encode(bytes(result)).decode()

    @staticmethod
    def xor_decrypt(encrypted: str, key: str) -> Optional[str]:
        """Decrypt XOR encrypted data."""
        try:
            data = base64.b64decode(encrypted.encode())
            key_bytes = key.encode()
            result = bytearray()

            for i, byte in enumerate(data):
                result.append(byte ^ key_bytes[i % len(key_bytes)])

            return bytes(result).decode()
        except Exception:
            return None

    def create_signature(self, data: str) -> str:
        """Create signature for data."""
        return hmac.new(
            self.key,
            data.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

    def verify_signature(self, data: str, signature: str) -> bool:
        """Verify signature for data."""
        expected = self.create_signature(data)
        return secrets.compare_digest(expected, signature)


# Global crypto manager
crypto = CryptoManager()
