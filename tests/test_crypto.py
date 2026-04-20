"""
Tests for crypto_engine.py — AES-256-GCM Encryption & Decryption
=================================================================
Verifies:
    - Encrypt → Decrypt round-trip returns original data
    - Different passwords produce different ciphertext
    - Same plaintext + same password → different ciphertext (random salt/nonce)
    - Wrong password → decryption fails
    - Edge cases: empty data, empty password, minimal data
    - Tampered ciphertext → detection
"""

import pytest
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from core import crypto_engine


class TestKeyDerivation:
    """Tests for PBKDF2 key derivation."""

    def test_derive_key_returns_32_bytes(self):
        """AES-256 requires a 32-byte (256-bit) key."""
        salt = os.urandom(16)
        key = crypto_engine.derive_key("test_password", salt)
        assert len(key) == 32

    def test_same_password_same_salt_same_key(self):
        """Deterministic: same inputs → same key."""
        salt = b"\x00" * 16
        key1 = crypto_engine.derive_key("password123", salt)
        key2 = crypto_engine.derive_key("password123", salt)
        assert key1 == key2

    def test_different_password_different_key(self):
        """Different password → different key."""
        salt = b"\x00" * 16
        key1 = crypto_engine.derive_key("password_A", salt)
        key2 = crypto_engine.derive_key("password_B", salt)
        assert key1 != key2

    def test_different_salt_different_key(self):
        """Different salt → different key (even with same password)."""
        key1 = crypto_engine.derive_key("same_password", b"\x00" * 16)
        key2 = crypto_engine.derive_key("same_password", b"\xff" * 16)
        assert key1 != key2


class TestEncryption:
    """Tests for AES-256-GCM encryption."""

    def test_encrypt_returns_bytes(self):
        """Encrypted output should be bytes."""
        result = crypto_engine.encrypt(b"Hello, World!", "password")
        assert isinstance(result, bytes)

    def test_encrypt_output_larger_than_input(self):
        """Encrypted output includes salt(16) + nonce(16) + ciphertext + tag(16)."""
        data = b"Hello"
        result = crypto_engine.encrypt(data, "password")
        # At minimum: 16 + 16 + len(data) + 16 = 53 bytes
        assert len(result) >= len(data) + 48

    def test_encrypt_different_each_time(self):
        """Same data + same password → different ciphertext (random salt/nonce)."""
        data = b"repeated_data"
        enc1 = crypto_engine.encrypt(data, "same_pass")
        enc2 = crypto_engine.encrypt(data, "same_pass")
        assert enc1 != enc2

    def test_encrypt_empty_data_raises(self):
        """Encrypting empty data should raise ValueError."""
        with pytest.raises(ValueError, match="empty"):
            crypto_engine.encrypt(b"", "password")

    def test_encrypt_empty_password_raises(self):
        """Encrypting with empty password should raise ValueError."""
        with pytest.raises(ValueError, match="empty"):
            crypto_engine.encrypt(b"data", "")


class TestDecryption:
    """Tests for AES-256-GCM decryption."""

    def test_roundtrip_simple(self):
        """Basic round-trip: encrypt → decrypt → original."""
        original = b"Hello, Stego-Cloud!"
        password = "TestPassword123"
        encrypted = crypto_engine.encrypt(original, password)
        decrypted = crypto_engine.decrypt(encrypted, password)
        assert decrypted == original

    def test_roundtrip_binary_data(self):
        """Round-trip with random binary data (simulates any file type)."""
        original = os.urandom(1024)  # 1KB of random bytes
        password = "BinaryTest!"
        encrypted = crypto_engine.encrypt(original, password)
        decrypted = crypto_engine.decrypt(encrypted, password)
        assert decrypted == original

    def test_roundtrip_large_data(self):
        """Round-trip with larger data (100KB)."""
        original = os.urandom(100 * 1024)
        password = "LargeDataTest"
        encrypted = crypto_engine.encrypt(original, password)
        decrypted = crypto_engine.decrypt(encrypted, password)
        assert decrypted == original

    def test_roundtrip_unicode_password(self):
        """Round-trip with Unicode password."""
        original = b"Secret data"
        password = "пароль_密码_🔑"
        encrypted = crypto_engine.encrypt(original, password)
        decrypted = crypto_engine.decrypt(encrypted, password)
        assert decrypted == original

    def test_wrong_password_fails(self):
        """Decrypting with the wrong password should fail."""
        encrypted = crypto_engine.encrypt(b"secret", "correct_password")
        with pytest.raises(ValueError, match="incorrect|tampered"):
            crypto_engine.decrypt(encrypted, "wrong_password")

    def test_tampered_ciphertext_fails(self):
        """GCM should detect tampered ciphertext."""
        encrypted = crypto_engine.encrypt(b"important data", "password")
        # Flip a bit in the ciphertext (after salt + nonce, before tag)
        tampered = bytearray(encrypted)
        tampered[40] ^= 0xFF  # Flip bits at position 40
        with pytest.raises(ValueError, match="incorrect|tampered"):
            crypto_engine.decrypt(bytes(tampered), "password")

    def test_truncated_data_raises(self):
        """Too-short data should raise ValueError."""
        with pytest.raises(ValueError, match="too short"):
            crypto_engine.decrypt(b"short", "password")

    def test_empty_password_raises(self):
        """Decrypting with empty password should raise ValueError."""
        encrypted = crypto_engine.encrypt(b"data", "password")
        with pytest.raises(ValueError, match="empty"):
            crypto_engine.decrypt(encrypted, "")

    def test_roundtrip_single_byte(self):
        """Edge case: single byte of data."""
        original = b"\x42"
        password = "OneByte"
        encrypted = crypto_engine.encrypt(original, password)
        decrypted = crypto_engine.decrypt(encrypted, password)
        assert decrypted == original
