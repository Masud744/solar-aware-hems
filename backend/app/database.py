# Supabase client initialization
from supabase import create_client, Client
from app.config import settings

_client: Client | None = None


def get_supabase() -> Client:
    """Get the persistent Supabase DB client singleton guaranteed with service_role superuser permissions."""
    global _client
    if _client is None:
        _client = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_SERVICE_ROLE_KEY,
        )
    # Always guarantee the service_role authorization header is set on Postgrest client
    try:
        _client.postgrest.auth(settings.SUPABASE_SERVICE_ROLE_KEY)
    except Exception:
        pass
    return _client


def create_auth_client() -> Client:
    """Create an isolated client for user authentication operations to avoid mutating service-role singleton."""
    return create_client(
        settings.SUPABASE_URL,
        settings.SUPABASE_SERVICE_ROLE_KEY,
    )
