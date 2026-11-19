from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.session import get_db
from src.schemas.users import (
    UserRegisterSchema,
    UserResponseSchema,
    ResendActivationSchema,
)
from src.notifications.email import send_activation_email
from src.services.users import (
    UserAlreadyExistsError,
    register_user,
    activate_user,
    InvalidActivationTokenError,
    ExpiredActivationTokenError,
    resend_activation_token,
)
from src.schemas.auth import (
    UserLoginSchema,
    TokenResponseSchema,
    RefreshTokenRequestSchema,
    AccessTokenResponseSchema,
)
from src.security.dependencies import get_current_user
from src.database.models.users import User
from src.services.auth import (
    login_user,
    refresh_access_token,
    logout_user,
    InvalidCredentialsError,
    InactiveAccountError,
    InvalidRefreshTokenError,
)

router = APIRouter(
    prefix="/api/v1/accounts",
    tags=["Authentication"],
)


@router.post(
    "/register/",
    response_model=UserResponseSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description=(
        "Registers a user and sends an activation email. "
        "The activation link is valid for 24 hours."
    ),
    responses={
        409: {"description": "Email already registered"},
        422: {"description": "Invalid registration data"},
    },
)
async def register(
    data: UserRegisterSchema,
    session: AsyncSession = Depends(get_db),
):
    try:
        user, activation_token = await register_user(
            data,
            session,
        )
    except UserAlreadyExistsError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error

    await send_activation_email(
        recipient=user.email,
        token=activation_token,
    )

    return user


@router.get(
    "/activate/",
    summary="Activate user account",
    description="Activate an account using a token received by email.",
)
async def activate_account(
    token: str,
    session: AsyncSession = Depends(get_db),
):
    try:
        await activate_user(token, session)

    except InvalidActivationTokenError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        ) from error

    except ExpiredActivationTokenError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        ) from error

    return {"message": "Account activated successfully"}


@router.post(
    "/resend-activation/",
    summary="Resend account activation email",
    description=(
        "Generates a new activation token valid for 24 hours "
        "and sends a new email to an inactive user."
    ),
)
async def resend_activation(
    data: ResendActivationSchema,
    session: AsyncSession = Depends(get_db),
):
    token = await resend_activation_token(
        email=str(data.email),
        session=session,
    )

    if token is not None:
        await send_activation_email(
            recipient=str(data.email),
            token=token,
        )

    return {
        "message": (
            "If the account exists and is not activated, "
            "a new activation email has been sent."
        )
    }


@router.post(
    "/login/",
    response_model=TokenResponseSchema,
    summary="Login user",
    description=(
        "Authenticates an active user and returns " "JWT access and refresh tokens."
    ),
    responses={
        401: {"description": "Invalid credentials"},
        403: {"description": "Account is not activated"},
    },
)
async def login(
    data: UserLoginSchema,
    session: AsyncSession = Depends(get_db),
):
    try:
        return await login_user(data, session)

    except InvalidCredentialsError as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(error),
        ) from error

    except InactiveAccountError as error:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(error),
        ) from error


@router.post(
    "/logout/",
    status_code=status.HTTP_200_OK,
    summary="Logout user",
    description=(
        "Revokes the provided refresh token, " "preventing it from being used again."
    ),
    responses={
        401: {"description": "Invalid or revoked refresh token"},
    },
)
async def logout(
    data: RefreshTokenRequestSchema,
    session: AsyncSession = Depends(get_db),
):
    try:
        await logout_user(
            refresh_token=data.refresh_token,
            session=session,
        )

    except InvalidRefreshTokenError as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(error),
        ) from error

    return {"message": "Successfully logged out"}


@router.get(
    "/me/",
    summary="Get current user",
)
async def get_me(
    current_user: User = Depends(get_current_user),
):
    return {
        "id": current_user.id,
        "email": current_user.email,
        "is_active": current_user.is_active,
    }


@router.post(
    "/token/refresh/",
    response_model=AccessTokenResponseSchema,
    summary="Refresh access token",
    responses={
        401: {"description": "Invalid or revoked refresh token"},
    },
)
async def refresh_token_endpoint(
    data: RefreshTokenRequestSchema,
    session: AsyncSession = Depends(get_db),
):
    try:
        access_token = await refresh_access_token(
            refresh_token=data.refresh_token,
            session=session,
        )

    except InvalidRefreshTokenError as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(error),
        ) from error

    return AccessTokenResponseSchema(
        access_token=access_token,
    )
