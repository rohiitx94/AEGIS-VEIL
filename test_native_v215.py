import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

url = os.getenv("SUPABASE_URL")
anon_key = os.getenv("SUPABASE_ANON_KEY")
secret_key = os.getenv("SUPABASE_KEY")

def test_key(name, key):
    print(f"--- Testing {name} ---")
    try:
        s = create_client(url, key)
        # Try a simple query
        res = s.table("images").select("count", count="exact").execute()
        print(f"{name} success: {res.count}")
    except Exception as e:
        print(f"{name} failed: {e}")

test_key("ANON", anon_key)
test_key("SECRET", secret_key)
