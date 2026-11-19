import pytest

from pwdlib import PasswordHash

from src.database.models.users import (
    User,
    UserGroup,
    UserGroupEnum,
)
from src.security.jwt import create_access_token


MOVIE_DATA = {
    "name": "Test Movie",
    "description": "Movie created during tests",
    "release_date": "2025-01-01",
    "duration": 120,
    "rating": 8.5,
}


async def create_test_user(db_session, role, email):
    group = UserGroup(name=role)

    db_session.add(group)
    await db_session.flush()

    user = User(
        email=email,
        hashed_password=PasswordHash.recommended().hash(
            "CinemaTest2026!"
        ),
        is_active=True,
        group_id=group.id,
    )

    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    return user


@pytest.mark.asyncio
async def test_create_movie_without_token(client):
    response = await client.post(
        "/api/v1/movies/",
        json=MOVIE_DATA,
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_user_cannot_create_movie(client, db_session):
    user = await create_test_user(
        db_session,
        UserGroupEnum.USER,
        "normal.user@example.com",
    )

    token = create_access_token(user.id)

    response = await client.post(
        "/api/v1/movies/",
        json=MOVIE_DATA,
        headers={
            "Authorization": f"Bearer {token}"
        },
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_moderator_can_manage_movies(
    client,
    db_session,
):
    moderator = await create_test_user(
        db_session,
        UserGroupEnum.MODERATOR,
        "moderator@example.com",
    )

    token = create_access_token(moderator.id)

    headers = {
        "Authorization": f"Bearer {token}"
    }

    # Create
    create_response = await client.post(
        "/api/v1/movies/",
        json=MOVIE_DATA,
        headers=headers,
    )

    assert create_response.status_code == 201

    movie_id = create_response.json()["id"]

    # Update
    updated_data = {
        **MOVIE_DATA,
        "name": "Updated Movie",
        "rating": 9.5,
    }

    update_response = await client.put(
        f"/api/v1/movies/{movie_id}/",
        json=updated_data,
        headers=headers,
    )

    assert update_response.status_code == 200
    assert update_response.json()["name"] == "Updated Movie"

    # Delete
    delete_response = await client.delete(
        f"/api/v1/movies/{movie_id}/",
        headers=headers,
    )

    assert delete_response.status_code == 204

    # Verify deletion
    get_response = await client.get(
        f"/api/v1/movies/{movie_id}/"
    )

    assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_admin_can_create_movie(client, db_session):
    admin = await create_test_user(
        db_session,
        UserGroupEnum.ADMIN,
        "admin@example.com",
    )

    token = create_access_token(admin.id)

    response = await client.post(
        "/api/v1/movies/",
        json=MOVIE_DATA,
        headers={
            "Authorization": f"Bearer {token}"
        },
    )

    assert response.status_code == 201
    assert response.json()["name"] == "Test Movie"
