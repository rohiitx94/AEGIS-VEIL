import os
import httpx
from dotenv import load_dotenv

load_dotenv()

url = os.getenv("SUPABASE_URL")
anon_key = os.getenv("SUPABASE_ANON_KEY")

target_url = f"{url}/rest/v1/images?select=count"
headers = {
    "apikey": anon_key,
    "Authorization": f"Bearer {anon_key}"
}

print(f"Testing raw httpx to {target_url}...")
try:
    response = httpx.get(target_url, headers=headers)
    print(f"Status: {response.status_code}")
    print(f"Body: {response.text}")
except Exception as e:
    print(f"Request failed: {e}")
