from datetime import date
from math import ceil
from typing import Literal

from sqlalchemy import func, select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models.movies import Movie
from src.schemas.movies import (
    MovieListItemSchema,
    MovieListResponseSchema,
    MovieDetailSchema, MovieUpdateSchema, MovieCreateSchema,
)


async def get_movies(
    session: AsyncSession,
    page: int = 1,
    per_page: int = 10,
    search: str | None = None,
    min_rating: float | None = None,
    release_date_from: date | None = None,
    release_date_to: date | None = None,
    sort_by: Literal[
        "id", "name", "release_date", "rating"
    ] = "id",
    sort_order: Literal["asc", "desc"] = "asc",
) -> MovieListResponseSchema:

    filters = []
    if search:
        search_value = f"%{search.strip()}%"

        filters.append(
            or_(
                Movie.name.ilike(search_value),
                Movie.description.ilike(search_value),
            )
        )

    if min_rating is not None:
        filters.append(
            Movie.rating >= min_rating
        )

    if release_date_from is not None:
        filters.append(
            Movie.release_date >= release_date_from
        )

    if release_date_to is not None:
        filters.append(
            Movie.release_date <= release_date_to
        )

    count_result = await session.execute(
        select(func.count(Movie.id)).where(*filters)
    )

    total_items = count_result.scalar_one()
    total_pages = ceil(total_items / per_page)

    sort_columns = {
        "id": Movie.id,
        "name": Movie.name,
        "release_date": Movie.release_date,
        "rating": Movie.rating,
    }

    sort_column = sort_columns[sort_by]

    if sort_order == "desc":
        sort_column = sort_column.desc()
    else:
        sort_column = sort_column.asc()

    offset = (page - 1) * per_page

    result = await session.execute(
        select(Movie)
        .where(*filters)
        .order_by(sort_column, Movie.id)
        .offset(offset)
        .limit(per_page)
    )

    movies = result.scalars().all()

    prev_page = (
        page - 1
        if 1 < page <= total_pages
        else None
    )

    next_page = (
        page + 1
        if page < total_pages
        else None
    )

    return MovieListResponseSchema(
        movies=[
            MovieListItemSchema.model_validate(movie)
            for movie in movies
        ],
        total_items=total_items,
        total_pages=total_pages,
        prev_page=prev_page,
        next_page=next_page,
    )


async def get_movie_by_id(
    session: AsyncSession,
    movie_id: int,
) -> MovieDetailSchema | None:
    result = await session.execute(
        select(Movie).where(Movie.id == movie_id)
    )

    movie = result.scalar_one_or_none()

    if movie is None:
        return None

    return MovieDetailSchema.model_validate(movie)


async def create_movie(
    session: AsyncSession,
    data: MovieCreateSchema,
) -> Movie:
    movie = Movie(**data.model_dump())

    session.add(movie)
    await session.commit()
    await session.refresh(movie)

    return movie


async def update_movie(
    session: AsyncSession,
    movie_id: int,
    data: MovieUpdateSchema,
) -> Movie | None:
    movie = await session.get(Movie, movie_id)

    if movie is None:
        return None

    for field, value in data.model_dump().items():
        setattr(movie, field, value)

    await session.commit()
    await session.refresh(movie)

    return movie


async def delete_movie(
    session: AsyncSession,
    movie_id: int,
) -> bool:
    movie = await session.get(Movie, movie_id)

    if movie is None:
        return False

    await session.delete(movie)
    await session.commit()

    return True
