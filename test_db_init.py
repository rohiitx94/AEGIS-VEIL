from api.db import supabase
import os

print(f"Supabase client: {supabase}")
if supabase:
    try:
        res = supabase.table("images").select("*").limit(1).execute()
        print(f"Successfully queried images! Result: {res}")
    except Exception as e:
        print(f"Query failed: {e}")
else:
    print("Supabase client failed to initialize.")
