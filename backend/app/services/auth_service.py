# Supabase Authentication & Profile Management Service
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from fastapi import Header, HTTPException, Depends, status
from pydantic import BaseModel

from app.database import get_supabase, create_auth_client
from app.config import settings

logger = logging.getLogger(__name__)


class UserProfile(BaseModel):
    id: str
    email: str
    full_name: Optional[str] = None
    role: str = "user"  # 'admin' | 'user'
    status: str = "pending"  # 'pending' | 'approved' | 'rejected'
    created_at: Optional[str] = None
    approved_at: Optional[str] = None
    approved_by: Optional[str] = None


class AuthUser(BaseModel):
    id: str
    email: str
    profile: UserProfile


def get_token_from_header(authorization: Optional[str] = Header(None)) -> str:
    """Extract Bearer token from Authorization header."""
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header. Please log in.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Authorization header format. Expected 'Bearer <token>'.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return parts[1]


def get_profile_by_user_id(user_id: str) -> Optional[UserProfile]:
    """Retrieve user profile from Supabase profiles table with service_role privileges."""
    try:
        sb = get_supabase()
        res = sb.table("profiles").select("*").eq("id", user_id).limit(1).execute()
        if res.data and len(res.data) > 0:
            row = res.data[0]
            prof = UserProfile(
                id=str(row["id"]),
                email=row["email"],
                full_name=row.get("full_name"),
                role=row.get("role", "user"),
                status=row.get("status", "pending"),
                created_at=str(row.get("created_at")),
                approved_at=str(row.get("approved_at")) if row.get("approved_at") else None,
                approved_by=str(row.get("approved_by")) if row.get("approved_by") else None,
            )
            logger.info(f"[PROFILE LOOKUP SUCCESS] ID: {prof.id}, Email: {prof.email}, Role: {prof.role}, Status: {prof.status}")
            return prof
    except Exception as e:
        logger.error(f"[PROFILE LOOKUP ERROR] user_id={user_id}: {e}")
    return None


def get_profile_by_email(email: str) -> Optional[UserProfile]:
    """Retrieve user profile by email address from Supabase profiles table."""
    try:
        sb = get_supabase()
        res = sb.table("profiles").select("*").eq("email", email.strip().lower()).limit(1).execute()
        if res.data and len(res.data) > 0:
            row = res.data[0]
            return UserProfile(
                id=str(row["id"]),
                email=row["email"],
                full_name=row.get("full_name"),
                role=row.get("role", "user"),
                status=row.get("status", "pending"),
                created_at=str(row.get("created_at")),
                approved_at=str(row.get("approved_at")) if row.get("approved_at") else None,
                approved_by=str(row.get("approved_by")) if row.get("approved_by") else None,
            )
    except Exception as e:
        logger.error(f"[PROFILE LOOKUP BY EMAIL ERROR] email={email}: {e}")
    return None


def create_or_update_profile(
    user_id: str,
    email: str,
    full_name: Optional[str] = None,
    role: str = "user",
    status: str = "pending",
    approved_by: Optional[str] = None,
) -> UserProfile:
    """Insert or update user profile in Supabase profiles table using service role client."""
    now_iso = datetime.now(timezone.utc).isoformat()
    profile_data: Dict[str, Any] = {
        "id": user_id,
        "email": email.strip().lower(),
        "full_name": full_name or "",
        "role": role,
        "status": status,
        "created_at": now_iso,
    }
    if status == "approved":
        profile_data["approved_at"] = now_iso
        if approved_by:
            profile_data["approved_by"] = approved_by

    try:
        sb = get_supabase()
        sb.table("profiles").upsert(profile_data).execute()
    except Exception as e:
        logger.warning(f"Could not upsert profile in Supabase: {e}")

    return UserProfile(
        id=user_id,
        email=email.strip().lower(),
        full_name=full_name,
        role=role,
        status=status,
        created_at=now_iso,
        approved_at=profile_data.get("approved_at"),
        approved_by=profile_data.get("approved_by"),
    )


async def get_current_user(token: str = Depends(get_token_from_header)) -> AuthUser:
    """Validate Supabase JWT token and return authenticated user and profile."""
    try:
        auth_sb = create_auth_client()
        user_resp = auth_sb.auth.get_user(token)
        if not user_resp or not user_resp.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired authentication token.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        u = user_resp.user
        user_id = str(u.id)
        email = u.email or ""
        raw_meta = u.user_metadata or {}
        full_name = raw_meta.get("full_name", "")

        profile = get_profile_by_user_id(user_id)
        if not profile:
            profile = get_profile_by_email(email)
        if not profile:
            profile = create_or_update_profile(
                user_id=user_id,
                email=email,
                full_name=full_name,
                role="user",
                status="pending",
            )

        logger.info(f"[/auth/me] AuthUser resolved: user_id={user_id}, email={email}, status={profile.status}, role={profile.role}")
        return AuthUser(id=user_id, email=email, profile=profile)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Authentication validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_approved_user(current_user: AuthUser = Depends(get_current_user)) -> AuthUser:
    """Ensure that the authenticated user's profile status is 'approved'."""
    if current_user.profile.status != "approved":
        if current_user.profile.status == "rejected":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Your account has been rejected by the administrator. Dashboard access is denied.",
            )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account is pending administrator approval. Please wait until your access is approved.",
        )
    return current_user


async def get_current_admin_user(current_user: AuthUser = Depends(get_current_approved_user)) -> AuthUser:
    """Ensure that the authenticated user has role 'admin' and status 'approved'."""
    if current_user.profile.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: Administrator privileges required.",
        )
    return current_user


def list_all_profiles(status_filter: Optional[str] = None) -> List[UserProfile]:
    """List profiles for admin management."""
    try:
        sb = get_supabase()
        q = sb.table("profiles").select("*").order("created_at", desc=True)
        if status_filter and status_filter.lower() != "all":
            q = q.eq("status", status_filter.lower())
        res = q.execute()
        results: List[UserProfile] = []
        for row in res.data or []:
            results.append(
                UserProfile(
                    id=str(row["id"]),
                    email=row["email"],
                    full_name=row.get("full_name"),
                    role=row.get("role", "user"),
                    status=row.get("status", "pending"),
                    created_at=str(row.get("created_at")),
                    approved_at=str(row.get("approved_at")) if row.get("approved_at") else None,
                    approved_by=str(row.get("approved_by")) if row.get("approved_by") else None,
                )
            )
        return results
    except Exception as e:
        logger.error(f"Error listing profiles: {e}")
        return []


def update_user_status(
    target_user_id: str,
    new_status: str,
    admin_user_id: str,
    new_role: Optional[str] = None,
) -> UserProfile:
    """Approve or reject a user profile (executed only by approved admin)."""
    now_iso = datetime.now(timezone.utc).isoformat()
    update_data: Dict[str, Any] = {
        "status": new_status,
    }
    if new_status == "approved":
        update_data["approved_at"] = now_iso
        update_data["approved_by"] = admin_user_id
    elif new_status in ("rejected", "pending"):
        update_data["approved_at"] = None
        update_data["approved_by"] = None

    if new_role:
        update_data["role"] = new_role

    try:
        sb = get_supabase()
        sb.table("profiles").update(update_data).eq("id", target_user_id).execute()
    except Exception as e:
        logger.error(f"Error updating user status in Supabase: {e}")
        raise HTTPException(
            status_code=500, detail=f"Database update failed: {str(e)}"
        )

    profile = get_profile_by_user_id(target_user_id)
    if not profile:
        raise HTTPException(status_code=404, detail="User profile not found after update.")
    return profile
