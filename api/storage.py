"""
Storage Manager — Local File Storage for Sprint 2
===================================================
Manages stego-images, carrier images, and metadata on the local filesystem.
In Sprint 2 this uses local disk; Sprint 3+ will add S3/Supabase Storage.

Directory structure:
    storage/
    ├── carriers/       # Original carrier images
    ├── stego_images/   # Images with hidden data
    ├── uploads/        # Temporary upload staging
    ├── extracted/      # Extracted files (temporary)
    └── metadata.json   # Image metadata registry
"""

import json
import uuid
import shutil
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, Dict, List

from api.config import settings
from core.utils import get_image_info, format_size


from api.db import supabase

# ──────────────────────────────────────────────
#  Metadata (Now handled by Supabase)
# ──────────────────────────────────────────────


# ──────────────────────────────────────────────
#  Image Storage Operations
# ──────────────────────────────────────────────
def store_stego_image(
    stego_image_path: Path,
    original_carrier_name: str,
    user_id: str,
    vault_id: str,
    hidden_file_name: Optional[str] = None,
    hidden_file_size: Optional[int] = None,
) -> Dict:
    """
    Store a stego-image and register its metadata.

    Args:
        stego_image_path:     Path to the generated stego-image.
        original_carrier_name: Name of the original carrier image.
        hidden_file_name:     Name of the hidden file (for display).
        hidden_file_size:     Size of the hidden file in bytes.

    Returns:
        Metadata dict for the stored image.
    """
    image_id = str(uuid.uuid4())[:8]
    dest_filename = f"{image_id}_{original_carrier_name}"

    # Ensure .png extension
    if not dest_filename.endswith(".png"):
        dest_filename = dest_filename.rsplit(".", 1)[0] + ".png"

    dest_path = settings.STEGO_DIR / dest_filename

    # Copy stego-image to storage
    shutil.copy2(stego_image_path, dest_path)

    # Get image info
    img_info = get_image_info(dest_path)

    # Create metadata entry for DB
    entry = {
        "id": image_id,
        "user_id": user_id,
        "vault_id": vault_id,
        "filename": dest_filename,
        "original_name": original_carrier_name,
        "path": str(dest_path),
        "resolution": img_info["resolution"],
        "width": img_info["width"],
        "height": img_info["height"],
        "file_size": img_info["file_size"],
        "file_size_bytes": dest_path.stat().st_size,
        "capacity": img_info["max_capacity"],
        "capacity_bytes": img_info["max_capacity_bytes"],
        "has_hidden_data": hidden_file_name is not None,
        "hidden_file_name": hidden_file_name,
        "hidden_file_size": format_size(hidden_file_size) if hidden_file_size else None,
        "hidden_file_size_bytes": hidden_file_size,
    }

    # Save to Supabase
    if supabase:
        res = supabase.table("images").insert(entry).execute()
        if res.data:
            return res.data[0]

    entry["created_at"] = datetime.now(timezone.utc).isoformat()
    return entry


def store_carrier_image(carrier_path: Path, user_id: str, vault_id: str, original_name: Optional[str] = None) -> Dict:
    """
    Store a carrier image (no hidden data) in the gallery.

    Args:
        carrier_path:   Path to the carrier image.
        user_id:        User ID.
        vault_id:       Vault ID.
        original_name:  Display name for the image.

    Returns:
        Metadata dict for the stored image.
    """
    image_id = str(uuid.uuid4())[:8]
    name = original_name or carrier_path.name
    dest_filename = f"{image_id}_{name}"

    if not dest_filename.endswith(".png"):
        dest_filename = dest_filename.rsplit(".", 1)[0] + ".png"

    dest_path = settings.CARRIER_DIR / dest_filename

    shutil.copy2(carrier_path, dest_path)
    img_info = get_image_info(dest_path)

    entry = {
        "id": image_id,
        "user_id": user_id,
        "vault_id": vault_id,
        "filename": dest_filename,
        "original_name": name,
        "path": str(dest_path),
        "resolution": img_info["resolution"],
        "width": img_info["width"],
        "height": img_info["height"],
        "file_size": img_info["file_size"],
        "file_size_bytes": dest_path.stat().st_size,
        "capacity": img_info["max_capacity"],
        "capacity_bytes": img_info["max_capacity_bytes"],
        "has_hidden_data": False,
        "hidden_file_name": None,
        "hidden_file_size": None,
        "hidden_file_size_bytes": None,
    }

    if supabase:
        res = supabase.table("images").insert(entry).execute()
        if res.data:
            return res.data[0]

    entry["created_at"] = datetime.now(timezone.utc).isoformat()
    return entry


# ──────────────────────────────────────────────
#  Retrieval Operations
# ──────────────────────────────────────────────
def get_image(image_id: str, user_id: str = None) -> Optional[Dict]:
    """Get metadata for a specific image by ID."""
    if not supabase: return None
    q = supabase.table("images").select("*").eq("id", image_id)
    if user_id:
        q = q.eq("user_id", user_id)
    res = q.execute()
    data = res.data
    return data[0] if data else None


def get_image_path(image_id: str, user_id: str = None) -> Optional[Path]:
    """Get the filesystem path for an image."""
    entry = get_image(image_id, user_id)
    if entry:
        path = Path(entry["path"])
        if path.exists():
            return path
    return None


def list_images(user_id: str, vault_id: str = None, has_hidden_data: Optional[bool] = None) -> List[Dict]:
    """
    List all images in the gallery for a given user.

    Args:
        user_id: Find images belonging to this user.
        vault_id: Optionally restrict to a specific vault.
        has_hidden_data: If set, filter by whether images contain hidden data.

    Returns:
        List of image metadata dicts, sorted by creation time (newest first).
    """
    if not supabase: return []
    
    q = supabase.table("images").select("*").eq("user_id", user_id).order("created_at", desc=True)
    if vault_id:
        q = q.eq("vault_id", vault_id)
    if has_hidden_data is not None:
        q = q.eq("has_hidden_data", has_hidden_data)
        
    res = q.execute()
    return res.data


def delete_image(image_id: str, user_id: str = None) -> bool:
    """Delete an image and its metadata."""
    if not supabase: return False
    
    entry = get_image(image_id, user_id)
    if not entry:
        return False

    # Delete file
    path = Path(entry["path"])
    if path.exists():
        path.unlink()

    # Remove from DB
    q = supabase.table("images").delete().eq("id", image_id)
    if user_id:
        q = q.eq("user_id", user_id)
    q.execute()

    return True


# ──────────────────────────────────────────────
#  Temporary File Management
# ──────────────────────────────────────────────
def save_temp_upload(content: bytes, filename: str) -> Path:
    """Save uploaded file content to temp staging area."""
    temp_path = settings.UPLOAD_DIR / f"{uuid.uuid4().hex[:8]}_{filename}"
    temp_path.write_bytes(content)
    return temp_path


def save_temp_extracted(content: bytes, filename: str) -> Path:
    """Save extracted file content for download."""
    extract_id = uuid.uuid4().hex[:8]
    temp_path = settings.EXTRACTED_DIR / f"{extract_id}_{filename}"
    temp_path.write_bytes(content)
    return temp_path, extract_id


def get_extracted_file(extract_id: str, filename: str) -> Optional[Path]:
    """Find an extracted file by its ID prefix."""
    for file in settings.EXTRACTED_DIR.iterdir():
        if file.name.startswith(extract_id):
            return file
    return None


def cleanup_temp(path: Path):
    """Remove a temporary file."""
    if path.exists():
        path.unlink()
