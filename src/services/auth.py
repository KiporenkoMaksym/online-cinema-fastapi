from datetime import datetime, timedelta, timezone
import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models.users import User, RefreshToken
from src.schemas.auth import UserLoginSchema
from src.security.password import verify_password
from src.security.jwt import (
    create_access_token,
    create_refresh_token,
    hash_token,
    decode_refresh_token,
    settings,
)


class InvalidRefreshTokenError(Exception):
    pass


class InvalidCredentialsError(Exception):
    pass


class InactiveAccountError(Exception):
    pass


async def login_user(
    data: UserLoginSchema,
    session: AsyncSession,
) -> dict:
    result = await session.execute(select(User).where(User.email == str(data.email)))
    user = result.scalar_one_or_none()

    if user is None:
        raise InvalidCredentialsError("Invalid email or password")

    if not verify_password(
        data.password,
        user.hashed_password,
    ):
        raise InvalidCredentialsError("Invalid email or password")

    if not user.is_active:
        raise InactiveAccountError("Account is not activated")

    access_token = create_access_token(user.id)
    refresh_token = create_refresh_token(user.id)

    db_token = RefreshToken(
        user_id=user.id,
        token=hash_token(refresh_token),
        expires_at=datetime.now(timezone.utc)
        + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )

    session.add(db_token)
    await session.commit()

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


async def logout_user(
    refresh_token: str,
    session: AsyncSession,
) -> None:
    try:
        payload = decode_refresh_token(refresh_token)
        user_id = int(payload["sub"])

    except (jwt.InvalidTokenError, ValueError, KeyError) as error:
        raise InvalidRefreshTokenError("Invalid or expired refresh token") from error

    token_hash = hash_token(refresh_token)

    result = await session.execute(
        select(RefreshToken).where(
            RefreshToken.token == token_hash,
            RefreshToken.user_id == user_id,
        )
    )

    stored_token = result.scalar_one_or_none()

    if stored_token is None:
        raise InvalidRefreshTokenError("Refresh token not found or already revoked")

    await session.delete(stored_token)
    await session.commit()


async def refresh_access_token(
    refresh_token: str,
    session: AsyncSession,
) -> str:
    try:
        payload = decode_refresh_token(refresh_token)
        user_id = int(payload["sub"])

    except (jwt.InvalidTokenError, ValueError, KeyError) as error:
        raise InvalidRefreshTokenError("Invalid or expired refresh token") from error

    token_hash = hash_token(refresh_token)

    result = await session.execute(
        select(RefreshToken).where(
            RefreshToken.token == token_hash,
            RefreshToken.user_id == user_id,
        )
    )

    stored_token = result.scalar_one_or_none()

    if stored_token is None:
        raise InvalidRefreshTokenError("Refresh token not found or revoked")

    expires_at = stored_token.expires_at

    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if expires_at <= datetime.now(timezone.utc):
        raise InvalidRefreshTokenError("Refresh token has expired")

    user_result = await session.execute(select(User).where(User.id == user_id))

    user = user_result.scalar_one_or_none()

    if user is None or not user.is_active:
        raise InvalidRefreshTokenError("User not found or inactive")

    return create_access_token(user.id)
