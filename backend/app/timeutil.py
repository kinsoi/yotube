from datetime import UTC, datetime


def utcnow() -> datetime:
    """Current time as a naive UTC datetime (SQLite stores naive datetimes)."""
    return datetime.now(UTC).replace(tzinfo=None)
