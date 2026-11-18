from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.session import get_db
from src.schemas.movies import MovieListResponseSchema, MovieDetailSchema
from src.services.movies import get_movies, get_movie_by_id

router = APIRouter(
    prefix="/api/v1/movies",
    tags=["Movies"],
)


@router.get(
    "/",
    response_model=MovieListResponseSchema,
    summary="Get movies with search and filters",
)
async def list_movies(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=10, ge=1, le=20),
    search: str | None = Query(
        default=None,
        max_length=255,
    ),
    min_rating: float | None = Query(
        default=None,
        ge=0,
        le=10,
    ),
    release_date_from: date | None = None,
    release_date_to: date | None = None,
    sort_by: Literal[
        "id", "name", "release_date", "rating"
    ] = "id",
    sort_order: Literal["asc", "desc"] = "asc",
    session: AsyncSession = Depends(get_db),
):
    if (
        release_date_from is not None
        and release_date_to is not None
        and release_date_from > release_date_to
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Invalid release date range",
        )

    return await get_movies(
        session=session,
        page=page,
        per_page=per_page,
        search=search,
        min_rating=min_rating,
        release_date_from=release_date_from,
        release_date_to=release_date_to,
        sort_by=sort_by,
        sort_order=sort_order,
    )


@router.get(
    "/{movie_id}/",
    response_model=MovieDetailSchema,
    summary="Get movie details",
    responses={
        404: {"description": "Movie not found"},
    },
)
async def movie_details(
    movie_id: int,
    session: AsyncSession = Depends(get_db),
):
    movie = await get_movie_by_id(
        session=session,
        movie_id=movie_id,
    )

    if movie is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Movie not found",
        )

    return movie
