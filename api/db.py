from postgrest import SyncPostgrestClient
from gotrue import SyncGoTrueClient
from api.config import settings
import logging

class SimpleSupabase:
    """
    A minimal wrapper for Supabase services to support opaque keys (sb_...)
    which are sometimes rejected by the high-level create_client constructor.
    """
    def __init__(self, url, key):
        self.url = url
        self.key = key
        self.headers = {
            "apikey": key,
            "Authorization": f"Bearer {key}"
        }
        # Initialize Postgrest (Database)
        self.postgrest = SyncPostgrestClient(f"{url}/rest/v1", headers=self.headers)
        # Initialize GoTrue (Auth)
        self.auth = SyncGoTrueClient(url=f"{url}/auth/v1", headers=self.headers)
        
    def table(self, table_name):
        return self.postgrest.table(table_name)

try:
    if settings.SUPABASE_URL and settings.SUPABASE_KEY:
        supabase = SimpleSupabase(settings.SUPABASE_URL, settings.SUPABASE_KEY)
        logging.info("Supabase client (manual) initialized.")
    else:
        logging.warning("Supabase URL or Key missing.")
        supabase = None
except Exception as e:
    logging.error(f"Failed to initialize Supabase client: {e}")
    supabase = None
