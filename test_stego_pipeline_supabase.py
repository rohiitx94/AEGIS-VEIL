"""
Full stego pipeline test with Supabase Storage:
  Upload Secret → Gallery → Extract → Verify roundtrip
"""
from fastapi.testclient import TestClient
from api.main import app, get_current_user
import io

client = TestClient(app)
USER_ID = "a383e13f-38f2-40fc-8b50-c0e461320c31"

async def mock_get_current_user():
    return USER_ID

app.dependency_overrides[get_current_user] = mock_get_current_user

def run():
    print("=" * 60)
    print("  Full Stego Pipeline w/ Supabase Storage")
    print("=" * 60)

    # 1. Login
    print("\n[1] Login...")
    res = client.post("/api/vault/login", json={"password": "real_password_hash_123"})
    assert res.status_code == 200
    token = res.json()["access_token"]
    headers = {"x-vault-token": token}
    print(f"    Mode: {res.json()['mode']}")

    # 2. Upload secret file (auto-generates carrier)
    print("\n[2] Upload secret (auto-carrier)...")
    secret_text = b"TOP SECRET: The treasure is buried under the old oak tree."
    res = client.post(
        "/api/upload-secret",
        headers=headers,
        data={"password": "my_encryption_key", "carrier_description": "a simple dark square"},
        files={"secret_file": ("treasure_map.txt", io.BytesIO(secret_text), "text/plain")}
    )
    print(f"    Status: {res.status_code}")
    if res.status_code != 200:
        print(f"    ERROR: {res.text}")
        return
    data = res.json()
    stego_id = data["image"]["id"]
    print(f"    Stego image ID: {stego_id}")
    print(f"    Message: {data['message']}")

    # 3. Verify in gallery
    print("\n[3] Check gallery...")
    res = client.get("/api/gallery", headers=headers)
    assert res.status_code == 200
    images = res.json()["images"]
    stego_entry = next((img for img in images if img["id"] == stego_id), None)
    assert stego_entry, "Stego image not in gallery!"
    print(f"    Found in gallery: True")
    print(f"    Has hidden data: {stego_entry['has_hidden_data']}")
    print(f"    Hidden file: {stego_entry.get('hidden_file_name')}")

    # 4. Serve the stego image (confirm it downloads from Supabase)
    print("\n[4] Serve stego image...")
    res = client.get(f"/api/images/{stego_id}", headers=headers)
    assert res.status_code == 200
    print(f"    Size: {len(res.content)} bytes")

    # 5. Extract secret
    print("\n[5] Extract secret...")
    res = client.post(
        "/api/extract-secret",
        headers=headers,
        data={"image_id": stego_id, "password": "my_encryption_key"}
    )
    print(f"    Status: {res.status_code}")
    if res.status_code != 200:
        print(f"    ERROR: {res.text}")
        return
    extract_data = res.json()
    print(f"    Extracted file: {extract_data['extracted_file']}")
    print(f"    File size: {extract_data['file_size']}")

    # 6. Download extracted file
    print("\n[6] Download extracted file...")
    dl_url = extract_data["download_url"]
    res = client.get(dl_url, headers=headers)
    assert res.status_code == 200
    recovered = res.content
    print(f"    Downloaded: {len(recovered)} bytes")
    print(f"    Content: {recovered.decode('utf-8')}")

    # 7. Verify roundtrip integrity
    print("\n[7] Verify roundtrip integrity...")
    assert recovered == secret_text, f"MISMATCH!\n  Sent:     {secret_text}\n  Received: {recovered}"
    print("    MATCH ✓")

    print("\n" + "=" * 60)
    print("  FULL PIPELINE PASSED ✓")
    print("=" * 60)

if __name__ == "__main__":
    run()
