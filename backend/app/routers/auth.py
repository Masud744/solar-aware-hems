# Authentication Router — /auth (Supabase Auth Integration)
import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, status, Header
from app.database import get_supabase, create_auth_client
from app.models.schemas import (
    SignUpRequest,
    LoginRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    AuthResponse,
    UserProfileSchema,
)
from app.services.auth_service import (
    get_current_user,
    get_profile_by_user_id,
    get_profile_by_email,
    create_or_update_profile,
    AuthUser,
    get_token_from_header,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup", response_model=AuthResponse)
async def signup_user(req: SignUpRequest):
    """Register a new user in Supabase Auth and initialize profile with pending status."""
    try:
        auth_sb = create_auth_client()
        res = auth_sb.auth.sign_up({
            "email": req.email,
            "password": req.password,
            "options": {
                "data": {
                    "full_name": req.full_name or "",
                }
            }
        })
        if not res or not res.user:
            raise HTTPException(
                status_code=400,
                detail="Signup failed. Please check your email and password.",
            )

        u = res.user
        user_id = str(u.id)

        # Check if first user in system
        existing_profile = get_profile_by_user_id(user_id) or get_profile_by_email(req.email)
        if not existing_profile:
            # Check if any profiles exist
            try:
                sb = get_supabase()
                prof_check = sb.table("profiles").select("id").limit(1).execute()
                is_first = not prof_check.data or len(prof_check.data) == 0
            except Exception:
                is_first = False

            role = "admin" if is_first else "user"
            initial_status = "approved" if is_first else "pending"

            profile = create_or_update_profile(
                user_id=user_id,
                email=req.email,
                full_name=req.full_name,
                role=role,
                status=initial_status,
            )
        else:
            profile = existing_profile

        user_schema = UserProfileSchema(
            id=profile.id,
            email=profile.email,
            full_name=profile.full_name,
            role=profile.role,
            status=profile.status,
            created_at=profile.created_at,
            approved_at=profile.approved_at,
            approved_by=profile.approved_by,
        )

        token = res.session.access_token if res.session else None
        expires_in = res.session.expires_in if res.session else None

        msg = (
            "Account created and approved as initial administrator."
            if profile.status == "approved"
            else "Account created successfully. Your access is currently pending administrator approval."
        )

        return AuthResponse(
            access_token=token,
            expires_in=expires_in,
            user=user_schema,
            message=msg,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Signup error: {e}")
        raise HTTPException(
            status_code=400,
            detail=f"Registration failed: {str(e)}",
        )


@router.post("/login", response_model=AuthResponse)
async def login_user(req: LoginRequest):
    """Authenticate user with Supabase Auth and check approval status."""
    try:
        auth_sb = create_auth_client()
        res = auth_sb.auth.sign_in_with_password({
            "email": req.email,
            "password": req.password,
        })
        if not res or not res.user or not res.session:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password.",
            )

        u = res.user
        user_id = str(u.id)
        email = u.email or req.email
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

        logger.info(
            f"[LOGIN AUTH CHECK] user_id={user_id}, email={email}, "
            f"profile_id={profile.id}, role={profile.role}, status={profile.status}"
        )

        user_schema = UserProfileSchema(
            id=profile.id,
            email=profile.email,
            full_name=profile.full_name,
            role=profile.role,
            status=profile.status,
            created_at=profile.created_at,
            approved_at=profile.approved_at,
            approved_by=profile.approved_by,
        )

        # Enforce approval status check
        if profile.status == "pending":
            logger.warning(f"[LOGIN BLOCKED] User {email} is pending approval.")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Your account is pending administrator approval. Please wait until your access is approved.",
            )
        elif profile.status == "rejected":
            logger.warning(f"[LOGIN BLOCKED] User {email} has been rejected.")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Your account access has been rejected by the administrator.",
            )

        logger.info(f"[LOGIN GRANTED] Access granted for approved user {email} (role: {profile.role}).")
        return AuthResponse(
            access_token=res.session.access_token,
            expires_in=res.session.expires_in,
            user=user_schema,
            message="Login successful.",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Login failed: {str(e)}",
        )


@router.get("/me", response_model=UserProfileSchema)
async def get_me(current_user: AuthUser = Depends(get_current_user)):
    """Return authenticated user profile."""
    p = current_user.profile
    return UserProfileSchema(
        id=p.id,
        email=p.email,
        full_name=p.full_name,
        role=p.role,
        status=p.status,
        created_at=p.created_at,
        approved_at=p.approved_at,
        approved_by=p.approved_by,
    )


@router.post("/forgot-password")
async def forgot_password(req: ForgotPasswordRequest):
    """Send password reset email via Supabase Auth."""
    try:
        auth_sb = create_auth_client()
        options = {}
        if req.redirect_url:
            options["redirect_to"] = req.redirect_url
        auth_sb.auth.reset_password_email(req.email, options=options)
        return {
            "status": "success",
            "message": "If the email is registered, a password reset link has been sent.",
        }
    except Exception as e:
        logger.error(f"Password reset request error: {e}")
        return {
            "status": "success",
            "message": "If the email is registered, a password reset link has been sent.",
        }


@router.post("/reset-password")
async def reset_password(
    req: ResetPasswordRequest,
    current_user: AuthUser = Depends(get_current_user),
):
    """Set new password for the currently authenticated user session."""
    try:
        sb = get_supabase()
        sb.auth.admin.update_user_by_id(current_user.id, {"password": req.new_password})
        return {
            "status": "success",
            "message": "Password updated successfully. Please log in with your new password.",
        }
    except Exception as e:
        logger.error(f"Password update error: {e}")
        raise HTTPException(
            status_code=400,
            detail=f"Failed to update password: {str(e)}",
        )
