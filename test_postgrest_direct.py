import os
from postgrest import SyncPostgrestClient
from dotenv import load_dotenv

load_dotenv()

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")

headers = {
    "apikey": key,
    "Authorization": f"Bearer {key}"
}

print(f"Testing direct SyncPostgrestClient...")
try:
    client = SyncPostgrestClient(f"{url}/rest/v1", headers=headers)
    res = client.table("images").select("count", count="exact").execute()
    print(f"Success! Count: {res.count}")
except Exception as e:
    print(f"Failed: {e}")
