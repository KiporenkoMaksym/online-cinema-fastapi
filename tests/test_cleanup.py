import importlib
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

cleanup_module = importlib.import_module("src.tasks.cleanup")


@pytest.mark.asyncio
async def test_cleanup_expired_tokens(
    monkeypatch,
):
    # Fake database connection
    connection = MagicMock()
    connection.execute = AsyncMock(return_value=SimpleNamespace(rowcount=3))

    # Fake engine
    engine = MagicMock()
    engine.begin.return_value.__aenter__ = AsyncMock(return_value=connection)
    engine.begin.return_value.__aexit__ = AsyncMock(return_value=None)
    engine.dispose = AsyncMock()

    monkeypatch.setenv(
        "DATABASE_URL",
        "sqlite+aiosqlite:///:memory:",
    )

    monkeypatch.setattr(
        cleanup_module,
        "create_async_engine",
        lambda url: engine,
    )

    result = await cleanup_module.cleanup_expired_tokens()

    assert result == 3

    connection.execute.assert_awaited_once()

    statement = connection.execute.await_args.args[0]

    assert "DELETE FROM activation_tokens" in str(statement)

    engine.dispose.assert_awaited_once()


@pytest.mark.asyncio
async def test_cleanup_when_no_expired_tokens(
    monkeypatch,
):
    connection = MagicMock()
    connection.execute = AsyncMock(return_value=SimpleNamespace(rowcount=0))

    engine = MagicMock()
    engine.begin.return_value.__aenter__ = AsyncMock(return_value=connection)
    engine.begin.return_value.__aexit__ = AsyncMock(return_value=None)
    engine.dispose = AsyncMock()

    monkeypatch.setenv(
        "DATABASE_URL",
        "sqlite+aiosqlite:///:memory:",
    )

    monkeypatch.setattr(
        cleanup_module,
        "create_async_engine",
        lambda url: engine,
    )

    result = await cleanup_module.cleanup_expired_tokens()

    assert result == 0
    engine.dispose.assert_awaited_once()


@pytest.mark.asyncio
async def test_cleanup_disposes_engine_on_error(
    monkeypatch,
):
    connection = MagicMock()
    connection.execute = AsyncMock(side_effect=RuntimeError("Database error"))

    engine = MagicMock()
    engine.begin.return_value.__aenter__ = AsyncMock(return_value=connection)
    engine.begin.return_value.__aexit__ = AsyncMock(return_value=None)
    engine.dispose = AsyncMock()

    monkeypatch.setenv(
        "DATABASE_URL",
        "sqlite+aiosqlite:///:memory:",
    )

    monkeypatch.setattr(
        cleanup_module,
        "create_async_engine",
        lambda url: engine,
    )

    with pytest.raises(RuntimeError, match="Database error"):
        await cleanup_module.cleanup_expired_tokens()

    engine.dispose.assert_awaited_once()


def test_celery_cleanup_task(monkeypatch):
    mock_cleanup = AsyncMock(return_value=2)

    monkeypatch.setattr(
        cleanup_module,
        "cleanup_expired_tokens",
        mock_cleanup,
    )

    result = cleanup_module.delete_expired_activation_tokens.run()

    assert result == 2
    mock_cleanup.assert_awaited_once()
