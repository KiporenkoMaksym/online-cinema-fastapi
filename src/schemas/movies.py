from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class MovieListItemSchema(BaseModel):
    id: int
    name: str
    description: str | None
    release_date: date
    duration: int
    rating: float | None

    model_config = ConfigDict(from_attributes=True)


class MovieListResponseSchema(BaseModel):
    movies: list[MovieListItemSchema]
    total_items: int = Field(ge=0)
    total_pages: int = Field(ge=0)
    prev_page: int | None = None
    next_page: int | None = None
