# Unit and integration tests for Supabase Authentication, Profile Approval & Per-User Chat Isolation
import os
import sys
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ.setdefault("SUPABASE_URL", "https://test.supabase.co")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "test-key-for-unit-tests")
os.environ.setdefault("GROQ_API_KEY", "test-groq-key")
os.environ.setdefault("GROQ_MODEL", "openai/gpt-oss-120b")

from app.main import app
from app.services.auth_service import (
    UserProfile,
    AuthUser,
    get_current_user,
    get_current_approved_user,
    get_current_admin_user,
)
from app.routers.chat import get_optional_auth_user

client = TestClient(app)


def teardown_function():
    """Clear FastAPI dependency overrides after each test."""
    app.dependency_overrides.clear()


def test_signup_creates_pending_user():
    """Verify signup flow creates user and returns pending status."""
    mock_auth_user = MagicMock(id="user-123", email="newuser@example.com", user_metadata={"full_name": "New User"})
    mock_auth_res = MagicMock(user=mock_auth_user, session=None)

    mock_supabase = MagicMock()
    mock_supabase.auth.sign_up.return_value = mock_auth_res
    mock_supabase.table().select().limit().execute.return_value = MagicMock(data=[{"id": "existing-admin"}])
    mock_supabase.table().upsert().execute.return_value = MagicMock(data=[])

    with patch("app.routers.auth.get_supabase", return_value=mock_supabase), \
         patch("app.routers.auth.create_auth_client", return_value=mock_supabase), \
         patch("app.services.auth_service.get_supabase", return_value=mock_supabase):
        resp = client.post("/auth/signup", json={
            "email": "newuser@example.com",
            "password": "securepassword123",
            "full_name": "New User"
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["user"]["email"] == "newuser@example.com"
        assert data["user"]["status"] == "pending"
        assert data["user"]["role"] == "user"
        assert "pending administrator approval" in data["message"]


def test_login_pending_user_is_blocked_with_403():
    """Verify login as pending user is blocked from dashboard access with 403."""
    mock_auth_user = MagicMock(id="user-pending-123", email="pending@example.com", user_metadata={})
    mock_session = MagicMock(access_token="valid-jwt-token", expires_in=3600)
    mock_auth_res = MagicMock(user=mock_auth_user, session=mock_session)

    mock_supabase = MagicMock()
    mock_supabase.auth.sign_in_with_password.return_value = mock_auth_res

    pending_profile = UserProfile(
        id="user-pending-123",
        email="pending@example.com",
        role="user",
        status="pending"
    )

    with patch("app.routers.auth.get_supabase", return_value=mock_supabase), \
         patch("app.routers.auth.create_auth_client", return_value=mock_supabase), \
         patch("app.routers.auth.get_profile_by_user_id", return_value=pending_profile):
        resp = client.post("/auth/login", json={
            "email": "pending@example.com",
            "password": "correctpassword"
        })
        assert resp.status_code == 403
        assert "Your account is pending administrator approval" in resp.json()["detail"]


def test_login_approved_user_receives_token():
    """Verify approved user receives access token and profile."""
    mock_auth_user = MagicMock(id="user-approved-123", email="approved@example.com", user_metadata={})
    mock_session = MagicMock(access_token="valid-approved-jwt", expires_in=3600)
    mock_auth_res = MagicMock(user=mock_auth_user, session=mock_session)

    mock_supabase = MagicMock()
    mock_supabase.auth.sign_in_with_password.return_value = mock_auth_res

    approved_profile = UserProfile(
        id="user-approved-123",
        email="approved@example.com",
        full_name="Approved User",
        role="user",
        status="approved"
    )

    with patch("app.routers.auth.get_supabase", return_value=mock_supabase), \
         patch("app.routers.auth.create_auth_client", return_value=mock_supabase), \
         patch("app.routers.auth.get_profile_by_user_id", return_value=approved_profile):
        resp = client.post("/auth/login", json={
            "email": "approved@example.com",
            "password": "correctpassword"
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["access_token"] == "valid-approved-jwt"
        assert data["user"]["status"] == "approved"


def test_admin_endpoints_require_admin_role():
    """Verify non-admin users cannot access admin endpoints."""
    normal_user = AuthUser(
        id="normal-user-1",
        email="user@example.com",
        profile=UserProfile(id="normal-user-1", email="user@example.com", role="user", status="approved")
    )
    app.dependency_overrides[get_current_user] = lambda: normal_user

    resp = client.get("/admin/users", headers={"Authorization": "Bearer normal-token"})
    assert resp.status_code == 403
    assert "Administrator privileges required" in resp.json()["detail"]


def test_admin_can_approve_pending_user():
    """Verify approved admin can approve pending user."""
    admin_user = AuthUser(
        id="admin-user-1",
        email="admin@example.com",
        profile=UserProfile(id="admin-user-1", email="admin@example.com", role="admin", status="approved")
    )
    app.dependency_overrides[get_current_user] = lambda: admin_user

    approved_user_profile = UserProfile(
        id="target-user-1",
        email="target@example.com",
        role="user",
        status="approved",
        approved_by="admin-user-1"
    )
    with patch("app.routers.admin.update_user_status", return_value=approved_user_profile):
        resp = client.post(
            "/admin/approve",
            json={"user_id": "target-user-1"},
            headers={"Authorization": "Bearer admin-token"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == "target-user-1"
        assert data["status"] == "approved"
        assert data["approved_by"] == "admin-user-1"


def test_chat_history_per_user_isolation():
    """Verify that User A cannot see User B's chat messages."""
    user_a = AuthUser(
        id="user-a-uuid",
        email="a@example.com",
        profile=UserProfile(id="user-a-uuid", email="a@example.com", role="user", status="approved")
    )
    app.dependency_overrides[get_optional_auth_user] = lambda: user_a

    user_a_messages = [
        {"id": 1, "session_id": "sess-1", "user_id": "user-a-uuid", "role": "user", "content": "User A secret message", "created_at": "2026-08-29T10:00:00Z"}
    ]

    with patch("app.services.assistant.load_chat_history", return_value=user_a_messages) as mock_load:
        resp = client.get("/chat/history?session_id=sess-1", headers={"Authorization": "Bearer token-a"})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["messages"]) == 1
        assert data["messages"][0]["content"] == "User A secret message"
        mock_load.assert_called_with("sess-1", user_id="user-a-uuid", limit=50)
