import uuid
from datetime import UTC, datetime
from typing import Annotated, cast

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_current_user, get_db_session, require_roles
from src.models.application_user import ApplicationUser
from src.models.auth_schemas import (
    ApplicationUserInvite,
    ApplicationUserList,
    ApplicationUserProfileUpdate,
    ApplicationUserRoleUpdate,
    ApplicationUserStatusUpdate,
    AuthenticatedUser,
)
from src.services.auth_service import ApplicationUserService

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.get("/me", response_model=AuthenticatedUser)
async def get_my_profile(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> AuthenticatedUser:
    return current_user


@router.put("/me", response_model=AuthenticatedUser)
async def update_my_profile(
    payload: ApplicationUserProfileUpdate,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: AsyncSession = Depends(get_db_session),
) -> AuthenticatedUser:
    profile = await session.get(ApplicationUser, current_user.id)
    if profile is None:
        # Authentication-disabled local development uses an ephemeral admin.
        return cast(
            AuthenticatedUser,
            current_user.model_copy(update={"display_name": payload.display_name.strip()}),
        )
    profile.display_name = payload.display_name.strip()
    profile.updated_at = datetime.now(UTC)
    await session.commit()
    return ApplicationUserService.to_response(profile)


@router.get("/users", response_model=ApplicationUserList)
async def list_application_users(
    _admin: Annotated[AuthenticatedUser, Depends(require_roles("admin"))],
    limit: int = Query(default=100, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_db_session),
) -> ApplicationUserList:
    count = int((await session.execute(select(func.count()).select_from(ApplicationUser))).scalar_one())
    profiles = (
        await session.scalars(
            select(ApplicationUser).order_by(ApplicationUser.created_at, ApplicationUser.id).limit(limit).offset(offset)
        )
    ).all()
    return ApplicationUserList(
        count=count,
        results=[ApplicationUserService.to_response(profile) for profile in profiles],
    )


@router.patch("/users/{user_id}/role", response_model=AuthenticatedUser)
async def update_application_user_role(
    user_id: str,
    payload: ApplicationUserRoleUpdate,
    admin: Annotated[AuthenticatedUser, Depends(require_roles("admin"))],
    session: AsyncSession = Depends(get_db_session),
) -> AuthenticatedUser:
    profile = await session.get(ApplicationUser, user_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Application user was not found.")
    if profile.id == admin.id and payload.role != "admin":
        admin_count = int(
            (
                await session.execute(
                    select(func.count()).select_from(ApplicationUser).where(
                        ApplicationUser.role == "admin",
                        ApplicationUser.disabled.is_(False),
                    )
                )
            ).scalar_one()
        )
        if admin_count <= 1:
            raise HTTPException(status_code=409, detail="The last active administrator cannot remove their own role.")
    profile.role = payload.role
    profile.updated_at = datetime.now(UTC)
    await session.commit()
    return ApplicationUserService.to_response(profile)


@router.post("/users/invite", response_model=AuthenticatedUser, status_code=201)
async def invite_application_user(
    payload: ApplicationUserInvite,
    admin: Annotated[AuthenticatedUser, Depends(require_roles("admin"))],
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> AuthenticatedUser:
    """Create an application profile and send a Supabase invite when configured."""
    normalized_email = payload.email.strip().lower()
    existing = await session.scalar(select(ApplicationUser).where(ApplicationUser.email == normalized_email))
    if existing is not None:
        raise HTTPException(status_code=409, detail="An application user with this email already exists.")
    settings = getattr(request.app.state, "settings", None) if request else None
    if settings is not None and settings.auth_enabled and not settings.supabase_service_role_key:
        raise HTTPException(status_code=503, detail="Admin invites require SUPABASE_SERVICE_ROLE_KEY on the backend.")
    subject = f"pending-{uuid.uuid4().hex}"
    if settings is not None and getattr(settings, "supabase_service_role_key", None) and getattr(settings, "supabase_url", None):
        import httpx

        key = settings.supabase_service_role_key.get_secret_value()
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(
                f"{settings.supabase_url.rstrip('/')}/auth/v1/admin/invite",
                headers={"Authorization": f"Bearer {key}", "apikey": key, "Content-Type": "application/json"},
                json={"email": normalized_email, "data": {"full_name": payload.display_name.strip()}},
            )
        if response.is_error:
            raise HTTPException(status_code=502, detail="Supabase invite could not be sent.")
        subject = str(response.json().get("id") or subject)
    profile = ApplicationUser(
        id=subject,
        email=normalized_email,
        display_name=payload.display_name.strip(),
        role=payload.role,
        disabled=False,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    session.add(profile)
    await session.flush()
    await session.commit()
    return ApplicationUserService.to_response(profile)


@router.patch("/users/{user_id}/status", response_model=AuthenticatedUser)
async def update_application_user_status(
    user_id: str,
    payload: ApplicationUserStatusUpdate,
    admin: Annotated[AuthenticatedUser, Depends(require_roles("admin"))],
    session: AsyncSession = Depends(get_db_session),
) -> AuthenticatedUser:
    profile = await session.get(ApplicationUser, user_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Application user was not found.")
    if profile.id == admin.id and payload.disabled:
        raise HTTPException(status_code=409, detail="The current administrator cannot disable their own account.")
    if payload.disabled and profile.role == "admin":
        admin_count = int((await session.execute(select(func.count()).select_from(ApplicationUser).where(ApplicationUser.role == "admin", ApplicationUser.disabled.is_(False)))).scalar_one())
        if admin_count <= 1:
            raise HTTPException(status_code=409, detail="The last active administrator cannot be disabled.")
    profile.disabled = payload.disabled
    profile.updated_at = datetime.now(UTC)
    await session.commit()
    return ApplicationUserService.to_response(profile)
