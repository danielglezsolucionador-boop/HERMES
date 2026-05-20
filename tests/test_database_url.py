from app.db.engine import normalize_database_url


def test_normalize_render_postgres_url_to_asyncpg():
    raw = "postgres://user:pass@example.railway.internal:5432/railway"

    assert (
        normalize_database_url(raw)
        == "postgresql+asyncpg://user:pass@example.railway.internal:5432/railway"
    )


def test_normalize_postgresql_url_to_asyncpg():
    raw = "postgresql://user:pass@example.com:5432/hermes"

    assert (
        normalize_database_url(raw)
        == "postgresql+asyncpg://user:pass@example.com:5432/hermes"
    )


def test_preserve_asyncpg_url():
    raw = "postgresql+asyncpg://user:pass@example.com:5432/hermes"

    assert normalize_database_url(raw) == raw
