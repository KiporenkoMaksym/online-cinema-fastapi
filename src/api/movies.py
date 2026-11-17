from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.session import get_db
from src.schemas.movies import MovieListResponseSchema
from src.services.movies import get_movies


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
