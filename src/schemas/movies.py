from datetime import date

from pydantic import BaseModel, ConfigDict, Field, field_validator


class MovieListItemSchema(BaseModel):
    id: int
    name: str
    description: str | None
    release_date: date
    duration: int
    rating: float | None

    model_config = ConfigDict(from_attributes=True)


class MovieDetailSchema(MovieListItemSchema):
    pass


class MovieListResponseSchema(BaseModel):
    movies: list[MovieListItemSchema]
    total_items: int = Field(ge=0)
    total_pages: int = Field(ge=0)
    prev_page: int | None = None
    next_page: int | None = None


class MovieCreateSchema(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    release_date: date
    duration: int = Field(gt=0)
    rating: float | None = Field(
        default=None,
        ge=0,
        le=10,
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError("Movie name cannot be empty")

        return value


class MovieUpdateSchema(MovieCreateSchema):
    pass
