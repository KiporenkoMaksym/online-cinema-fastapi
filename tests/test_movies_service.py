from datetime import date

import pytest

from src.database.models.movies import Movie
from src.schemas.movies import MovieCreateSchema, MovieUpdateSchema
from src.services.movies import (
    get_movies,
    get_movie_by_id,
    create_movie,
    update_movie,
    delete_movie,
)


@pytest.mark.asyncio
async def test_create_movie_service(db_session):
    data = MovieCreateSchema(
        name="Interstellar",
        description="Science fiction",
        release_date=date(2014, 11, 7),
        duration=169,
        rating=8.7,
    )

    movie = await create_movie(db_session, data)

    assert movie.id is not None
    assert movie.name == "Interstellar"

    saved_movie = await db_session.get(Movie, movie.id)

    assert saved_movie is not None
    assert saved_movie.rating == 8.7


@pytest.mark.asyncio
async def test_get_movie_by_id_success(db_session):
    movie = Movie(
        name="Inception",
        release_date=date(2010, 7, 16),
        duration=148,
        rating=8.8,
    )

    db_session.add(movie)
    await db_session.commit()

    result = await get_movie_by_id(db_session, movie.id)

    assert result is not None
    assert result.id == movie.id
    assert result.name == "Inception"


@pytest.mark.asyncio
async def test_get_movie_by_id_not_found(db_session):
    result = await get_movie_by_id(db_session, 999999)

    assert result is None


@pytest.mark.asyncio
async def test_update_movie_success(db_session):
    movie = Movie(
        name="Old Name",
        release_date=date(2020, 1, 1),
        duration=100,
        rating=6.0,
    )

    db_session.add(movie)
    await db_session.commit()

    data = MovieUpdateSchema(
        name="Updated Name",
        description="Updated description",
        release_date=date(2021, 1, 1),
        duration=130,
        rating=9.0,
    )

    updated = await update_movie(db_session, movie.id, data)

    assert updated is not None
    assert updated.name == "Updated Name"
    assert updated.description == "Updated description"
    assert updated.duration == 130
    assert updated.rating == 9.0

    await db_session.refresh(movie)
    assert movie.name == "Updated Name"


@pytest.mark.asyncio
async def test_update_movie_not_found(db_session):
    data = MovieUpdateSchema(
        name="Missing Movie",
        release_date=date(2022, 1, 1),
        duration=100,
    )

    result = await update_movie(
        db_session,
        999999,
        data,
    )

    assert result is None


@pytest.mark.asyncio
async def test_delete_movie_success(db_session):
    movie = Movie(
        name="Movie To Delete",
        release_date=date(2022, 1, 1),
        duration=110,
    )

    db_session.add(movie)
    await db_session.commit()

    movie_id = movie.id

    result = await delete_movie(db_session, movie_id)

    assert result is True

    deleted_movie = await db_session.get(Movie, movie_id)
    assert deleted_movie is None


@pytest.mark.asyncio
async def test_delete_movie_not_found(db_session):
    result = await delete_movie(db_session, 999999)

    assert result is False


@pytest.mark.asyncio
async def test_movies_pagination(db_session):
    for index in range(5):
        db_session.add(
            Movie(
                name=f"Movie {index}",
                release_date=date(2020, 1, 1),
                duration=100,
                rating=7.0,
            )
        )

    await db_session.commit()

    first_page = await get_movies(
        db_session,
        page=1,
        per_page=2,
    )

    assert first_page.total_items == 5
    assert first_page.total_pages == 3
    assert len(first_page.movies) == 2
    assert first_page.prev_page is None
    assert first_page.next_page == 2

    second_page = await get_movies(
        db_session,
        page=2,
        per_page=2,
    )

    assert second_page.prev_page == 1
    assert second_page.next_page == 3

    last_page = await get_movies(
        db_session,
        page=3,
        per_page=2,
    )

    assert len(last_page.movies) == 1
    assert last_page.prev_page == 2
    assert last_page.next_page is None


@pytest.mark.asyncio
async def test_filter_movies_by_end_date(db_session):
    db_session.add_all(
        [
            Movie(
                name="Old Movie",
                release_date=date(2010, 1, 1),
                duration=100,
            ),
            Movie(
                name="New Movie",
                release_date=date(2025, 1, 1),
                duration=120,
            ),
        ]
    )

    await db_session.commit()

    result = await get_movies(
        db_session,
        release_date_to=date(2020, 1, 1),
    )

    assert result.total_items == 1
    assert result.movies[0].name == "Old Movie"


@pytest.mark.asyncio
async def test_search_movie_by_description(db_session):
    db_session.add_all(
        [
            Movie(
                name="Movie A",
                description="Space exploration",
                release_date=date(2020, 1, 1),
                duration=120,
            ),
            Movie(
                name="Movie B",
                description="Romantic comedy",
                release_date=date(2021, 1, 1),
                duration=100,
            ),
        ]
    )

    await db_session.commit()

    result = await get_movies(
        db_session,
        search="space",
    )

    assert result.total_items == 1
    assert result.movies[0].name == "Movie A"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "sort_by,expected_names",
    [
        ("name", ["Alpha", "Beta"]),
        ("release_date", ["Beta", "Alpha"]),
        ("rating", ["Beta", "Alpha"]),
    ],
)
async def test_movies_sorting_ascending(
    db_session,
    sort_by,
    expected_names,
):
    db_session.add_all(
        [
            Movie(
                name="Alpha",
                release_date=date(2022, 1, 1),
                duration=100,
                rating=9.0,
            ),
            Movie(
                name="Beta",
                release_date=date(2020, 1, 1),
                duration=120,
                rating=7.0,
            ),
        ]
    )

    await db_session.commit()

    result = await get_movies(
        db_session,
        sort_by=sort_by,
        sort_order="asc",
    )

    assert [movie.name for movie in result.movies] == expected_names
