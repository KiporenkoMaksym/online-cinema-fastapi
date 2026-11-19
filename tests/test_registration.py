from datetime import timedelta, timezone, datetime

import pytest
from sqlalchemy import select

from src.database.models import ActivationToken, User

REGISTER_URL = "/api/v1/accounts/register/"


@pytest.mark.asyncio
async def test_register_with_invalid_email(client):
    response = await client.post(
        REGISTER_URL,
        json={
            "email": "invalid-email",
            "password": "CinemaTest2026!",
        },
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_register_with_short_password(client):
    response = await client.post(
        REGISTER_URL,
        json={
            "email": "test@example.com",
            "password": "123",
        },
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_register_without_password(client):
    response = await client.post(
        REGISTER_URL,
        json={
            "email": "test@example.com",
        },
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_register_without_email(client):
    response = await client.post(
        REGISTER_URL,
        json={
            "password": "CinemaTest2026!",
        },
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_register_user_success(
    client,
    db_session,
    monkeypatch,
):
    sent_emails = []

    async def mock_send_activation_email(
        recipient: str,
        token: str,
    ):
        sent_emails.append({
            "recipient": recipient,
            "token": token,
        })

    monkeypatch.setattr(
        "src.api.auth.send_activation_email",
        mock_send_activation_email,
    )

    response = await client.post(
        REGISTER_URL,
        json={
            "email": "newuser@example.com",
            "password": "CinemaTest2026!",
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data["email"] == "newuser@example.com"
    assert data["is_active"] is False

    result = await db_session.execute(
        select(User).where(
            User.email == "newuser@example.com"
        )
    )

    user = result.scalar_one_or_none()

    assert user is not None
    assert user.is_active is False

    result = await db_session.execute(
        select(ActivationToken).where(
            ActivationToken.user_id == user.id
        )
    )

    activation = result.scalar_one_or_none()

    assert activation is not None
    assert len(sent_emails) == 1
    assert sent_emails[0]["recipient"] == user.email
    assert sent_emails[0]["token"] == activation.token


@pytest.mark.asyncio
async def test_register_duplicate_email(
    client,
    monkeypatch,
):
    async def mock_send_activation_email(
        recipient: str,
        token: str,
    ):
        pass

    monkeypatch.setattr(
        "src.api.auth.send_activation_email",
        mock_send_activation_email,
    )

    user_data = {
        "email": "duplicate@example.com",
        "password": "CinemaTest2026!",
    }

    first_response = await client.post(
        REGISTER_URL,
        json=user_data,
    )

    assert first_response.status_code == 201

    second_response = await client.post(
        REGISTER_URL,
        json=user_data,
    )

    assert second_response.status_code == 409

    assert second_response.json()["detail"] == (
        "User with this email already exists"
    )


@pytest.mark.asyncio
async def test_activate_with_invalid_token(client):
    response = await client.get(
        "/api/v1/accounts/activate/",
        params={
            "token": "invalid-activation-token"
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "Invalid activation token"
    )


@pytest.mark.asyncio
async def test_register_activate_and_login(
    client,
    db_session,
    monkeypatch,
):
    activation_tokens = []

    async def mock_send_activation_email(
        recipient: str,
        token: str,
    ):
        activation_tokens.append(token)

    monkeypatch.setattr(
        "src.api.auth.send_activation_email",
        mock_send_activation_email,
    )

    email = "activation.test@example.com"
    password = "CinemaTest2026!"

    # 1. Register
    register_response = await client.post(
        REGISTER_URL,
        json={
            "email": email,
            "password": password,
        },
    )

    assert register_response.status_code == 201
    assert register_response.json()["is_active"] is False
    assert len(activation_tokens) == 1

    # 2. Login before activation must be forbidden
    inactive_login_response = await client.post(
        "/api/v1/accounts/login/",
        json={
            "email": email,
            "password": password,
        },
    )

    assert inactive_login_response.status_code == 403

    # 3. Activate account
    activation_response = await client.get(
        "/api/v1/accounts/activate/",
        params={"token": activation_tokens[0]},
    )

    assert activation_response.status_code == 200

    # 4. Login after activation
    login_response = await client.post(
        "/api/v1/accounts/login/",
        json={
            "email": email,
            "password": password,
        },
    )

    assert login_response.status_code == 200

    tokens = login_response.json()
    assert tokens["access_token"]
    assert tokens["refresh_token"]


@pytest.mark.asyncio
async def test_cannot_reuse_activation_token(
    client,
    monkeypatch,
):
    tokens = []

    async def mock_send_activation_email(
        recipient: str,
        token: str,
    ):
        tokens.append(token)

    monkeypatch.setattr(
        "src.api.auth.send_activation_email",
        mock_send_activation_email,
    )

    await client.post(
        REGISTER_URL,
        json={
            "email": "reuse.test@example.com",
            "password": "CinemaTest2026!",
        },
    )

    assert len(tokens) == 1

    first_response = await client.get(
        "/api/v1/accounts/activate/",
        params={"token": tokens[0]},
    )

    assert first_response.status_code == 200

    second_response = await client.get(
        "/api/v1/accounts/activate/",
        params={"token": tokens[0]},
    )

    assert second_response.status_code == 400
    assert second_response.json()["detail"] == (
        "Invalid activation token"
    )


@pytest.mark.asyncio
async def test_expired_activation_token(
    client,
    db_session,
    monkeypatch,
):
    tokens = []

    async def mock_send_activation_email(
        recipient: str,
        token: str,
    ):
        tokens.append(token)

    monkeypatch.setattr(
        "src.api.auth.send_activation_email",
        mock_send_activation_email,
    )

    await client.post(
        REGISTER_URL,
        json={
            "email": "expired.test@example.com",
            "password": "CinemaTest2026!",
        },
    )

    assert len(tokens) == 1

    result = await db_session.execute(
        select(ActivationToken).where(
            ActivationToken.token == tokens[0]
        )
    )

    activation = result.scalar_one()
    activation.expires_at = (
        datetime.now(timezone.utc) - timedelta(hours=1)
    )

    await db_session.commit()

    response = await client.get(
        "/api/v1/accounts/activate/",
        params={"token": tokens[0]},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "Activation token has expired"
    )


@pytest.mark.asyncio
async def test_resend_activation(
    client,
    db_session,
    monkeypatch,
):
    sent_tokens = []

    async def mock_send_activation_email(
        recipient: str,
        token: str,
    ):
        sent_tokens.append(token)

    monkeypatch.setattr(
        "src.api.auth.send_activation_email",
        mock_send_activation_email,
    )

    email = "resend.test@example.com"

    register_response = await client.post(
        "/api/v1/accounts/register/",
        json={
            "email": email,
            "password": "CinemaTest2026!",
        },
    )

    assert register_response.status_code == 201
    assert len(sent_tokens) == 1

    old_token = sent_tokens[0]

    response = await client.post(
        "/api/v1/accounts/resend-activation/",
        json={"email": email},
    )

    assert response.status_code == 200
    assert len(sent_tokens) == 2

    new_token = sent_tokens[1]

    assert new_token != old_token

    # Old activation token must no longer work
    old_response = await client.get(
        "/api/v1/accounts/activate/",
        params={"token": old_token},
    )

    assert old_response.status_code == 400

    # New activation token must work
    new_response = await client.get(
        "/api/v1/accounts/activate/",
        params={"token": new_token},
    )

    assert new_response.status_code == 200


@pytest.mark.asyncio
async def test_resend_activation_unknown_email(
    client,
    monkeypatch,
):
    sent_emails = []

    async def mock_send_activation_email(
        recipient: str,
        token: str,
    ):
        sent_emails.append(recipient)

    monkeypatch.setattr(
        "src.api.auth.send_activation_email",
        mock_send_activation_email,
    )

    response = await client.post(
        "/api/v1/accounts/resend-activation/",
        json={
            "email": "unknown@example.com"
        },
    )

    assert response.status_code == 200
    assert sent_emails == []
