from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from src.database.models.users import (
    ActivationToken,
    UserGroup,
    UserGroupEnum,
)
from src.schemas.users import UserRegisterSchema
from src.services.users import (
    InvalidActivationTokenError,
    activate_user,
    register_user,
    resend_activation_token,
)

PASSWORD = "CinemaTest2026!"


@pytest.mark.asyncio
async def test_register_creates_default_user_group(db_session):
    data = UserRegisterSchema(
        email="group@example.com",
        password=PASSWORD,
    )

    user, token = await register_user(data, db_session)

    result = await db_session.execute(
        select(UserGroup).where(UserGroup.name == UserGroupEnum.USER)
    )
    group = result.scalar_one()

    assert user.group_id == group.id
    assert user.is_active is False
    assert token


@pytest.mark.asyncio
async def test_register_reuses_existing_user_group(db_session):
    group = UserGroup(name=UserGroupEnum.USER)
    db_session.add(group)
    await db_session.commit()

    data = UserRegisterSchema(
        email="existing-group@example.com",
        password=PASSWORD,
    )

    user, _ = await register_user(data, db_session)

    result = await db_session.execute(
        select(UserGroup).where(UserGroup.name == UserGroupEnum.USER)
    )
    groups = result.scalars().all()

    assert len(groups) == 1
    assert user.group_id == group.id


@pytest.mark.asyncio
async def test_activate_token_with_missing_user(db_session):
    activation = ActivationToken(
        user_id=999999,
        token="orphan-activation-token",
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
    )

    db_session.add(activation)

    # Isolate the service branch from the database FK constraint.
    await db_session.flush()

    with pytest.raises(
        InvalidActivationTokenError,
        match="User not found",
    ):
        await activate_user(
            "orphan-activation-token",
            db_session,
        )


@pytest.mark.asyncio
async def test_resend_activation_for_active_user(db_session):
    data = UserRegisterSchema(
        email="active@example.com",
        password=PASSWORD,
    )

    user, token = await register_user(data, db_session)
    await activate_user(token, db_session)

    result = await resend_activation_token(
        user.email,
        db_session,
    )

    assert result is None

    activation_result = await db_session.execute(
        select(ActivationToken).where(ActivationToken.user_id == user.id)
    )

    assert activation_result.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_resend_creates_token_when_missing(db_session):
    data = UserRegisterSchema(
        email="missing-token@example.com",
        password=PASSWORD,
    )

    user, old_token = await register_user(data, db_session)

    result = await db_session.execute(
        select(ActivationToken).where(ActivationToken.token == old_token)
    )

    activation = result.scalar_one()
    await db_session.delete(activation)
    await db_session.commit()

    new_token = await resend_activation_token(
        user.email,
        db_session,
    )

    assert new_token is not None
    assert new_token != old_token

    result = await db_session.execute(
        select(ActivationToken).where(ActivationToken.token == new_token)
    )

    new_activation = result.scalar_one_or_none()

    assert new_activation is not None
    assert new_activation.user_id == user.id


@pytest.mark.asyncio
async def test_resend_updates_token_expiration(db_session):
    data = UserRegisterSchema(
        email="expiration@example.com",
        password=PASSWORD,
    )

    user, old_token = await register_user(data, db_session)

    new_token = await resend_activation_token(
        user.email,
        db_session,
    )

    result = await db_session.execute(
        select(ActivationToken).where(ActivationToken.user_id == user.id)
    )

    activation = result.scalar_one()

    expires_at = activation.expires_at

    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    expected_expiration = datetime.now(timezone.utc) + timedelta(hours=24)

    assert new_token != old_token
    assert activation.token == new_token
    assert abs((expires_at - expected_expiration).total_seconds()) < 10
