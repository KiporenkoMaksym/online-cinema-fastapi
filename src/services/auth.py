from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models.users import User, RefreshToken
from src.schemas.auth import UserLoginSchema
from src.security.password import verify_password
from src.security.jwt import (
    create_access_token,
    create_refresh_token,
    hash_token,
    settings,
)


class InvalidCredentialsError(Exception):
    pass


class InactiveAccountError(Exception):
    pass


async def login_user(
    data: UserLoginSchema,
    session: AsyncSession,
) -> dict:
    result = await session.execute(
        select(User).where(User.email == str(data.email))
    )
    user = result.scalar_one_or_none()

    if user is None:
        raise InvalidCredentialsError(
            "Invalid email or password"
        )

    if not verify_password(
        data.password,
        user.hashed_password,
    ):
        raise InvalidCredentialsError(
            "Invalid email or password"
        )

    if not user.is_active:
        raise InactiveAccountError(
            "Account is not activated"
        )

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
