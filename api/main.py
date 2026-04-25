"""
Stego-Cloud API — FastAPI Backend
===================================
REST API that wraps the core steganography engine.

Endpoints:
    POST /api/upload-secret     — Encrypt + hide a file inside a carrier image
    POST /api/extract-secret    — Extract + decrypt a hidden file from a stego-image
    GET  /api/gallery           — List all images in the gallery
    GET  /api/capacity/{id}     — Check hiding capacity of an image
    POST /api/generate-carrier  — Generate a carrier image via AI
    GET  /api/images/{id}       — Serve an image file
    GET  /api/download/{id}/{f} — Download an extracted file
    DELETE /api/images/{id}     — Delete an image
    GET  /api/health            — Health check

Run:
    python -m api.main
    # or: uvicorn api.main:app --reload --port 8000
"""

import sys
import io
import os
import tempfile
import uuid
from pathlib import Path

# Fix Windows console encoding
if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    if sys.stdout.encoding != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if sys.stderr and hasattr(sys.stderr, 'reconfigure'):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Query, Depends, Header, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
import jwt
from datetime import datetime, timedelta

from api.config import settings
from api import storage
from api.models import (
    UploadResponse, ExtractResponse, GalleryResponse,
    CapacityResponse, CarrierGenerateResponse, ErrorResponse,
    HealthResponse, ImageInfo
)
from core import crypto_engine, stego_engine, utils, __version__
from core.image_provider import generate_carrier_image, get_or_create_carrier


# ──────────────────────────────────────────────
#  App Initialization
# ──────────────────────────────────────────────
app = FastAPI(
    title="Stego-Cloud API",
    description=(
        "Secure, invisible cloud storage using LSB steganography "
        "and AES-256 encryption. Upload files to hide them inside "
        "innocent-looking images."
    ),
    version=__version__,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS — allow frontend connections
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ──────────────────────────────────────────────
#  Helper: Build ImageInfo from metadata
# ──────────────────────────────────────────────
def _build_image_info(entry: dict) -> ImageInfo:
    """Convert a storage metadata entry to an API ImageInfo response."""
    base_url = f"/api/images/{entry['id']}"
    return ImageInfo(
        id=entry["id"],
        filename=entry["filename"],
        original_name=entry["original_name"],
        resolution=entry["resolution"],
        file_size=entry["file_size"],
        capacity=entry["capacity"],
        has_hidden_data=entry["has_hidden_data"],
        hidden_file_name=entry.get("hidden_file_name"),
        hidden_file_size=entry.get("hidden_file_size"),
        created_at=entry["created_at"],
        thumbnail_url=base_url,
        full_url=base_url,
    )


# ──────────────────────────────────────────────
#  Authentication & Security (Panic Mode)
# ──────────────────────────────────────────────
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/login", auto_error=False)

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(hours=24)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm="HS256")

async def get_current_user(token: str = Depends(oauth2_scheme)):
    """Validates Supabase token against Supabase API."""
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    from api.db import supabase
    if not supabase:
        # Fallback for dev if supabase is missing
        return "local_dev_user"
    res = supabase.auth.get_user(token)
    if not res.user:
        raise HTTPException(status_code=401, detail="Invalid token")
    return res.user.id

async def get_current_mode(x_vault_token: str = Header(None), token_query: str = Query(None, alias="token")):
    token = x_vault_token or token_query
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        # This token is the LOCAL vault token for real/panic modes, not Supabase token
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
        mode = payload.get("mode")
        if mode not in ["real", "panic"]:
            raise HTTPException(status_code=401, detail="Invalid vault token mode")
        # Let's return the whole payload to access vault_id
        return payload
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Could not validate vault credentials")

class LoginRequest(BaseModel):
    password: str

class SetupVaultRequest(BaseModel):
    password: str

class CreateSharedVaultRequest(BaseModel):
    join_password: str

class JoinSharedVaultRequest(BaseModel):
    join_password: str

from fastapi import Header

@app.post("/api/vault/login", tags=["Auth"])
async def vault_login(req: LoginRequest, user_id: str = Depends(get_current_user)):
    """Dual-password check in endpoint. We check DB for the user's password."""
    from api.db import supabase
    if supabase:
        # Check users table for password
        res = supabase.table("users").select("checkin_password_hash").eq("id", user_id).execute()
        
        # Determine mode
        is_real = res.data and res.data[0].get("checkin_password_hash") == req.password
        # Also allow global gallery password for dev
        if not is_real and req.password == settings.GALLERY_PASSWORD:
            is_real = True

        mode = "real" if is_real else "panic"
        
        # Find the user's vault ID (usually their private vault)
        vault_res = supabase.table("vaults").select("id").eq("owner_id", user_id).eq("is_shared", False).limit(1).execute()
        vault_id = vault_res.data[0]['id'] if vault_res.data else user_id
        
        token = create_access_token({"mode": mode, "user_id": user_id, "vault_id": vault_id})
        return {"access_token": token, "token_type": "bearer", "mode": mode}
    
    # Fallback when Supabase fails:
    if req.password == settings.GALLERY_PASSWORD:
        token = create_access_token({"mode": "real", "vault_id": "default"})
        return {"access_token": token, "token_type": "bearer", "mode": "real"}
    else:
        token = create_access_token({"mode": "panic", "vault_id": "default"})
        return {"access_token": token, "token_type": "bearer", "mode": "panic"}

@app.post("/api/vault/setup", tags=["Auth"])
async def setup_vault(req: SetupVaultRequest, user_id: str = Depends(get_current_user)):
    from api.db import supabase
    if not supabase: raise HTTPException(status_code=500, detail="DB Error")
    supabase.table("users").update({"checkin_password_hash": req.password}).eq("id", user_id).execute()
    
    vault_res = supabase.table("vaults").select("id").eq("owner_id", user_id).eq("is_shared", False).limit(1).execute()
    vault_id = vault_res.data[0]['id'] if vault_res.data else user_id
    token = create_access_token({"mode": "real", "user_id": user_id, "vault_id": vault_id})
    return {"success": True, "access_token": token, "mode": "real", "token_type": "bearer"}

@app.get("/api/vault/status", tags=["Auth"])
async def vault_status(user_id: str = Depends(get_current_user)):
    from api.db import supabase
    if not supabase: raise HTTPException(status_code=500, detail="DB Error")
    res = supabase.table("users").select("checkin_password_hash").eq("id", user_id).execute()
    has_password = res.data and res.data[0].get("checkin_password_hash") is not None
    return {"has_password": has_password}

@app.post("/api/seed-decoy", tags=["Gallery"])
async def seed_decoy(user_id: str = Depends(get_current_user), vault_token_payload: dict = Depends(get_current_mode)):
    mode = vault_token_payload.get("mode")
    vault_id = vault_token_payload.get("vault_id", user_id)
    """Seed the gallery with 3 innocent photos for the decoy gallery."""
    if mode != "real":
        # Panic mode acts like this endpoint doesn't exist
        raise HTTPException(status_code=404, detail="Not Found")
    
    from core.image_provider import download_carrier_pack
    # Ensure carrier directory exists
    settings.CARRIER_DIR.mkdir(parents=True, exist_ok=True)
    
    paths = download_carrier_pack(count=3, output_dir=settings.CARRIER_DIR)
    for p in paths:
        storage.store_carrier_image(p, original_name=p.name, user_id=user_id, vault_id=vault_id)
    return {"success": True, "message": f"Seeded {len(paths)} decoy photos."}


# ──────────────────────────────────────────────
#  Health Check
# ──────────────────────────────────────────────
@app.get("/api/health", response_model=HealthResponse, tags=["System"])
async def health_check():
    """Check if the API is running."""
    return HealthResponse(
        status="healthy",
        version=__version__,
        sprint="Sprint 2",
    )


# ──────────────────────────────────────────────
#  Upload Secret (Encode Pipeline)
# ──────────────────────────────────────────────
@app.post("/api/upload-secret", response_model=UploadResponse, tags=["Steganography"])
async def upload_secret(
    secret_file: UploadFile = File(..., description="The secret file to hide"),
    password: str = Form(..., description="Encryption password"),
    carrier_image: UploadFile = File(None, description="Carrier image (optional — AI generates one if omitted)"),
    carrier_description: str = Form("beautiful nature landscape photography", description="AI image description (used if no carrier provided)"),
    user_id: str = Depends(get_current_user),
    vault_token_payload: dict = Depends(get_current_mode),
):
    """
    Hide a secret file inside a carrier image.

    Pipeline: Secret File → AES-256-GCM Encrypt → LSB Encode → Store

    If no carrier image is provided, one is automatically generated using Gemini AI.
    """
    try:
        mode = vault_token_payload.get("mode")
        vault_id = vault_token_payload.get("vault_id", user_id)
        # Panic mode illusion
        if mode != "real":
            raise HTTPException(status_code=404, detail="Not Found")

        # 1. Read secret file
        secret_data = await secret_file.read()
        if not secret_data:
            raise HTTPException(status_code=400, detail="Secret file is empty.")

        if len(secret_data) > settings.MAX_FILE_SIZE:
            raise HTTPException(
                status_code=413,
                detail=f"File too large. Maximum: {utils.format_size(settings.MAX_FILE_SIZE)}"
            )

        secret_filename = secret_file.filename or "secret_file"

        # 2. Encrypt the secret data
        encrypted = crypto_engine.encrypt(secret_data, password)

        # 3. Get or create carrier image
        if carrier_image and carrier_image.filename:
            # User provided a carrier image
            carrier_data = await carrier_image.read()
            carrier_temp = storage.save_temp_upload(carrier_data, carrier_image.filename)
            carrier_name = carrier_image.filename
        else:
            # Generate carrier via AI (with fallback chain)
            carrier_temp = get_or_create_carrier(
                required_bytes=len(encrypted),
                description=carrier_description,
                output_dir=settings.CARRIER_DIR,
            )
            carrier_name = carrier_temp.name

        # 4. Validate capacity
        validation = utils.validate_capacity(carrier_temp, len(encrypted))
        if not validation["can_fit"]:
            storage.cleanup_temp(carrier_temp)
            raise HTTPException(
                status_code=400,
                detail=f"Carrier image too small. {validation['message']}"
            )

        # 5. Encode (hide data in image)
        stego_filename = f"stego_{uuid.uuid4().hex[:8]}.png"
        stego_temp = settings.UPLOAD_DIR / stego_filename
        stego_engine.encode(carrier_temp, encrypted, stego_temp)

        # 6. Store the stego-image
        entry = storage.store_stego_image(
            stego_image_path=stego_temp,
            original_carrier_name=carrier_name,
            user_id=user_id,
            vault_id=vault_id,
            hidden_file_name=secret_filename,
            hidden_file_size=len(secret_data),
        )

        # 7. Cleanup temp files
        storage.cleanup_temp(stego_temp)
        if carrier_image and carrier_image.filename:
            storage.cleanup_temp(carrier_temp)

        return UploadResponse(
            success=True,
            message=f"Secret file '{secret_filename}' has been hidden inside '{carrier_name}'.",
            image=_build_image_info(entry),
        )

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


# ──────────────────────────────────────────────
#  Extract Secret (Decode Pipeline)
# ──────────────────────────────────────────────
@app.post("/api/extract-secret", response_model=ExtractResponse, tags=["Steganography"])
async def extract_secret(
    image_id: str = Form(None, description="ID of a stored stego-image"),
    stego_image: UploadFile = File(None, description="Or upload a stego-image directly"),
    password: str = Form(..., description="Decryption password"),
    output_filename: str = Form(None, description="Name for the extracted file"),
    vault_token_payload: dict = Depends(get_current_mode),
):
    mode = vault_token_payload.get("mode")
    """
    Extract a hidden file from a stego-image.

    Pipeline: Stego-Image → LSB Decode → AES-256-GCM Decrypt → Download

    Provide either an `image_id` (for stored images) or upload a `stego_image` directly.
    """
    try:
        if mode != "real":
            raise HTTPException(status_code=404, detail="Not Found")

        # 1. Get the stego-image
        if image_id:
            image_path = storage.get_image_path(image_id)
            if not image_path:
                raise HTTPException(status_code=404, detail=f"Image '{image_id}' not found.")

            # Try to get the hidden file name from metadata
            image_meta = storage.get_image(image_id)
            default_name = image_meta.get("hidden_file_name", "extracted_file") if image_meta else "extracted_file"

        elif stego_image and stego_image.filename:
            stego_data = await stego_image.read()
            image_path = storage.save_temp_upload(stego_data, stego_image.filename)
            default_name = "extracted_file"
        else:
            raise HTTPException(
                status_code=400,
                detail="Provide either 'image_id' or upload a 'stego_image'."
            )

        # 2. Decode (extract hidden bits)
        encrypted_data = stego_engine.decode(image_path)

        # 3. Decrypt
        try:
            decrypted = crypto_engine.decrypt(encrypted_data, password)
        except ValueError:
            raise HTTPException(
                status_code=401,
                detail="Decryption failed. Wrong password or the image doesn't contain hidden data."
            )

        # 4. Save extracted file
        final_name = output_filename or default_name
        result_path, extract_id = storage.save_temp_extracted(decrypted, final_name)

        # 5. Cleanup temp stego if uploaded
        if stego_image and stego_image.filename and not image_id:
            storage.cleanup_temp(image_path)
        elif image_id:
            storage.delete_image(image_id)
            if image_path and "dl_" in image_path.name:
                storage.cleanup_temp(image_path)

        return ExtractResponse(
            success=True,
            message=f"Successfully extracted '{final_name}'.",
            extracted_file=final_name,
            file_size=utils.format_size(len(decrypted)),
            download_url=f"/api/download/{extract_id}/{final_name}",
        )

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


# ──────────────────────────────────────────────
#  Gallery — List Images
# ──────────────────────────────────────────────
@app.get("/api/gallery", response_model=GalleryResponse, tags=["Gallery"])
async def get_gallery(
    filter: str = Query(None, description="Filter: 'hidden' (stego only), 'clean' (carriers only), or None (all)"),
    user_id: str = Depends(get_current_user),
    vault_token_payload: dict = Depends(get_current_mode),
):
    mode = vault_token_payload.get("mode")
    vault_id = vault_token_payload.get("vault_id", user_id)
    """
    List all images in the gallery.

    The gallery displays stego-images as normal photos — providing plausible deniability.
    """
    has_hidden = None
    if filter == "hidden":
        has_hidden = True
    elif filter == "clean":
        has_hidden = False

    # Force clean images only if in panic mode
    if mode == "panic":
        has_hidden = False

    images = storage.list_images(user_id=user_id, vault_id=vault_id, has_hidden_data=has_hidden)
    
    # Strictly mask any remaining traces for panic mode
    if mode == "panic":
        for img in images:
            img["has_hidden_data"] = False
            img["hidden_file_name"] = None
            img["hidden_file_size"] = None

    image_infos = [_build_image_info(img) for img in images]

    return GalleryResponse(
        success=True,
        total=len(image_infos),
        images=image_infos,
    )


# ──────────────────────────────────────────────
#  Capacity Check
# ──────────────────────────────────────────────
@app.get("/api/capacity/{image_id}", response_model=CapacityResponse, tags=["Gallery"])
async def check_capacity(image_id: str, vault_token_payload: dict = Depends(get_current_mode)):
    """Check the hiding capacity of a stored image."""
    mode = vault_token_payload.get("mode")
    if mode != "real":
        raise HTTPException(status_code=404, detail="Not Found")
    
    image_path = storage.get_image_path(image_id)
    if not image_path:
        raise HTTPException(status_code=404, detail=f"Image '{image_id}' not found.")

    img_info = utils.get_image_info(image_path)
    if "dl_" in image_path.name:
        storage.cleanup_temp(image_path)

    return CapacityResponse(
        success=True,
        image_id=image_id,
        resolution=img_info["resolution"],
        total_pixels=img_info["total_pixels"],
        max_capacity=img_info["max_capacity"],
        max_capacity_bytes=img_info["max_capacity_bytes"],
    )


# ──────────────────────────────────────────────
#  Generate Carrier Image
# ──────────────────────────────────────────────
@app.post("/api/generate-carrier", response_model=CarrierGenerateResponse, tags=["AI"])
async def generate_carrier(
    description: str = Form("beautiful nature landscape photography", description="Description of the image to generate"),
    user_id: str = Depends(get_current_user),
    vault_token_payload: dict = Depends(get_current_mode),
):
    mode = vault_token_payload.get("mode")
    vault_id = vault_token_payload.get("vault_id", user_id)
    """
    Generate a carrier image using Gemini AI.

    The generated image can be used as a carrier for hiding files.
    Falls back to Unsplash photos or procedural generation if AI is unavailable.
    """
    try:
        if mode != "real":
            raise HTTPException(status_code=404, detail="Not Found")

        carrier_path = generate_carrier_image(
            description=description,
            output_dir=settings.CARRIER_DIR,
        )

        entry = storage.store_carrier_image(carrier_path, original_name=carrier_path.name, user_id=user_id, vault_id=vault_id)

        return CarrierGenerateResponse(
            success=True,
            message=f"Carrier image generated: {description}",
            image=_build_image_info(entry),
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate carrier: {str(e)}")


# ──────────────────────────────────────────────
#  Serve Images
# ──────────────────────────────────────────────
@app.get("/api/images/{image_id}", tags=["Gallery"])
async def get_image_file(image_id: str, background_tasks: BackgroundTasks, vault_token_payload: dict = Depends(get_current_mode)):
    """Serve an image file (for gallery display)."""
    mode = vault_token_payload.get("mode")
    # Allow panic mode to view innocent images
    image_path = storage.get_image_path(image_id)
    if not image_path:
        raise HTTPException(status_code=404, detail=f"Image '{image_id}' not found.")

    if "dl_" in image_path.name:
        background_tasks.add_task(storage.cleanup_temp, image_path)

    return FileResponse(
        path=image_path,
        media_type="image/png",
        filename=image_path.name,
    )


# ──────────────────────────────────────────────
#  Download Extracted File
# ──────────────────────────────────────────────
@app.get("/api/download/{extract_id}/{filename}", tags=["Steganography"])
async def download_extracted(extract_id: str, filename: str, vault_token_payload: dict = Depends(get_current_mode)):
    """Download an extracted file."""
    mode = vault_token_payload.get("mode")
    if mode != "real":
        raise HTTPException(status_code=404, detail="Not Found")
    
    file_path = storage.get_extracted_file(extract_id, filename)
    if not file_path:
        raise HTTPException(status_code=404, detail="Extracted file not found or expired.")

    return FileResponse(
        path=file_path,
        filename=filename,
        media_type="application/octet-stream",
    )


# ──────────────────────────────────────────────
#  Delete Image
# ──────────────────────────────────────────────
@app.delete("/api/images/{image_id}", tags=["Gallery"])
async def delete_image(image_id: str, vault_token_payload: dict = Depends(get_current_mode)):
    """Delete an image from the gallery."""
    mode = vault_token_payload.get("mode")
    # Allowed in both real and panic modes to maintain the facade
    success = storage.delete_image(image_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Image '{image_id}' not found.")

    return {"success": True, "message": f"Image '{image_id}' deleted."}


# ──────────────────────────────────────────────
#  Upload Carrier Image (without hiding data)
# ──────────────────────────────────────────────
@app.post("/api/upload-carrier", tags=["Gallery"])
async def upload_carrier(
    image: UploadFile = File(..., description="Carrier image to add to gallery"),
    user_id: str = Depends(get_current_user),
    vault_token_payload: dict = Depends(get_current_mode),
):
    """Upload a carrier image to the gallery (without hiding any data)."""
    try:
        mode = vault_token_payload.get("mode")
        vault_id = vault_token_payload.get("vault_id", user_id)
        # Allow panic mode to upload cleanly to maintain illusion!
        image_data = await image.read()
        temp_path = storage.save_temp_upload(image_data, image.filename or "upload.png")

        entry = storage.store_carrier_image(temp_path, original_name=image.filename, user_id=user_id, vault_id=vault_id)
        storage.cleanup_temp(temp_path)

        return {
            "success": True,
            "message": f"Image '{image.filename}' added to gallery.",
            "image": _build_image_info(entry),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ──────────────────────────────────────────────
#  Run Server
# ──────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    print("=" * 60)
    print("🚀 Stego-Cloud API Server")
    print(f"   Version: {__version__}")
    print(f"   Sprint:  2 — FastAPI Backend")
    print(f"   Docs:    http://localhost:{settings.PORT}/docs")
    print(f"   ReDoc:   http://localhost:{settings.PORT}/redoc")
    print("=" * 60)
    uvicorn.run(
        "api.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
