from datetime import datetime, timedelta, timezone

import pytest
from pwdlib import PasswordHash
from sqlalchemy import select

from src.database.models.users import (
    User,
    UserGroup,
    UserGroupEnum,
    RefreshToken,
    ActivationToken,
)
from src.schemas.users import UserRegisterSchema
from src.security.jwt import (
    create_access_token,
    create_refresh_token,
    hash_token,
)
from src.schemas.auth import UserLoginSchema
from src.services.auth import (
    InvalidCredentialsError,
    InvalidRefreshTokenError,
    login_user,
    logout_user,
    refresh_access_token,
    InactiveAccountError,
)
from src.services.users import (
    UserAlreadyExistsError,
    register_user,
    activate_user,
    ExpiredActivationTokenError,
    InvalidActivationTokenError,
)

PASSWORD = "CinemaTest2026!"


async def create_test_user(db_session, email, is_active=True):
    group = UserGroup(name=UserGroupEnum.USER)
    db_session.add(group)
    await db_session.flush()

    user = User(
        email=email,
        hashed_password=PasswordHash.recommended().hash(PASSWORD),
        is_active=is_active,
        group_id=group.id,
    )

    db_session.add(user)
    await db_session.commit()

    return user


@pytest.mark.asyncio
async def test_login_with_wrong_password(db_session):
    await create_test_user(
        db_session,
        "wrong-password@example.com",
    )

    data = UserLoginSchema(
        email="wrong-password@example.com",
        password="WrongPassword123!",
    )

    with pytest.raises(
        InvalidCredentialsError,
        match="Invalid email or password",
    ):
        await login_user(data, db_session)


@pytest.mark.asyncio
async def test_refresh_expired_stored_token(db_session):
    user = await create_test_user(
        db_session,
        "expired-refresh@example.com",
    )

    token = create_refresh_token(user.id)

    stored_token = RefreshToken(
        user_id=user.id,
        token=hash_token(token),
        expires_at=datetime.now(timezone.utc) - timedelta(hours=1),
    )

    db_session.add(stored_token)
    await db_session.commit()

    with pytest.raises(
        InvalidRefreshTokenError,
        match="Refresh token has expired",
    ):
        await refresh_access_token(token, db_session)


@pytest.mark.asyncio
async def test_refresh_token_for_inactive_user(db_session):
    user = await create_test_user(
        db_session,
        "inactive-refresh@example.com",
        is_active=False,
    )

    token = create_refresh_token(user.id)

    stored_token = RefreshToken(
        user_id=user.id,
        token=hash_token(token),
        expires_at=datetime.now(timezone.utc) + timedelta(days=1),
    )

    db_session.add(stored_token)
    await db_session.commit()

    with pytest.raises(
        InvalidRefreshTokenError,
        match="User not found or inactive",
    ):
        await refresh_access_token(token, db_session)


@pytest.mark.asyncio
async def test_refresh_for_missing_user(db_session):
    token = create_refresh_token(999999)

    stored_token = RefreshToken(
        user_id=999999,
        token=hash_token(token),
        expires_at=datetime.now(timezone.utc) + timedelta(days=1),
    )

    db_session.add(stored_token)
    await db_session.commit()

    with pytest.raises(
        InvalidRefreshTokenError,
        match="User not found or inactive",
    ):
        await refresh_access_token(token, db_session)


@pytest.mark.asyncio
async def test_logout_twice(db_session):
    user = await create_test_user(
        db_session,
        "logout-twice@example.com",
    )

    token = create_refresh_token(user.id)

    db_session.add(
        RefreshToken(
            user_id=user.id,
            token=hash_token(token),
            expires_at=datetime.now(timezone.utc) + timedelta(days=1),
        )
    )
    await db_session.commit()

    await logout_user(token, db_session)

    with pytest.raises(
        InvalidRefreshTokenError,
        match="Refresh token not found or already revoked",
    ):
        await logout_user(token, db_session)


@pytest.mark.asyncio
async def test_refresh_with_access_token(db_session):
    user = await create_test_user(
        db_session,
        "wrong-token-type@example.com",
    )

    access_token = create_access_token(user.id)

    with pytest.raises(
        InvalidRefreshTokenError,
        match="Invalid or expired refresh token",
    ):
        await refresh_access_token(
            access_token,
            db_session,
        )


@pytest.mark.asyncio
async def test_logout_with_access_token(db_session):
    user = await create_test_user(
        db_session,
        "logout-access-token@example.com",
    )

    access_token = create_access_token(user.id)

    with pytest.raises(
        InvalidRefreshTokenError,
        match="Invalid or expired refresh token",
    ):
        await logout_user(
            access_token,
            db_session,
        )


@pytest.mark.asyncio
async def test_login_user_success_saves_refresh_token(db_session):
    user = await create_test_user(
        db_session,
        "login-success@example.com",
    )

    data = UserLoginSchema(
        email=user.email,
        password=PASSWORD,
    )

    result = await login_user(data, db_session)

    assert result["access_token"]
    assert result["refresh_token"]
    assert result["token_type"] == "bearer"

    token_hash = hash_token(result["refresh_token"])

    db_result = await db_session.execute(
        select(RefreshToken).where(
            RefreshToken.user_id == user.id,
            RefreshToken.token == token_hash,
        )
    )

    stored_token = db_result.scalar_one_or_none()

    assert stored_token is not None
    assert stored_token.user_id == user.id


@pytest.mark.asyncio
async def test_login_inactive_user(db_session):
    user = await create_test_user(
        db_session,
        "inactive-login@example.com",
        is_active=False,
    )

    data = UserLoginSchema(
        email=user.email,
        password=PASSWORD,
    )

    with pytest.raises(
        InactiveAccountError,
        match="Account is not activated",
    ):
        await login_user(data, db_session)


@pytest.mark.asyncio
async def test_refresh_token_not_stored(db_session):
    user = await create_test_user(
        db_session,
        "not-stored@example.com",
    )

    token = create_refresh_token(user.id)

    with pytest.raises(
        InvalidRefreshTokenError,
        match="Refresh token not found or revoked",
    ):
        await refresh_access_token(token, db_session)


@pytest.mark.asyncio
async def test_refresh_after_user_deactivation(db_session):
    user = await create_test_user(
        db_session,
        "deactivated@example.com",
    )

    token = create_refresh_token(user.id)

    stored_token = RefreshToken(
        user_id=user.id,
        token=hash_token(token),
        expires_at=datetime.now(timezone.utc) + timedelta(days=1),
    )

    db_session.add(stored_token)
    await db_session.commit()

    user.is_active = False
    await db_session.commit()

    with pytest.raises(
        InvalidRefreshTokenError,
        match="User not found or inactive",
    ):
        await refresh_access_token(token, db_session)


@pytest.mark.asyncio
async def test_refresh_token_with_naive_expiration(db_session):
    user = await create_test_user(
        db_session,
        "naive-expiration@example.com",
    )

    token = create_refresh_token(user.id)

    stored_token = RefreshToken(
        user_id=user.id,
        token=hash_token(token),
        expires_at=datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=1),
    )

    db_session.add(stored_token)
    await db_session.commit()

    new_access_token = await refresh_access_token(token, db_session)

    assert new_access_token


@pytest.mark.asyncio
async def test_login_rejects_password_when_verification_fails(
    db_session,
    monkeypatch,
):
    user = await create_test_user(
        db_session,
        "password-check@example.com",
    )

    monkeypatch.setattr(
        "src.services.auth.verify_password",
        lambda plain_password, hashed_password: False,
    )

    data = UserLoginSchema(
        email=user.email,
        password=PASSWORD,
    )

    with pytest.raises(
        InvalidCredentialsError,
        match="Invalid email or password",
    ):
        await login_user(data, db_session)


@pytest.mark.asyncio
async def test_login_user_not_found(db_session):
    data = UserLoginSchema(
        email="nonexistent-user@example.com",
        password=PASSWORD,
    )

    with pytest.raises(
        InvalidCredentialsError,
        match="Invalid email or password",
    ):
        await login_user(data, db_session)


@pytest.mark.asyncio
async def test_activate_user_with_invalid_token(db_session):
    with pytest.raises(
        InvalidActivationTokenError,
        match="Invalid activation token",
    ):
        await activate_user(
            "nonexistent-activation-token",
            db_session,
        )


@pytest.mark.asyncio
async def test_activate_user_with_expired_token(db_session):
    data = UserRegisterSchema(
        email="expired-service@example.com",
        password=PASSWORD,
    )

    user, token = await register_user(data, db_session)

    result = await db_session.execute(
        select(ActivationToken).where(ActivationToken.user_id == user.id)
    )

    activation = result.scalar_one()
    activation.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
    await db_session.commit()

    with pytest.raises(
        ExpiredActivationTokenError,
        match="Activation token has expired",
    ):
        await activate_user(token, db_session)


@pytest.mark.asyncio
async def test_register_user_duplicate_email(db_session):
    data = UserRegisterSchema(
        email="duplicate-service@example.com",
        password=PASSWORD,
    )

    await register_user(data, db_session)

    with pytest.raises(
        UserAlreadyExistsError,
        match="User with this email already exists",
    ):
        await register_user(data, db_session)
