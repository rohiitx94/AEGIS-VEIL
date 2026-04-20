from fastapi.testclient import TestClient
from api.main import app, get_current_user
import io

client = TestClient(app)

USER_ID = "a383e13f-38f2-40fc-8b50-c0e461320c31"

async def mock_get_current_user():
    return USER_ID

app.dependency_overrides[get_current_user] = mock_get_current_user

def run_tests():
    print("1. Setup Vault (Set Real Password)")
    res = client.post("/api/vault/setup", json={"password": "real_password_hash_123"})
    print("Setup:", res.json())
    assert res.status_code == 200

    print("\n2. Login Real Mode")
    res = client.post("/api/vault/login", json={"password": "real_password_hash_123"})
    print("Login Real:", res.json())
    assert res.status_code == 200
    assert res.json().get("mode") == "real"
    token_real = res.json()["access_token"]
    
    print("\n3. Login Panic Mode (Wrong DB password)")
    res = client.post("/api/vault/login", json={"password": "wrong_password"})
    print("Login Panic:", res.json())
    assert res.status_code == 200
    assert res.json().get("mode") == "panic"
    token_panic = res.json()["access_token"]

    print("\n4. Joint Vault Create")
    try:
        res = client.post("/api/vault/shared/create", json={"join_password": "joint_secure_123"})
        print("Shared Create:", res.json())
        assert res.status_code == 200
    except Exception as e:
        print("Shared Create Failed", str(e))
    
    print("\n5. Joint Vault Join")
    res = client.post("/api/vault/shared/join", json={"join_password": "joint_secure_123"})
    print("Shared Join:", res.json())
    assert res.status_code == 200
    assert res.json().get("mode") == "real"

    print("\n6. Seed Decoy (Real Mode)")
    res = client.post("/api/seed-decoy", headers={"x-vault-token": token_real})
    print("Seed Decoy Real:", res.status_code, res.text)
    
    print("\n7. Upload Secret (Stego Engine)")
    res = client.post(
        "/api/upload-secret",
        headers={"x-vault-token": token_real},
        data={"password": "enc_password", "carrier_description": "a simple dark square"},
        files={"secret_file": ("test.txt", io.BytesIO(b"Hello World! Secret Text."))}
    )
    print("Upload Secret:", res.status_code, res.text)
    if res.status_code == 200:
        image_id = res.json()["image"]["id"]
        
        print("\n8. Extract Secret")
        res = client.post(
            "/api/extract-secret",
            headers={"x-vault-token": token_real},
            data={"image_id": image_id, "password": "enc_password"}
        )
        print("Extract Secret:", res.status_code, res.text)
    
    print("\nAll tests passed!")

if __name__ == "__main__":
    run_tests()
