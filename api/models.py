"""
API Models — Pydantic Request/Response Schemas
===============================================
Defines the data shapes for all API endpoints.
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


# ──────────────────────────────────────────────
#  Response Models
# ──────────────────────────────────────────────
class ImageInfo(BaseModel):
    """Information about a stored stego-image."""
    id: str = Field(..., description="Unique image identifier")
    filename: str = Field(..., description="Display filename")
    original_name: str = Field(..., description="Original carrier image name")
    resolution: str = Field(..., description="Image resolution (e.g., '3840×2160')")
    file_size: str = Field(..., description="Human-readable file size")
    capacity: str = Field(..., description="Hiding capacity")
    has_hidden_data: bool = Field(..., description="Whether this image contains hidden data")
    hidden_file_name: Optional[str] = Field(None, description="Name of the hidden file")
    hidden_file_size: Optional[str] = Field(None, description="Size of the hidden file")
    created_at: str = Field(..., description="When the image was stored")
    thumbnail_url: str = Field(..., description="URL to image thumbnail")
    full_url: str = Field(..., description="URL to full-size image")


class UploadResponse(BaseModel):
    """Response after successfully hiding a file."""
    success: bool = True
    message: str
    image: ImageInfo


class ExtractResponse(BaseModel):
    """Response after extracting a hidden file."""
    success: bool = True
    message: str
    extracted_file: str = Field(..., description="Name of the extracted file")
    file_size: str = Field(..., description="Size of extracted file")
    download_url: str = Field(..., description="URL to download the extracted file")


class GalleryResponse(BaseModel):
    """Response listing all images in the gallery."""
    success: bool = True
    total: int
    images: List[ImageInfo]


class CapacityResponse(BaseModel):
    """Response with capacity information for an image."""
    success: bool = True
    image_id: str
    resolution: str
    total_pixels: int
    max_capacity: str
    max_capacity_bytes: int


class CarrierGenerateResponse(BaseModel):
    """Response after generating a carrier image."""
    success: bool = True
    message: str
    image: ImageInfo


class ErrorResponse(BaseModel):
    """Error response."""
    success: bool = False
    error: str
    detail: Optional[str] = None


class HealthResponse(BaseModel):
    """Health check response."""
    status: str = "healthy"
    version: str
    sprint: str = "Sprint 2"
