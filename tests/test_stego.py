"""
Tests for stego_engine.py — LSB Steganography Encode & Decode
==============================================================
Verifies:
    - Encode → Decode round-trip returns original data
    - Capacity calculation is correct
    - Payload too large → clear error
    - PNG enforcement
    - Various payload sizes (1 byte, 1KB, max capacity)
    - Image visual integrity (resolution preserved)
"""

import pytest
import os
import sys
import numpy as np
from pathlib import Path
from PIL import Image

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from core import stego_engine


# ──────────────────────────────────────────────
#  Fixtures
# ──────────────────────────────────────────────
@pytest.fixture
def tmp_dir(tmp_path):
    """Provide a temporary directory for test files."""
    return tmp_path


@pytest.fixture
def small_image(tmp_dir):
    """Create a small test image (100×100 = 10,000 pixels ≈ 3,750 bytes capacity)."""
    path = tmp_dir / "small_carrier.png"
    img = Image.fromarray(
        np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8),
        mode="RGB"
    )
    img.save(path, format="PNG")
    return path


@pytest.fixture
def medium_image(tmp_dir):
    """Create a medium test image (500×500 = 250,000 pixels ≈ 93,750 bytes capacity)."""
    path = tmp_dir / "medium_carrier.png"
    img = Image.fromarray(
        np.random.randint(0, 256, (500, 500, 3), dtype=np.uint8),
        mode="RGB"
    )
    img.save(path, format="PNG")
    return path


@pytest.fixture
def tiny_image(tmp_dir):
    """Create a tiny image (10×10 = 100 pixels ≈ 33 bytes capacity)."""
    path = tmp_dir / "tiny_carrier.png"
    img = Image.fromarray(
        np.random.randint(0, 256, (10, 10, 3), dtype=np.uint8),
        mode="RGB"
    )
    img.save(path, format="PNG")
    return path


# ──────────────────────────────────────────────
#  Capacity Tests
# ──────────────────────────────────────────────
class TestCapacity:
    """Tests for calculate_capacity()."""

    def test_capacity_small_image(self, small_image):
        """100×100 image: 10,000 pixels × 3 bits = 30,000 bits. Minus 32 header = 29,968 bits = 3,746 bytes."""
        capacity = stego_engine.calculate_capacity(small_image)
        expected = (100 * 100 * 3 - 32) // 8
        assert capacity == expected

    def test_capacity_medium_image(self, medium_image):
        """500×500 image capacity calculation."""
        capacity = stego_engine.calculate_capacity(medium_image)
        expected = (500 * 500 * 3 - 32) // 8
        assert capacity == expected

    def test_capacity_nonexistent_file(self, tmp_dir):
        """Nonexistent file should raise FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            stego_engine.calculate_capacity(tmp_dir / "ghost.png")


# ──────────────────────────────────────────────
#  Encoding Tests
# ──────────────────────────────────────────────
class TestEncode:
    """Tests for encode()."""

    def test_encode_creates_file(self, small_image, tmp_dir):
        """Encoding should create an output file."""
        output = tmp_dir / "stego_output.png"
        data = b"Hello, World!"
        stego_engine.encode(small_image, data, output)
        assert output.exists()

    def test_encode_preserves_resolution(self, small_image, tmp_dir):
        """Stego-image should have the same resolution as the carrier."""
        output = tmp_dir / "stego_output.png"
        stego_engine.encode(small_image, b"test data", output)

        original = Image.open(small_image)
        stego = Image.open(output)
        assert original.size == stego.size

    def test_encode_rejects_jpeg_output(self, small_image, tmp_dir):
        """JPEG output should be rejected (lossy = data loss)."""
        with pytest.raises(ValueError, match="png"):
            stego_engine.encode(small_image, b"data", tmp_dir / "bad.jpg")

    def test_encode_payload_too_large(self, tiny_image, tmp_dir):
        """Data larger than capacity should raise ValueError."""
        big_data = b"x" * 1000  # Way more than 33 bytes
        with pytest.raises(ValueError, match="too large"):
            stego_engine.encode(tiny_image, big_data, tmp_dir / "out.png")

    def test_encode_nonexistent_carrier(self, tmp_dir):
        """Nonexistent carrier should raise FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            stego_engine.encode(
                tmp_dir / "ghost.png", b"data", tmp_dir / "out.png"
            )


# ──────────────────────────────────────────────
#  Decode Tests
# ──────────────────────────────────────────────
class TestDecode:
    """Tests for decode()."""

    def test_decode_nonexistent_file(self, tmp_dir):
        """Nonexistent stego-image should raise FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            stego_engine.decode(tmp_dir / "ghost.png")


# ──────────────────────────────────────────────
#  Round-Trip Tests
# ──────────────────────────────────────────────
class TestRoundTrip:
    """Tests for encode → decode round-trip."""

    def test_roundtrip_simple_text(self, small_image, tmp_dir):
        """Encode then decode simple text → original."""
        original = b"Hello, Stego-Cloud!"
        output = tmp_dir / "stego.png"

        stego_engine.encode(small_image, original, output)
        extracted = stego_engine.decode(output)

        assert extracted == original

    def test_roundtrip_binary_data(self, small_image, tmp_dir):
        """Encode then decode binary data → original."""
        original = os.urandom(512)
        output = tmp_dir / "stego.png"

        stego_engine.encode(small_image, original, output)
        extracted = stego_engine.decode(output)

        assert extracted == original

    def test_roundtrip_single_byte(self, small_image, tmp_dir):
        """Edge case: single byte payload."""
        original = b"\x42"
        output = tmp_dir / "stego.png"

        stego_engine.encode(small_image, original, output)
        extracted = stego_engine.decode(output)

        assert extracted == original

    def test_roundtrip_max_capacity(self, small_image, tmp_dir):
        """Test with data filling the entire image capacity."""
        capacity = stego_engine.calculate_capacity(small_image)
        original = os.urandom(capacity)  # Fill to max
        output = tmp_dir / "stego.png"

        stego_engine.encode(small_image, original, output)
        extracted = stego_engine.decode(output)

        assert extracted == original

    def test_roundtrip_near_max_capacity(self, small_image, tmp_dir):
        """Test with data just under max capacity."""
        capacity = stego_engine.calculate_capacity(small_image)
        original = os.urandom(capacity - 1)
        output = tmp_dir / "stego.png"

        stego_engine.encode(small_image, original, output)
        extracted = stego_engine.decode(output)

        assert extracted == original

    def test_roundtrip_medium_image(self, medium_image, tmp_dir):
        """Round-trip with a larger image and larger payload."""
        original = os.urandom(50000)  # 50KB
        output = tmp_dir / "stego.png"

        stego_engine.encode(medium_image, original, output)
        extracted = stego_engine.decode(output)

        assert extracted == original

    def test_visual_similarity(self, small_image, tmp_dir):
        """
        The stego-image should be visually similar to the original.
        Since we only modify LSBs, maximum per-channel change is 1.
        """
        data = os.urandom(1000)
        output = tmp_dir / "stego.png"
        stego_engine.encode(small_image, data, output)

        original_pixels = np.array(Image.open(small_image).convert("RGB"))
        stego_pixels = np.array(Image.open(output).convert("RGB"))

        # Maximum difference per channel should be at most 1
        diff = np.abs(original_pixels.astype(int) - stego_pixels.astype(int))
        assert diff.max() <= 1, f"Max pixel difference is {diff.max()}, expected ≤ 1"
