from math import ceil

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models.movies import Movie
from src.schemas.movies import (
    MovieListItemSchema,
    MovieListResponseSchema,
)


async def get_movies(
    session: AsyncSession,
    page: int = 1,
    per_page: int = 10,
) -> MovieListResponseSchema:
    count_result = await session.execute(
        select(func.count(Movie.id))
    )

    total_items = count_result.scalar_one()
    total_pages = ceil(total_items / per_page)

    offset = (page - 1) * per_page

    result = await session.execute(
        select(Movie)
        .order_by(Movie.id)
        .offset(offset)
        .limit(per_page)
    )

    movies = result.scalars().all()

    prev_page = page - 1 if page > 1 else None
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
