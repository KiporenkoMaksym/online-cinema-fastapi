from datetime import date

import pytest

from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models.movies import Movie


@pytest.fixture
def movie_data():
    return [
        {
            "name": "Interstellar",
            "description": "Science fiction movie",
            "release_date": "2014-11-07",
            "duration": 169,
            "rating": 8.7,
        },
        {
            "name": "Inception",
            "description": "Science fiction thriller",
            "release_date": "2010-07-16",
            "duration": 148,
            "rating": 8.8,
        },
        {
            "name": "The Matrix",
            "description": "Science fiction action",
            "release_date": "1999-03-31",
            "duration": 136,
            "rating": 8.7,
        },
    ]


@pytest.mark.asyncio
async def test_get_empty_movie_catalog(client):
    response = await client.get("/api/v1/movies/")

    assert response.status_code == 200

    data = response.json()

    assert data["movies"] == []
    assert data["total_items"] == 0
    assert data["total_pages"] == 0
    assert data["next_page"] is None


@pytest.mark.asyncio
async def test_get_movie_catalog(
    client,
    db_session: AsyncSession,
):
    movie = Movie(
        name="Interstellar",
        description="Science fiction movie",
        release_date=__import__("datetime").date(2014, 11, 7),
        duration=169,
        rating=8.7,
    )

    db_session.add(movie)
    await db_session.commit()

    response = await client.get("/api/v1/movies/")

    assert response.status_code == 200

    data = response.json()

    assert data["total_items"] == 1
    assert len(data["movies"]) == 1
    assert data["movies"][0]["name"] == "Interstellar"


@pytest.mark.asyncio
async def test_movie_not_found(client):
    response = await client.get("/api/v1/movies/999999/")

    assert response.status_code == 404
    assert response.json()["detail"] == "Movie not found"


@pytest.mark.asyncio
async def test_invalid_pagination(client):
    response = await client.get("/api/v1/movies/?page=0&per_page=10")

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_per_page_limit(client):
    response = await client.get("/api/v1/movies/?page=1&per_page=100")

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_search_movies(client, db_session):
    movies = [
        Movie(
            name="Interstellar",
            description="Space adventure",
            release_date=date(2014, 11, 7),
            duration=169,
            rating=8.7,
        ),
        Movie(
            name="Inception",
            description="Dream thriller",
            release_date=date(2010, 7, 16),
            duration=148,
            rating=8.8,
        ),
    ]

    db_session.add_all(movies)
    await db_session.commit()

    response = await client.get("/api/v1/movies/?search=interstellar")

    assert response.status_code == 200
    assert response.json()["total_items"] == 1
    assert response.json()["movies"][0]["name"] == "Interstellar"


@pytest.mark.asyncio
async def test_filter_movies_by_rating(client, db_session):
    movies = [
        Movie(
            name="Movie A",
            release_date=date(2020, 1, 1),
            duration=120,
            rating=9.0,
        ),
        Movie(
            name="Movie B",
            release_date=date(2021, 1, 1),
            duration=110,
            rating=7.0,
        ),
    ]

    db_session.add_all(movies)
    await db_session.commit()

    response = await client.get("/api/v1/movies/?min_rating=8")

    assert response.status_code == 200
    assert response.json()["total_items"] == 1
    assert response.json()["movies"][0]["name"] == "Movie A"


@pytest.mark.asyncio
async def test_sort_movies_by_rating(client, db_session):
    movies = [
        Movie(
            name="Movie A",
            release_date=date(2020, 1, 1),
            duration=120,
            rating=7.0,
        ),
        Movie(
            name="Movie B",
            release_date=date(2021, 1, 1),
            duration=110,
            rating=9.0,
        ),
    ]

    db_session.add_all(movies)
    await db_session.commit()

    response = await client.get("/api/v1/movies/?sort_by=rating&sort_order=desc")

    assert response.status_code == 200

    names = [movie["name"] for movie in response.json()["movies"]]

    assert names == ["Movie B", "Movie A"]


@pytest.mark.asyncio
async def test_filter_movies_by_release_date(
    client,
    db_session,
):
    movies = [
        Movie(
            name="Old Movie",
            release_date=date(2000, 1, 1),
            duration=100,
            rating=7.0,
        ),
        Movie(
            name="New Movie",
            release_date=date(2023, 1, 1),
            duration=120,
            rating=8.0,
        ),
    ]

    db_session.add_all(movies)
    await db_session.commit()

    response = await client.get("/api/v1/movies/?release_date_from=2020-01-01")

    assert response.status_code == 200
    assert response.json()["total_items"] == 1
    assert response.json()["movies"][0]["name"] == "New Movie"
