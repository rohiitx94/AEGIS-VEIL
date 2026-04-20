import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")

# A dummy but valid-looking JWT to pass the constructor check
dummy_jwt = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoyNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"

print(f"Testing Postgrest header injection workaround...")
try:
    s = create_client(url, dummy_jwt)
    # Manually override the headers on the underlying clients
    s.postgrest.headers["apikey"] = key
    s.postgrest.headers["Authorization"] = f"Bearer {key}"
    
    res = s.table("images").select("count", count="exact").execute()
    print(f"Success! Count: {res.count}")
except Exception as e:
    print(f"Failed: {e}")
