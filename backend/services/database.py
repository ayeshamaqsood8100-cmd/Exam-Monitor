from supabase import create_client, Client
from backend.config.settings import settings

class DatabaseService:
    def __init__(self):
        # Use the service role key so backend operations bypass RLS safely.
        # The service_role key is required to bypass Row Level Security for backend operations.
        self.client: Client = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_SERVICE_ROLE_KEY
        )

# Create a single global instance of the database connection
db = DatabaseService()
