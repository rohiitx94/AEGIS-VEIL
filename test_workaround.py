import os
from supabase import create_client, ClientOptions
from dotenv import load_dotenv

load_dotenv()

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")

# A dummy but valid-looking JWT
dummy_jwt = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzY2hlbWEiOiJwdWJsaWMifQ.dummy"

print(f"Testing dummy JWT bypass with key: {key[:10]}...")
try:
    s = create_client(url, dummy_jwt, options=ClientOptions(
        headers={
            "apikey": key,
            "Authorization": f"Bearer {key}"
        }
    ))
    res = s.table("images").select("count", count="exact").execute()
    print(f"Success! Count: {res.count}")
except Exception as e:
    print(f"Failed: {e}")
