"""
Utilities — Capacity Validation & Helper Functions
===================================================
Provides convenience functions for capacity checking, file info,
and human-readable formatting used across the Stego-Cloud pipeline.
"""

from pathlib import Path
from typing import Union, Dict
from PIL import Image

from core.stego_engine import calculate_capacity


# ──────────────────────────────────────────────
#  Size Formatting
# ──────────────────────────────────────────────
def format_size(size_bytes: int) -> str:
    """
    Convert a byte count to a human-readable string.

    Examples:
        format_size(0)       → "0 B"
        format_size(1024)    → "1.00 KB"
        format_size(3145728) → "3.00 MB"
    """
    if size_bytes == 0:
        return "0 B"

    units = ["B", "KB", "MB", "GB", "TB"]
    unit_index = 0
    size = float(size_bytes)

    while size >= 1024 and unit_index < len(units) - 1:
        size /= 1024
        unit_index += 1

    if unit_index == 0:
        return f"{int(size)} B"
    return f"{size:.2f} {units[unit_index]}"


# ──────────────────────────────────────────────
#  Image Info
# ──────────────────────────────────────────────
def get_image_info(image_path: Union[str, Path]) -> Dict:
    """
    Get detailed information about a carrier image.

    Args:
        image_path: Path to the image file.

    Returns:
        Dictionary with keys:
            - path: str
            - format: str (e.g., "PNG", "JPEG")
            - resolution: str (e.g., "3840×2160")
            - width: int
            - height: int
            - total_pixels: int
            - file_size: str (human-readable)
            - max_capacity: str (human-readable)
            - max_capacity_bytes: int
    """
    image_path = Path(image_path)

    if not image_path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")

    with Image.open(image_path) as img:
        width, height = img.size
        img_format = img.format or "Unknown"

    total_pixels = width * height
    file_size = image_path.stat().st_size
    capacity = calculate_capacity(image_path)

    return {
        "path": str(image_path),
        "format": img_format,
        "resolution": f"{width}×{height}",
        "width": width,
        "height": height,
        "total_pixels": total_pixels,
        "file_size": format_size(file_size),
        "max_capacity": format_size(capacity),
        "max_capacity_bytes": capacity,
    }


# ──────────────────────────────────────────────
#  Capacity Validation
# ──────────────────────────────────────────────
def validate_capacity(
    image_path: Union[str, Path],
    data_size: int
) -> Dict:
    """
    Check if a carrier image can hold a given amount of data.

    Args:
        image_path: Path to the carrier image.
        data_size:  Size of the data to hide (in bytes). This should be the
                    size of the *encrypted* data, not the raw file.

    Returns:
        Dictionary with keys:
            - can_fit: bool
            - image_capacity: int (bytes)
            - data_size: int (bytes)
            - remaining: int (bytes, negative if doesn't fit)
            - utilization: float (percentage, 0-100+)
            - message: str (human-readable summary)
    """
    image_path = Path(image_path)
    capacity = calculate_capacity(image_path)
    remaining = capacity - data_size
    utilization = (data_size / capacity * 100) if capacity > 0 else float("inf")

    can_fit = remaining >= 0

    if can_fit:
        message = (
            f"✅ Data fits! Using {format_size(data_size)} of "
            f"{format_size(capacity)} ({utilization:.1f}% utilization). "
            f"{format_size(remaining)} remaining."
        )
    else:
        message = (
            f"❌ Data too large! Need {format_size(data_size)} but image "
            f"can only hold {format_size(capacity)}. "
            f"Overage: {format_size(abs(remaining))}."
        )

    return {
        "can_fit": can_fit,
        "image_capacity": capacity,
        "data_size": data_size,
        "remaining": remaining,
        "utilization": round(utilization, 2),
        "message": message,
    }


# ──────────────────────────────────────────────
#  Supported File Types
# ──────────────────────────────────────────────
# Files that can be hidden inside images.
# Sprint 1 supports all binary-safe file types — the crypto engine
# treats everything as raw bytes, so any file format works.
SUPPORTED_EXTENSIONS = {
    # Text
    ".txt", ".md", ".csv", ".json", ".xml", ".yaml", ".yml", ".log",
    # Documents
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
    # Code
    ".py", ".js", ".ts", ".html", ".css", ".java", ".c", ".cpp",
    # Archives (small ones)
    ".zip", ".gz", ".tar",
    # Keys & Secrets
    ".pem", ".key", ".env", ".pgp",
    # Other
    ".dat", ".bin",
}


def is_supported_file(file_path: Union[str, Path]) -> bool:
    """Check if a file type is in our supported list."""
    return Path(file_path).suffix.lower() in SUPPORTED_EXTENSIONS


def get_file_info(file_path: Union[str, Path]) -> Dict:
    """
    Get information about a secret file to be hidden.

    Returns:
        Dictionary with keys:
            - path, name, extension, size, size_readable
    """
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    size = file_path.stat().st_size
    return {
        "path": str(file_path),
        "name": file_path.name,
        "extension": file_path.suffix.lower(),
        "size": size,
        "size_readable": format_size(size),
    }
