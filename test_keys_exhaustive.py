import os
from supabase import create_client, ClientOptions
from dotenv import load_dotenv

load_dotenv()

url = os.getenv("SUPABASE_URL")
anon_key = os.getenv("SUPABASE_ANON_KEY")
secret_key = os.getenv("SUPABASE_KEY")

def test_key(name, key):
    print(f"--- Testing {name} ---")
    try:
        # Try native first
        s = create_client(url, key)
        res = s.table("images").select("count", count="exact").execute()
        print(f"Native {name} success: {res.count}")
    except Exception as e:
        print(f"Native {name} failed: {e}")
        
    try:
        # Try with manual headers
        s = create_client(url, key, options=ClientOptions(headers={"apikey": key, "Authorization": f"Bearer {key}"}))
        res = s.table("images").select("count", count="exact").execute()
        print(f"Header {name} success: {res.count}")
    except Exception as e:
        print(f"Header {name} failed: {e}")

test_key("ANON", anon_key)
test_key("SECRET", secret_key)
