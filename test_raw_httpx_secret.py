import os
import httpx
from dotenv import load_dotenv

load_dotenv()

url = os.getenv("SUPABASE_URL")
secret_key = os.getenv("SUPABASE_KEY")

target_url = f"{url}/rest/v1/images?select=count"
headers = {
    "apikey": secret_key,
    "Authorization": f"Bearer {secret_key}"
}

print(f"Testing raw httpx with SECRET KEY to {target_url}...")
try:
    response = httpx.get(target_url, headers=headers)
    print(f"Status: {response.status_code}")
    print(f"Body: {response.text}")
except Exception as e:
    print(f"Request failed: {e}")
