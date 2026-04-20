"""
Stego Engine — LSB (Least Significant Bit) Steganography
=========================================================
Hides encrypted binary data inside the pixels of a carrier image.

How it works:
    Every pixel has 3 color channels (R, G, B), each stored as an 8-bit value (0-255).
    The Least Significant Bit (LSB) of each channel has minimal visual impact —
    changing it shifts the color by at most 1/256, which is imperceptible to the human eye.

    We exploit this by replacing the LSB of each channel with one bit of our secret payload.
    A 4K image (3840×2160) has ~8.2M pixels × 3 channels = ~24.8M bits ≈ 3.1 MB of capacity.

Encoding format:
    [32-bit payload length (big-endian)][payload bits...]
    The 32-bit header tells the decoder how many bits to extract.

CRITICAL: Output MUST be saved as PNG. JPEG is lossy and would destroy the hidden data.
"""

import numpy as np
from PIL import Image
from pathlib import Path
from typing import Union


# ──────────────────────────────────────────────
#  Constants
# ──────────────────────────────────────────────
HEADER_BITS = 32   # 32-bit unsigned integer for payload length (supports up to ~4GB)
BITS_PER_CHANNEL = 1  # Number of LSBs used per color channel


# ──────────────────────────────────────────────
#  Capacity Calculation
# ──────────────────────────────────────────────
def calculate_capacity(image_path: Union[str, Path]) -> int:
    """
    Calculate the maximum number of bytes that can be hidden in an image.

    Args:
        image_path: Path to the carrier image file.

    Returns:
        Maximum payload size in bytes (excluding the 32-bit header overhead).

    The formula:
        total_bits = width × height × 3 (channels) × BITS_PER_CHANNEL
        usable_bits = total_bits - HEADER_BITS (reserved for length header)
        capacity_bytes = usable_bits // 8
    """
    image_path = Path(image_path)
    if not image_path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")

    with Image.open(image_path) as img:
        width, height = img.size
        total_pixels = width * height
        total_bits = total_pixels * 3 * BITS_PER_CHANNEL
        usable_bits = total_bits - HEADER_BITS
        return max(0, usable_bits // 8)


# ──────────────────────────────────────────────
#  LSB Encoding
# ──────────────────────────────────────────────
def encode(image_path: Union[str, Path], data: bytes, output_path: Union[str, Path]) -> Path:
    """
    Hide binary data inside a carrier image using LSB steganography.

    Args:
        image_path:  Path to the carrier image (any format Pillow supports).
        data:        The secret bytes to hide (should already be encrypted).
        output_path: Where to save the resulting stego-image (MUST be .png).

    Returns:
        Path to the saved stego-image.

    Raises:
        ValueError: If the data exceeds the image's capacity.
        FileNotFoundError: If the carrier image doesn't exist.

    Algorithm:
        1. Load image as RGB NumPy array
        2. Prepend 32-bit big-endian length header to the payload
        3. Convert entire payload to a flat bitstream
        4. Validate capacity
        5. Clear the LSB of each pixel channel value
        6. Set the LSB to the corresponding bit from the payload
        7. Save as lossless PNG
    """
    image_path = Path(image_path)
    output_path = Path(output_path)

    if not image_path.exists():
        raise FileNotFoundError(f"Carrier image not found: {image_path}")

    # Enforce PNG output (lossless — JPEG would destroy hidden data)
    if output_path.suffix.lower() != ".png":
        raise ValueError(
            f"Output must be .png (got '{output_path.suffix}'). "
            "JPEG/WebP are lossy and would corrupt hidden data."
        )

    # Load image and convert to RGB (strip alpha channel if present)
    img = Image.open(image_path).convert("RGB")
    pixels = np.array(img, dtype=np.uint8)
    height, width, channels = pixels.shape

    # Build the payload: [32-bit length header][data]
    payload_length = len(data)
    header = payload_length.to_bytes(4, byteorder="big")
    full_payload = header + data

    # Convert payload bytes to a flat array of individual bits
    payload_bits = np.unpackbits(
        np.frombuffer(full_payload, dtype=np.uint8)
    )

    # Capacity check
    total_available_bits = height * width * channels * BITS_PER_CHANNEL
    if len(payload_bits) > total_available_bits:
        capacity_bytes = (total_available_bits - HEADER_BITS) // 8
        raise ValueError(
            f"Payload too large! "
            f"Data size: {len(data):,} bytes. "
            f"Image capacity: {capacity_bytes:,} bytes. "
            f"Image resolution: {width}×{height} ({width * height:,} pixels). "
            f"Use a higher-resolution carrier image."
        )

    # Flatten the pixel array for easy iteration
    flat_pixels = pixels.flatten()

    # Inject bits into the LSBs
    # Step 1: Clear the LSBs of only the pixels we need
    flat_pixels[:len(payload_bits)] = (
        (flat_pixels[:len(payload_bits)] & 0xFE) | payload_bits
    )

    # Reshape back to image dimensions and save
    stego_pixels = flat_pixels.reshape((height, width, channels))
    stego_img = Image.fromarray(stego_pixels, mode="RGB")

    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)
    stego_img.save(output_path, format="PNG")

    return output_path


# ──────────────────────────────────────────────
#  LSB Decoding
# ──────────────────────────────────────────────
def decode(stego_image_path: Union[str, Path]) -> bytes:
    """
    Extract hidden data from a stego-image.

    Args:
        stego_image_path: Path to the stego-image containing hidden data.

    Returns:
        The extracted bytes (still encrypted — pass to crypto_engine.decrypt()).

    Raises:
        FileNotFoundError: If the stego-image doesn't exist.
        ValueError: If the extracted header indicates an impossible payload size.

    Algorithm:
        1. Load stego-image as RGB NumPy array
        2. Extract the LSB from each channel value
        3. Read first 32 bits → interpret as payload length (big-endian)
        4. Read exactly that many more bits
        5. Pack bits back into bytes and return
    """
    stego_image_path = Path(stego_image_path)

    if not stego_image_path.exists():
        raise FileNotFoundError(f"Stego-image not found: {stego_image_path}")

    # Load the stego-image
    img = Image.open(stego_image_path).convert("RGB")
    pixels = np.array(img, dtype=np.uint8)
    height, width, channels = pixels.shape

    # Flatten and extract all LSBs
    flat_pixels = pixels.flatten()
    all_lsbs = flat_pixels & 1  # Extract LSB from every channel value

    # Read the 32-bit header to get payload length
    header_bits = all_lsbs[:HEADER_BITS]
    header_bytes = np.packbits(header_bits)
    payload_length = int.from_bytes(header_bytes[:4], byteorder="big")

    # Sanity check: payload length shouldn't exceed image capacity
    max_payload = (len(all_lsbs) - HEADER_BITS) // 8
    if payload_length > max_payload or payload_length < 0:
        raise ValueError(
            f"Invalid payload length extracted: {payload_length:,} bytes. "
            f"Maximum possible: {max_payload:,} bytes. "
            "This image may not contain hidden data, or the data is corrupted."
        )

    if payload_length == 0:
        raise ValueError(
            "Payload length is 0. This image does not appear to contain hidden data."
        )

    # Extract the payload bits
    total_payload_bits = payload_length * 8
    payload_bits = all_lsbs[HEADER_BITS:HEADER_BITS + total_payload_bits]

    # Pad to multiple of 8 if necessary (shouldn't happen, but safety first)
    remainder = len(payload_bits) % 8
    if remainder != 0:
        payload_bits = np.concatenate([
            payload_bits,
            np.zeros(8 - remainder, dtype=np.uint8)
        ])

    # Pack bits back into bytes
    payload_bytes = np.packbits(payload_bits)

    return bytes(payload_bytes[:payload_length])
