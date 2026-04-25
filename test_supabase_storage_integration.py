"""
Integration test: Supabase Storage pipeline
Tests: upload carrier → gallery list → serve image → delete
"""
from fastapi.testclient import TestClient
from api.main import app, get_current_user
from api.db import supabase
import io

client = TestClient(app)

USER_ID = "a383e13f-38f2-40fc-8b50-c0e461320c31"

async def mock_get_current_user():
    return USER_ID

app.dependency_overrides[get_current_user] = mock_get_current_user

def run():
    print("=" * 60)
    print("  Supabase Storage Integration Test")
    print("=" * 60)

    # 1. Login to get vault token
    print("\n[1] Login (real mode)...")
    res = client.post("/api/vault/login", json={"password": "real_password_hash_123"})
    print(f"    Status: {res.status_code}")
    assert res.status_code == 200, f"Login failed: {res.text}"
    token_real = res.json()["access_token"]
    mode = res.json()["mode"]
    print(f"    Mode: {mode}, Token: {token_real[:30]}...")
    headers = {"x-vault-token": token_real}

    # 2. Upload a carrier image (raw PNG bytes)
    print("\n[2] Upload carrier image to Supabase Storage...")
    # Create a minimal valid PNG (1x1 red pixel)
    import struct, zlib
    def make_png():
        sig = b'\x89PNG\r\n\x1a\n'
        # IHDR
        ihdr_data = struct.pack('>IIBBBBB', 1, 1, 8, 2, 0, 0, 0)
        ihdr_crc = zlib.crc32(b'IHDR' + ihdr_data) & 0xffffffff
        ihdr = struct.pack('>I', 13) + b'IHDR' + ihdr_data + struct.pack('>I', ihdr_crc)
        # IDAT
        raw = b'\x00\xff\x00\x00'  # filter=0, R=255 G=0 B=0
        compressed = zlib.compress(raw)
        idat_crc = zlib.crc32(b'IDAT' + compressed) & 0xffffffff
        idat = struct.pack('>I', len(compressed)) + b'IDAT' + compressed + struct.pack('>I', idat_crc)
        # IEND
        iend_crc = zlib.crc32(b'IEND') & 0xffffffff
        iend = struct.pack('>I', 0) + b'IEND' + struct.pack('>I', iend_crc)
        return sig + ihdr + idat + iend

    png_bytes = make_png()
    res = client.post(
        "/api/upload-carrier",
        headers=headers,
        files={"image": ("test_carrier.png", io.BytesIO(png_bytes), "image/png")}
    )
    print(f"    Status: {res.status_code}")
    if res.status_code != 200:
        print(f"    ERROR: {res.text}")
        return
    upload_data = res.json()
    image_id = upload_data["image"]["id"]
    print(f"    Image ID: {image_id}")
    print(f"    Filename: {upload_data['image']['filename']}")

    # 3. Verify it's in Supabase bucket
    print("\n[3] Verify file exists in Supabase vault_images bucket...")
    if supabase:
        # Check DB entry
        db_entry = supabase.table("images").select("*").eq("id", image_id).execute()
        if db_entry.data:
            path = db_entry.data[0]["path"]
            print(f"    DB path: {path}")
            # Check bucket
            parts = path.rsplit("/", 1)
            folder = parts[0] if len(parts) > 1 else ""
            files = supabase.storage.from_("vault_images").list(folder)
            found = any(f["name"] == parts[-1] for f in files) if files else False
            print(f"    Found in bucket: {found}")
            assert found, "File NOT found in Supabase bucket!"
        else:
            print("    ERROR: No DB entry found!")
            return

    # 4. Gallery should list it
    print("\n[4] Gallery list...")
    res = client.get("/api/gallery", headers=headers)
    print(f"    Status: {res.status_code}")
    assert res.status_code == 200
    images = res.json()["images"]
    print(f"    Total images: {len(images)}")
    found_in_gallery = any(img["id"] == image_id for img in images)
    print(f"    Our image in gallery: {found_in_gallery}")
    assert found_in_gallery, "Uploaded image not found in gallery!"

    # 5. Serve image (downloads from Supabase, proxied through backend)
    print("\n[5] Serve image via /api/images/{id} (Option B proxy)...")
    res = client.get(f"/api/images/{image_id}", headers=headers)
    print(f"    Status: {res.status_code}")
    print(f"    Content-Type: {res.headers.get('content-type')}")
    print(f"    Response body size: {len(res.content)} bytes")
    assert res.status_code == 200, f"Serve failed: {res.text}"
    assert len(res.content) > 0, "Empty image response!"

    # 6. Delete image
    print("\n[6] Delete image...")
    res = client.delete(f"/api/images/{image_id}", headers=headers)
    print(f"    Status: {res.status_code}")
    assert res.status_code == 200

    # 7. Verify deleted from bucket
    print("\n[7] Verify deleted from bucket...")
    if supabase:
        files = supabase.storage.from_("vault_images").list(folder)
        still_there = any(f["name"] == parts[-1] for f in files) if files else False
        print(f"    Still in bucket: {still_there}")
        assert not still_there, "File was NOT deleted from bucket!"

    print("\n" + "=" * 60)
    print("  ALL TESTS PASSED ✓")
    print("=" * 60)

if __name__ == "__main__":
    run()
