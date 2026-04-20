import os
from gotrue import SyncGoTrueClient
from dotenv import load_dotenv

load_dotenv()

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")

headers = {
    "apikey": key,
    "Authorization": f"Bearer {key}"
}

print(f"Testing direct SyncGoTrueClient...")
try:
    # Use the auth URL
    client = SyncGoTrueClient(url=f"{url}/auth/v1", headers=headers)
    # Just try a simple call that doesn't need auth but checks connection
    print("Direct Auth Client created.")
    # Actually, we need a real check. 
except Exception as e:
    print(f"Auth failed: {e}")
