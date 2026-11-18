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
    summary="Get movie catalog",
)
async def list_movies(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=10, ge=1, le=20),
    session: AsyncSession = Depends(get_db),
):
    return await get_movies(
        session=session,
        page=page,
        per_page=per_page,
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
