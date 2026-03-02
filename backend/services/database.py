from supabase import create_client, Client
from backend.config.settings import settings

class DatabaseService:
    def __init__(self):
        # We initialize the Supabase client using the URL and Service Key from our settings
        # VERY IMPORTANT: SUPABASE_SERVICE_KEY must be the 'service_role' secret key from 
        # API Settings -> Project API keys, NOT the public 'anon' key. 
        # The service_role key is required to bypass Row Level Security for backend operations.
        self.client: Client = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_SERVICE_KEY
        )

# Create a single global instance of the database connection
db = DatabaseService()
