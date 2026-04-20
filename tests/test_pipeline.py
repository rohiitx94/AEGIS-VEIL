"""
Tests for Full Pipeline — Crypto + Stego Integration
======================================================
Verifies the complete end-to-end flow:
    Secret File → Encrypt → LSB Encode → LSB Decode → Decrypt → Original File

This is the most critical test: it proves the entire system works together.
"""

import pytest
import os
import sys
import hashlib
import numpy as np
from pathlib import Path
from PIL import Image

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from core import crypto_engine, stego_engine
from core.utils import validate_capacity, format_size


# ──────────────────────────────────────────────
#  Fixtures
# ──────────────────────────────────────────────
@pytest.fixture
def carrier_image(tmp_path):
    """Create a 500×500 carrier image (capacity ≈ 93KB)."""
    path = tmp_path / "carrier.png"
    img = Image.fromarray(
        np.random.randint(0, 256, (500, 500, 3), dtype=np.uint8),
        mode="RGB"
    )
    img.save(path, format="PNG")
    return path


@pytest.fixture
def large_carrier(tmp_path):
    """Create a 1000×1000 carrier image (capacity ≈ 375KB)."""
    path = tmp_path / "large_carrier.png"
    img = Image.fromarray(
        np.random.randint(0, 256, (1000, 1000, 3), dtype=np.uint8),
        mode="RGB"
    )
    img.save(path, format="PNG")
    return path


@pytest.fixture
def sample_text_file(tmp_path):
    """Create a sample text file to hide."""
    path = tmp_path / "secret.txt"
    content = (
        "TOP SECRET: Stego-Cloud Project\n"
        "================================\n"
        "This is a classified document containing\n"
        "sensitive information that must be hidden.\n"
        "\n"
        "Password: hunter2\n"
        "API Key: sk-abc123def456\n"
        "Recovery Phrase: apple banana cherry delta echo foxtrot\n"
    )
    path.write_text(content)
    return path


@pytest.fixture
def sample_binary_file(tmp_path):
    """Create a sample binary file (simulates a PDF or small document)."""
    path = tmp_path / "secret.bin"
    path.write_bytes(os.urandom(10000))  # 10KB random binary
    return path


# ──────────────────────────────────────────────
#  Full Pipeline Tests
# ──────────────────────────────────────────────
class TestFullPipeline:
    """End-to-end: File → Encrypt → Encode → Decode → Decrypt → File"""

    def test_text_file_pipeline(self, carrier_image, sample_text_file, tmp_path):
        """Complete round-trip with a text file."""
        password = "SuperSecretPassword123!"
        stego_output = tmp_path / "stego.png"
        extracted_output = tmp_path / "extracted.txt"

        # Read original
        original_data = sample_text_file.read_bytes()
        original_hash = hashlib.sha256(original_data).hexdigest()

        # Encrypt
        encrypted = crypto_engine.encrypt(original_data, password)

        # Validate capacity
        validation = validate_capacity(carrier_image, len(encrypted))
        assert validation["can_fit"], validation["message"]

        # Encode into image
        stego_engine.encode(carrier_image, encrypted, stego_output)
        assert stego_output.exists()

        # Decode from image
        extracted_encrypted = stego_engine.decode(stego_output)

        # Decrypt
        decrypted = crypto_engine.decrypt(extracted_encrypted, password)

        # Verify
        extracted_hash = hashlib.sha256(decrypted).hexdigest()
        assert extracted_hash == original_hash, "SHA-256 mismatch!"
        assert decrypted == original_data, "Data mismatch!"

        # Save and verify file content
        extracted_output.write_bytes(decrypted)
        assert extracted_output.read_text() == sample_text_file.read_text()

    def test_binary_file_pipeline(self, carrier_image, sample_binary_file, tmp_path):
        """Complete round-trip with a binary file."""
        password = "BinaryTest_pässwörd_🔐"
        stego_output = tmp_path / "stego.png"

        original_data = sample_binary_file.read_bytes()
        original_hash = hashlib.sha256(original_data).hexdigest()

        encrypted = crypto_engine.encrypt(original_data, password)
        stego_engine.encode(carrier_image, encrypted, stego_output)
        extracted_encrypted = stego_engine.decode(stego_output)
        decrypted = crypto_engine.decrypt(extracted_encrypted, password)

        assert hashlib.sha256(decrypted).hexdigest() == original_hash
        assert decrypted == original_data

    def test_wrong_password_fails_pipeline(self, carrier_image, sample_text_file, tmp_path):
        """Full pipeline with wrong password should fail at decryption."""
        stego_output = tmp_path / "stego.png"

        original_data = sample_text_file.read_bytes()
        encrypted = crypto_engine.encrypt(original_data, "correct_password")
        stego_engine.encode(carrier_image, encrypted, stego_output)
        extracted_encrypted = stego_engine.decode(stego_output)

        with pytest.raises(ValueError, match="incorrect|tampered"):
            crypto_engine.decrypt(extracted_encrypted, "wrong_password")

    def test_multiple_files_same_carrier_resolution(self, large_carrier, tmp_path):
        """
        Different files encoded into images of the same resolution
        should all round-trip correctly (each using a fresh carrier copy).
        """
        password = "MultiFile123"
        files_data = [
            b"File 1: Short text",
            b"File 2: " + os.urandom(500),
            b"File 3: " + b"A" * 10000,
        ]

        for i, data in enumerate(files_data):
            stego_output = tmp_path / f"stego_{i}.png"

            encrypted = crypto_engine.encrypt(data, password)
            stego_engine.encode(large_carrier, encrypted, stego_output)
            extracted = stego_engine.decode(stego_output)
            decrypted = crypto_engine.decrypt(extracted, password)

            assert decrypted == data, f"File {i} failed round-trip"

    def test_pipeline_preserves_file_extension_data(self, carrier_image, tmp_path):
        """
        The pipeline should faithfully preserve any file content,
        regardless of what the file "is" — we treat everything as bytes.
        """
        # Simulate a tiny JSON config
        json_data = b'{"api_key": "sk-abc123", "secret": "hunter2"}'
        password = "JsonTest"
        stego_output = tmp_path / "stego.png"

        encrypted = crypto_engine.encrypt(json_data, password)
        stego_engine.encode(carrier_image, encrypted, stego_output)
        extracted = stego_engine.decode(stego_output)
        decrypted = crypto_engine.decrypt(extracted, password)

        assert decrypted == json_data

    def test_capacity_validation_integration(self, carrier_image, tmp_path):
        """Test that the capacity validator correctly predicts encode success/failure."""
        capacity = stego_engine.calculate_capacity(carrier_image)

        # Data that fits
        small_data = os.urandom(100)
        encrypted_small = crypto_engine.encrypt(small_data, "pass")
        validation = validate_capacity(carrier_image, len(encrypted_small))
        assert validation["can_fit"] is True

        # Data that doesn't fit
        huge_data = os.urandom(capacity + 1000)
        encrypted_huge = crypto_engine.encrypt(huge_data, "pass")
        validation = validate_capacity(carrier_image, len(encrypted_huge))
        assert validation["can_fit"] is False


class TestEdgeCases:
    """Edge cases and stress tests."""

    def test_minimal_data(self, carrier_image, tmp_path):
        """Single byte through the full pipeline."""
        stego_output = tmp_path / "stego.png"
        original = b"\x00"
        password = "minimal"

        encrypted = crypto_engine.encrypt(original, password)
        stego_engine.encode(carrier_image, encrypted, stego_output)
        extracted = stego_engine.decode(stego_output)
        decrypted = crypto_engine.decrypt(extracted, password)

        assert decrypted == original

    def test_long_password(self, carrier_image, tmp_path):
        """Very long password should work fine (PBKDF2 handles any length)."""
        stego_output = tmp_path / "stego.png"
        original = b"test data with long password"
        password = "a" * 10000  # 10,000 character password

        encrypted = crypto_engine.encrypt(original, password)
        stego_engine.encode(carrier_image, encrypted, stego_output)
        extracted = stego_engine.decode(stego_output)
        decrypted = crypto_engine.decrypt(extracted, password)

        assert decrypted == original

    def test_special_characters_in_data(self, carrier_image, tmp_path):
        """Data with null bytes, unicode, and special chars."""
        stego_output = tmp_path / "stego.png"
        original = "Hello\x00World\nEnd\r\nТест 日本語 🔑".encode("utf-8")
        password = "special"

        encrypted = crypto_engine.encrypt(original, password)
        stego_engine.encode(carrier_image, encrypted, stego_output)
        extracted = stego_engine.decode(stego_output)
        decrypted = crypto_engine.decrypt(extracted, password)

        assert decrypted == original
