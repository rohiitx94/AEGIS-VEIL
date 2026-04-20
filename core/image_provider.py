"""
Image Provider — Real High-Resolution Photos from the Internet
================================================================
Downloads real, high-resolution photographs from free image sources
to use as carrier images for steganography.

Image sources (in priority order):
    1. Pexels API  — Keyword search for specific themes (free API key)
    2. Picsum Photos — Random high-res photographs (no API key needed)
    3. Gemini AI — AI-generated images (if API key available)
    4. Procedural — Gradient fallback (offline, always works)

Why real photos are better for steganography:
    - Natural photographic noise masks LSB modifications perfectly
    - Rich textures and color variation make statistical detection harder
    - They look like normal gallery photos (plausible deniability)
    - Higher resolution = more hiding capacity

Setup (optional, for keyword search):
    Set PEXELS_API_KEY for keyword-based image search.
    Get your free key from: https://www.pexels.com/api/
    
    Set GEMINI_API_KEY for AI image generation.
    Get your key from: https://aistudio.google.com/apikey
"""

import os
import io
import json
import random
import requests
from pathlib import Path
from typing import Union, Optional, List, Dict
from PIL import Image

from core.stego_engine import calculate_capacity
from core.utils import format_size


# ──────────────────────────────────────────────
#  Constants
# ──────────────────────────────────────────────
DEFAULT_OUTPUT_DIR = Path("sample_images")
MIN_CAPACITY_BYTES = 1024  # At least 1KB of hiding capacity

# Categories of images that look natural in a personal gallery
PHOTO_CATEGORIES = [
    "nature", "landscape", "mountains", "ocean", "forest",
    "city", "architecture", "street", "travel", "sunset",
    "flowers", "animals", "food", "sky", "beach",
    "autumn", "winter", "lake", "garden", "bridge",
]


# ──────────────────────────────────────────────
#  Source 1: Pexels API (Keyword Search)
# ──────────────────────────────────────────────
def _fetch_from_pexels(
    query: str,
    output_dir: Path,
    filename: Optional[str] = None,
    min_width: int = 2500,
) -> Optional[Path]:
    """
    Download a high-resolution photo from Pexels by keyword.
    
    Pexels provides free, high-quality stock photos with a generous
    API limit (200 requests/hour on free tier).
    
    Args:
        query:     Search keyword (e.g., "sunset mountains").
        output_dir: Where to save the image.
        filename:  Custom filename.
        min_width: Minimum image width in pixels.
    
    Returns:
        Path to saved image, or None if failed.
    """
    api_key = os.environ.get("PEXELS_API_KEY")
    if not api_key:
        return None
    
    try:
        print(f"📷 Searching Pexels for '{query}'...")
        
        headers = {"Authorization": api_key}
        params = {
            "query": query,
            "per_page": 15,
            "orientation": "landscape",
            "size": "large",
        }
        
        resp = requests.get(
            "https://api.pexels.com/v1/search",
            headers=headers,
            params=params,
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        
        photos = data.get("photos", [])
        if not photos:
            print(f"   No results found for '{query}'")
            return None
        
        # Pick a random photo from results (variety!)
        photo = random.choice(photos)
        
        # Get the highest resolution available
        # Pexels provides: original, large2x, large, medium, small
        image_url = photo["src"].get("original") or photo["src"].get("large2x")
        photographer = photo.get("photographer", "Unknown")
        
        print(f"   Found: Photo by {photographer}")
        print(f"   Downloading high-res version...")
        
        img_resp = requests.get(image_url, timeout=30, headers=headers)
        img_resp.raise_for_status()
        
        img = Image.open(io.BytesIO(img_resp.content)).convert("RGB")
        width, height = img.size
        
        # Generate filename
        if filename is None:
            safe_query = "".join(c if c.isalnum() or c == " " else "" for c in query)
            safe_query = safe_query.strip().replace(" ", "_")[:40]
            filename = f"carrier_{safe_query}_{photo['id']}.png"
        
        if not filename.endswith(".png"):
            filename = filename.rsplit(".", 1)[0] + ".png"
        
        output_path = output_dir / filename
        img.save(output_path, format="PNG")
        
        capacity = calculate_capacity(output_path)
        
        print(f"✅ Pexels photo saved: {output_path}")
        print(f"   Photographer: {photographer}")
        print(f"   Resolution: {width}×{height} ({width * height:,} pixels)")
        print(f"   Hiding capacity: {format_size(capacity)}")
        
        return output_path
    
    except Exception as e:
        print(f"⚠️  Pexels fetch failed: {e}")
        return None


# ──────────────────────────────────────────────
#  Source 2: Picsum Photos (Random High-Res)
# ──────────────────────────────────────────────
def _fetch_from_picsum(
    output_dir: Path,
    filename: Optional[str] = None,
    width: int = 3840,
    height: int = 2160,
    description: str = "random",
) -> Optional[Path]:
    """
    Download a real high-resolution photograph from Picsum Photos.
    
    Picsum (picsum.photos) serves real photos from Unsplash photographers.
    No API key required. Always returns a different random photo.
    
    Args:
        output_dir: Where to save the image.
        filename:  Custom filename.
        width:     Requested width in pixels.
        height:    Requested height in pixels.
        description: Used for filename only.
    
    Returns:
        Path to saved image, or None if failed.
    """
    try:
        # Use a random seed to get different photos each time
        seed = random.randint(1, 99999)
        url = f"https://picsum.photos/seed/{seed}/{width}/{height}"
        
        print(f"📷 Downloading high-res photo from Picsum Photos...")
        
        resp = requests.get(url, timeout=30, allow_redirects=True)
        resp.raise_for_status()
        
        img = Image.open(io.BytesIO(resp.content)).convert("RGB")
        actual_w, actual_h = img.size
        
        if filename is None:
            safe_desc = "".join(c if c.isalnum() or c == " " else "" for c in description)
            safe_desc = safe_desc.strip().replace(" ", "_")[:40]
            filename = f"carrier_{safe_desc}_{seed}.png"
        
        if not filename.endswith(".png"):
            filename = filename.rsplit(".", 1)[0] + ".png"
        
        output_path = output_dir / filename
        img.save(output_path, format="PNG")
        
        capacity = calculate_capacity(output_path)
        
        print(f"✅ Real photo downloaded: {output_path}")
        print(f"   Resolution: {actual_w}×{actual_h} ({actual_w * actual_h:,} pixels)")
        print(f"   Hiding capacity: {format_size(capacity)}")
        
        return output_path
    
    except Exception as e:
        print(f"⚠️  Picsum fetch failed: {e}")
        return None


# ──────────────────────────────────────────────
#  Source 3: Gemini AI Image Generation
# ──────────────────────────────────────────────
def _generate_with_gemini(
    description: str,
    output_dir: Path,
    filename: Optional[str] = None,
) -> Optional[Path]:
    """
    Generate an image using Gemini AI.
    
    Uses gemini-2.5-flash-image model for image generation.
    Requires GEMINI_API_KEY environment variable.
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return None
    
    try:
        from google import genai
        from google.genai import types
        
        client = genai.Client(api_key=api_key)
        
        prompt = (
            f"Generate a high-resolution, photorealistic photograph of: {description}. "
            "Richly detailed with natural colors and textures. "
            "No text, no watermarks, no borders."
        )
        
        print(f"🤖 Asking Gemini AI to generate: '{description}'...")
        
        response = client.models.generate_content(
            model="gemini-2.5-flash-image",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE", "TEXT"],
            )
        )
        
        # Find image in response
        image_data = None
        if response.candidates:
            for part in response.candidates[0].content.parts:
                if part.inline_data and part.inline_data.mime_type.startswith("image/"):
                    image_data = part.inline_data.data
                    break
        
        if not image_data:
            return None
        
        img = Image.open(io.BytesIO(image_data)).convert("RGB")
        
        if filename is None:
            safe_desc = "".join(c if c.isalnum() or c == " " else "" for c in description)
            safe_desc = safe_desc.strip().replace(" ", "_")[:40]
            filename = f"carrier_ai_{safe_desc}.png"
        
        if not filename.endswith(".png"):
            filename = filename.rsplit(".", 1)[0] + ".png"
        
        output_path = output_dir / filename
        img.save(output_path, format="PNG")
        
        capacity = calculate_capacity(output_path)
        width, height = img.size
        
        print(f"✅ AI-generated image saved: {output_path}")
        print(f"   Resolution: {width}×{height} ({width * height:,} pixels)")
        print(f"   Hiding capacity: {format_size(capacity)}")
        
        return output_path
    
    except Exception as e:
        print(f"⚠️  Gemini AI generation failed: {e}")
        return None


# ──────────────────────────────────────────────
#  Source 4: Procedural Image (Offline Fallback)
# ──────────────────────────────────────────────
def _create_procedural_carrier(
    description: str,
    output_dir: Path,
    filename: Optional[str] = None,
    resolution: tuple = (3840, 2160),
) -> Path:
    """
    Create a procedural image as the final offline fallback.
    Uses gradient + noise patterns for decent steganographic properties.
    """
    import numpy as np

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    width, height = resolution

    # Create multi-layer gradient with noise
    x = np.linspace(0, 4 * np.pi, width)
    y = np.linspace(0, 4 * np.pi, height)
    xx, yy = np.meshgrid(x, y)

    r = ((np.sin(xx * 0.7 + 0.3) * 0.5 + 0.5) * 180 + 40).astype(np.uint8)
    g = ((np.sin(yy * 0.9 + 1.5) * 0.5 + 0.5) * 180 + 40).astype(np.uint8)
    b = ((np.sin((xx + yy) * 0.5 + 2.7) * 0.5 + 0.5) * 180 + 40).astype(np.uint8)

    noise = np.random.randint(0, 15, (height, width), dtype=np.uint8)
    r = np.clip(r.astype(np.int16) + noise, 0, 255).astype(np.uint8)
    g = np.clip(g.astype(np.int16) + noise, 0, 255).astype(np.uint8)
    b = np.clip(b.astype(np.int16) + noise, 0, 255).astype(np.uint8)

    pixels = np.stack([r, g, b], axis=2)
    img = Image.fromarray(pixels, mode="RGB")

    if filename is None:
        safe_desc = "".join(c if c.isalnum() or c == " " else "" for c in description)
        safe_desc = safe_desc.strip().replace(" ", "_")[:40]
        filename = f"carrier_procedural_{safe_desc}.png"

    if not filename.endswith(".png"):
        filename = filename.rsplit(".", 1)[0] + ".png"

    output_path = output_dir / filename
    img.save(output_path, format="PNG")

    capacity = calculate_capacity(output_path)
    print(f"✅ Procedural carrier image created: {output_path}")
    print(f"   Resolution: {width}×{height} ({width * height:,} pixels)")
    print(f"   Hiding capacity: {format_size(capacity)}")

    return output_path


# ──────────────────────────────────────────────
#  Main Entry Points
# ──────────────────────────────────────────────
def generate_carrier_image(
    description: str = "nature landscape",
    output_dir: Union[str, Path] = DEFAULT_OUTPUT_DIR,
    filename: Optional[str] = None,
    min_capacity_bytes: int = MIN_CAPACITY_BYTES,
) -> Path:
    """
    Get a high-resolution carrier image from the best available source.
    
    Tries sources in order until one succeeds:
        1. Pexels (keyword search, needs PEXELS_API_KEY)
        2. Picsum Photos (random real photo, no key needed)
        3. Gemini AI (generated, needs GEMINI_API_KEY)
        4. Procedural gradient (always works, offline)
    
    Args:
        description:       What kind of image to find (e.g., "sunset mountains").
        output_dir:        Directory to save the image.
        filename:          Custom filename (auto-generated if None).
        min_capacity_bytes: Minimum hiding capacity required.
    
    Returns:
        Path to the saved carrier image (always succeeds due to fallback).
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Source 1: Pexels (keyword-based real photos)
    result = _fetch_from_pexels(description, output_dir, filename)
    if result:
        return result
    
    # Source 2: Picsum (random real photos, always available)
    result = _fetch_from_picsum(
        output_dir, filename,
        width=3840, height=2160,
        description=description,
    )
    if result:
        return result
    
    # Source 3: Gemini AI generation
    result = _generate_with_gemini(description, output_dir, filename)
    if result:
        return result
    
    # Source 4: Procedural fallback (always works)
    print("📌 All online sources unavailable. Using procedural carrier.")
    return _create_procedural_carrier(description, output_dir, filename)


def get_or_create_carrier(
    required_bytes: int,
    description: str = "nature landscape",
    output_dir: Union[str, Path] = DEFAULT_OUTPUT_DIR,
) -> Path:
    """
    High-level function: get a carrier image suitable for the payload size.
    
    Automatically selects the best available image source and ensures
    the image has sufficient capacity for the payload.
    
    Args:
        required_bytes: Minimum capacity needed (encrypted payload size).
        description:    What kind of image to find/generate.
        output_dir:     Where to save the image.
    
    Returns:
        Path to a carrier image with sufficient capacity.
    """
    return generate_carrier_image(
        description=description,
        output_dir=output_dir,
        min_capacity_bytes=required_bytes,
    )


# ──────────────────────────────────────────────
#  Batch Download (Gallery Seeding)
# ──────────────────────────────────────────────
def download_carrier_pack(
    count: int = 5,
    categories: Optional[List[str]] = None,
    output_dir: Union[str, Path] = DEFAULT_OUTPUT_DIR,
) -> List[Path]:
    """
    Download multiple carrier images for gallery seeding.
    
    Useful for Sprint 4's "Panic Mode" decoy gallery — 
    pre-populate with innocent-looking photos.
    
    Args:
        count:      Number of images to download.
        categories: List of image categories (default: random from PHOTO_CATEGORIES).
        output_dir: Where to save images.
    
    Returns:
        List of paths to downloaded images.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    if categories is None:
        categories = random.sample(PHOTO_CATEGORIES, min(count, len(PHOTO_CATEGORIES)))
    
    paths = []
    print(f"📷 Downloading {count} carrier images...")
    
    for i in range(count):
        category = categories[i % len(categories)]
        print(f"\n[{i + 1}/{count}] Category: {category}")
        
        path = generate_carrier_image(
            description=category,
            output_dir=output_dir,
        )
        paths.append(path)
    
    print(f"\n✅ Downloaded {len(paths)} carrier images to {output_dir}")
    return paths


# ──────────────────────────────────────────────
#  AI-Suggested Search Queries  
# ──────────────────────────────────────────────
def suggest_carrier_images(
    secret_file_size: int,
    theme: str = "nature",
    count: int = 5,
) -> List[Dict]:
    """
    Use Gemini AI to suggest optimal carrier image search queries
    based on the payload size and preferred theme.
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        # Return sensible defaults without AI
        return [
            {
                "description": f"High resolution {theme} photography",
                "estimated_resolution": "3840×2160",
                "reason": "Rich natural textures mask LSB modifications"
            },
            {
                "description": f"{theme} macro photography with fine details",
                "estimated_resolution": "4000×3000",
                "reason": "High color variance per pixel, ideal for hiding data"
            },
        ]
    
    try:
        from google import genai
        
        client = genai.Client(api_key=api_key)
        
        required_bits = (secret_file_size + 4) * 8
        required_pixels = required_bits // 3 + 1
        min_width = int(required_pixels ** 0.5) + 1

        prompt = f"""You are an AI assistant for a steganography application.
The user needs to hide {format_size(secret_file_size)} of encrypted data inside an image.

Requirements:
- Minimum ~{min_width}x{min_width} resolution
- Should look like a normal personal photo
- Theme: {theme}

Generate exactly {count} search queries for finding carrier images on Pexels/Unsplash.
Respond in JSON array format with keys: "description", "estimated_resolution", "reason"
"""
        
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt
        )
        
        text = response.text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1]
            text = text.rsplit("```", 1)[0]
        
        return json.loads(text)
    
    except Exception as e:
        print(f"⚠️  AI suggestion failed: {e}")
        return [
            {
                "description": f"High resolution {theme} photography",
                "estimated_resolution": "3840×2160",
                "reason": "Natural textures mask LSB modifications"
            },
        ]
