import os
import jwt
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

# We need to generate a Supabase-compatible JWT if we want to test get_current_user
# But wait, get_current_user calls supabase.auth.get_user(token).
# This validates the token AGAINST SUPABASE.
# So we need a REAL token from Supabase.

# However, for testing, I can just modify get_current_user in api/main.py 
# to take a "test-token" that returns the legacy user.

print("Verification steps:")
print("1. Start the server: python -m api.main")
print("2. Test Gallery (Real Mode): curl -H 'X-Vault-Token: <real_token>' http://localhost:8000/api/gallery")
print("3. Test Gallery (Panic Mode): curl -H 'X-Vault-Token: <panic_token>' http://localhost:8000/api/gallery")

# I'll create a small script to generate the VAULT tokens (the ones our API creates)
def create_vault_token(mode, user_id, vault_id):
    secret = os.getenv("JWT_SECRET", "super-secret-jwt-key-for-stego-cloud")
    payload = {
        "mode": mode,
        "user_id": user_id,
        "vault_id": vault_id,
        "exp": datetime.utcnow() + timedelta(hours=24)
    }
    return jwt.encode(payload, secret, algorithm="HS256")

user_id = "a383e13f-38f2-40fc-8b50-c0e461320c31"
vault_id = "7445abb6-9ff8-4fcd-9923-a4073a3e283d"

real_token = create_vault_token("real", user_id, vault_id)
panic_token = create_vault_token("panic", user_id, user_id)

print(f"\nREAL Vault Token: {real_token}")
print(f"PANIC Vault Token: {panic_token}")
