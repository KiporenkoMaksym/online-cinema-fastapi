import pytest
from pwdlib import PasswordHash

from src.database.models import User, UserGroup, UserGroupEnum
from src.security.jwt import (
    create_access_token,
    create_refresh_token,
    decode_access_token,
    decode_refresh_token,
)


def test_create_and_decode_access_token():
    token = create_access_token(user_id=1)

    payload = decode_access_token(token)

    assert payload["sub"] == "1"
    assert payload["type"] == "access"
    assert "exp" in payload


def test_create_and_decode_refresh_token():
    token = create_refresh_token(user_id=1)

    payload = decode_refresh_token(token)

    assert payload["sub"] == "1"
    assert payload["type"] == "refresh"
    assert "jti" in payload


@pytest.mark.asyncio
async def test_get_me_without_token(client):
    response = await client.get("/api/v1/accounts/me/")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_me_with_invalid_token(client):
    response = await client.get(
        "/api/v1/accounts/me/",
        headers={"Authorization": "Bearer invalid-token"},
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_refresh_with_invalid_token(client):
    response = await client.post(
        "/api/v1/accounts/token/refresh/",
        json={"refresh_token": "invalid-refresh-token"},
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_logout_with_invalid_token(client):
    response = await client.post(
        "/api/v1/accounts/logout/",
        json={"refresh_token": "invalid-refresh-token"},
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_with_invalid_credentials(client):
    response = await client.post(
        "/api/v1/accounts/login/",
        json={
            "email": "nonexistent@example.com",
            "password": "WrongPassword123!",
        },
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_full_authentication_flow(client, db_session):
    password = "CinemaTest2026!"

    # Create a test user
    group = UserGroup(name=UserGroupEnum.USER)
    db_session.add(group)
    await db_session.flush()

    user = User(
        email="auth.test@example.com",
        hashed_password=PasswordHash.recommended().hash(password),
        is_active=True,
        group_id=group.id,
    )

    db_session.add(user)
    await db_session.commit()

    # 1. Login
    login_response = await client.post(
        "/api/v1/accounts/login/",
        json={
            "email": user.email,
            "password": password,
        },
    )

    assert login_response.status_code == 200

    tokens = login_response.json()

    access_token = tokens["access_token"]
    refresh_token = tokens["refresh_token"]

    assert access_token
    assert refresh_token

    # 2. Get current user
    me_response = await client.get(
        "/api/v1/accounts/me/",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert me_response.status_code == 200
    assert me_response.json()["email"] == user.email

    # 3. Refresh access token
    refresh_response = await client.post(
        "/api/v1/accounts/token/refresh/",
        json={"refresh_token": refresh_token},
    )

    assert refresh_response.status_code == 200
    assert refresh_response.json()["access_token"]

    # 4. Logout
    logout_response = await client.post(
        "/api/v1/accounts/logout/",
        json={"refresh_token": refresh_token},
    )

    assert logout_response.status_code == 200

    # 5. Try to reuse revoked refresh token
    revoked_response = await client.post(
        "/api/v1/accounts/token/refresh/",
        json={"refresh_token": refresh_token},
    )

    assert revoked_response.status_code == 401
