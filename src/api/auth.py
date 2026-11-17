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
from src.schemas.auth import UserLoginSchema, TokenResponseSchema

from src.services.auth import (
    login_user,
    InvalidCredentialsError,
    InactiveAccountError,
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
        "Authenticates an active user and returns "
        "JWT access and refresh tokens."
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
