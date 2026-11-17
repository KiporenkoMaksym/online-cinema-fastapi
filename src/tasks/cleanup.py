import asyncio
import os

from sqlalchemy import delete, func
from sqlalchemy.ext.asyncio import create_async_engine

from src.database.models.users import ActivationToken
from src.tasks.celery_app import celery_app


async def cleanup_expired_tokens() -> int:
    database_url = os.environ["DATABASE_URL"]

    engine = create_async_engine(database_url)

    try:
        async with engine.begin() as connection:
            result = await connection.execute(
                delete(ActivationToken).where(
                    ActivationToken.expires_at <= func.now()
                )
            )

            return result.rowcount

    finally:
        await engine.dispose()


@celery_app.task(
    name="src.tasks.cleanup.delete_expired_activation_tokens"
)
def delete_expired_activation_tokens() -> int:
    deleted_count = asyncio.run(cleanup_expired_tokens())

    print(f"Deleted expired tokens: {deleted_count}")

    return deleted_count
