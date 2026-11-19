import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models.users import (
    ActivationToken,
    User,
    UserGroup,
    UserGroupEnum,
)
from src.schemas.users import UserRegisterSchema
from src.security.password import hash_password


class UserAlreadyExistsError(Exception):
    pass


class InvalidActivationTokenError(Exception):
    pass


class ExpiredActivationTokenError(Exception):
    pass


async def activate_user(
    token: str,
    session: AsyncSession,
) -> None:
    activation_result = await session.execute(
        select(ActivationToken).where(ActivationToken.token == token)
    )

    activation = activation_result.scalar_one_or_none()

    if activation is None:
        raise InvalidActivationTokenError("Invalid activation token")

    expires_at = activation.expires_at

    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if expires_at <= datetime.now(timezone.utc):
        raise ExpiredActivationTokenError("Activation token has expired")

    user = await session.get(User, activation.user_id)

    if user is None:
        raise InvalidActivationTokenError("User not found")

    user.is_active = True

    await session.delete(activation)
    await session.commit()


async def register_user(
    data: UserRegisterSchema,
    session: AsyncSession,
) -> tuple[User, str]:
    user_result = await session.execute(
        select(User).where(User.email == str(data.email))
    )
    existing_user = user_result.scalar_one_or_none()

    if existing_user is not None:
        raise UserAlreadyExistsError("User with this email already exists")

    group_result = await session.execute(
        select(UserGroup).where(UserGroup.name == UserGroupEnum.USER)
    )
    user_group = group_result.scalar_one_or_none()

    if user_group is None:
        user_group = UserGroup(name=UserGroupEnum.USER)
        session.add(user_group)
        await session.flush()

    user = User(
        email=str(data.email),
        hashed_password=hash_password(data.password),
        is_active=False,
        group_id=user_group.id,
    )
    session.add(user)
    await session.flush()

    activation_value = secrets.token_urlsafe(32)

    activation_token = ActivationToken(
        user_id=user.id,
        token=activation_value,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
    )
    session.add(activation_token)

    await session.commit()
    await session.refresh(user)

    return user, activation_value


async def resend_activation_token(
    email: str,
    session: AsyncSession,
) -> str | None:
    user_result = await session.execute(select(User).where(User.email == email))
    user = user_result.scalar_one_or_none()

    if user is None or user.is_active:
        return None

    activation_result = await session.execute(
        select(ActivationToken).where(ActivationToken.user_id == user.id)
    )
    activation = activation_result.scalar_one_or_none()

    new_token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(hours=24)

    if activation is None:
        activation = ActivationToken(
            user_id=user.id,
            token=new_token,
            expires_at=expires_at,
        )
        session.add(activation)
    else:
        activation.token = new_token
        activation.expires_at = expires_at

    await session.commit()

    return new_token
