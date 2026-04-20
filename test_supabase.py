import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")

print(f"Testing connection to: {url}")
print(f"Using key starting with: {key[:10]}...")

try:
    supabase = create_client(url, key)
    print("Successfully created client!")
    # Test a simple query
    res = supabase.table("users").select("*").limit(1).execute()
    print(f"Query result: {res}")
except Exception as e:
    print(f"Failed to connect or query: {e}")
