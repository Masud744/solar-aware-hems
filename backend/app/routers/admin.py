# Admin Router — /admin (User Approval & Role Management)
import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, Query, status
from pydantic import BaseModel, Field

from app.models.schemas import (
    AdminUserListResponse,
    UserProfileSchema,
    AdminUserActionRequest,
)
from app.services.auth_service import (
    get_current_admin_user,
    list_all_profiles,
    update_user_status,
    create_or_update_profile,
    get_profile_by_user_id,
    AuthUser,
)
from app.database import get_supabase

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin", tags=["admin"])


class BootstrapAdminRequest(BaseModel):
    email: str = Field(..., description="Admin email address")
    admin_secret: Optional[str] = None


@router.get("/users", response_model=AdminUserListResponse)
async def get_admin_users(
    status: Optional[str] = Query(None, description="Filter by status: pending, approved, rejected, or all"),
    current_admin: AuthUser = Depends(get_current_admin_user),
):
    """List all registered user profiles with their approval status (Admin only)."""
    profiles = list_all_profiles(status_filter=status)
    schemas = [
        UserProfileSchema(
            id=p.id,
            email=p.email,
            full_name=p.full_name,
            role=p.role,
            status=p.status,
            created_at=p.created_at,
            approved_at=p.approved_at,
            approved_by=p.approved_by,
        )
        for p in profiles
    ]
    return AdminUserListResponse(users=schemas, count=len(schemas))


@router.post("/approve", response_model=UserProfileSchema)
async def approve_user(
    req: AdminUserActionRequest,
    current_admin: AuthUser = Depends(get_current_admin_user),
):
    """Approve a pending user for application access (Admin only)."""
    try:
        updated = update_user_status(
            target_user_id=req.user_id,
            new_status="approved",
            admin_user_id=current_admin.id,
            new_role=req.role,
        )
        return UserProfileSchema(
            id=updated.id,
            email=updated.email,
            full_name=updated.full_name,
            role=updated.role,
            status=updated.status,
            created_at=updated.created_at,
            approved_at=updated.approved_at,
            approved_by=updated.approved_by,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to approve user: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to approve user: {str(e)}"
        )


@router.post("/reject", response_model=UserProfileSchema)
async def reject_user(
    req: AdminUserActionRequest,
    current_admin: AuthUser = Depends(get_current_admin_user),
):
    """Reject a user's application access (Admin only)."""
    try:
        updated = update_user_status(
            target_user_id=req.user_id,
            new_status="rejected",
            admin_user_id=current_admin.id,
        )
        return UserProfileSchema(
            id=updated.id,
            email=updated.email,
            full_name=updated.full_name,
            role=updated.role,
            status=updated.status,
            created_at=updated.created_at,
            approved_at=updated.approved_at,
            approved_by=updated.approved_by,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to reject user: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to reject user: {str(e)}"
        )


@router.post("/set-role", response_model=UserProfileSchema)
async def set_user_role(
    req: AdminUserActionRequest,
    current_admin: AuthUser = Depends(get_current_admin_user),
):
    """Change a user's role between admin and user (Admin only)."""
    if not req.role or req.role not in ("admin", "user"):
        raise HTTPException(status_code=400, detail="Invalid role. Must be 'admin' or 'user'.")

    target = get_profile_by_user_id(req.user_id)
    if not target:
        raise HTTPException(status_code=404, detail="User profile not found.")

    try:
        updated = update_user_status(
            target_user_id=req.user_id,
            new_status=target.status,
            admin_user_id=current_admin.id,
            new_role=req.role,
        )
        return UserProfileSchema(
            id=updated.id,
            email=updated.email,
            full_name=updated.full_name,
            role=updated.role,
            status=updated.status,
            created_at=updated.created_at,
            approved_at=updated.approved_at,
            approved_by=updated.approved_by,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update role: {str(e)}")


@router.post("/bootstrap-admin", response_model=UserProfileSchema)
async def bootstrap_admin(req: BootstrapAdminRequest):
    """Securely promote a designated admin email to approved admin status."""
    sb = get_supabase()
    try:
        # Search for user in Supabase auth
        auth_users = sb.auth.admin.list_users()
        target_user = None
        for u in auth_users:
            if u.email and u.email.lower() == req.email.lower():
                target_user = u
                break

        if not target_user:
            raise HTTPException(
                status_code=404,
                detail=f"User with email '{req.email}' not found in Supabase Auth. Please register the account first.",
            )

        u_id = str(target_user.id)
        raw_meta = target_user.user_metadata or {}
        full_name = raw_meta.get("full_name", "")

        profile = create_or_update_profile(
            user_id=u_id,
            email=req.email,
            full_name=full_name,
            role="admin",
            status="approved",
        )

        return UserProfileSchema(
            id=profile.id,
            email=profile.email,
            full_name=profile.full_name,
            role=profile.role,
            status=profile.status,
            created_at=profile.created_at,
            approved_at=profile.approved_at,
            approved_by=profile.approved_by,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Admin bootstrap error: {e}")
        raise HTTPException(status_code=500, detail=f"Bootstrap failed: {str(e)}")
