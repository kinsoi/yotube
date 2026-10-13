import logging

from app.main import RedactOAuthCallback, configure_logging


def access_record(path: str) -> logging.LogRecord:
    return logging.LogRecord(
        "uvicorn.access",
        logging.INFO,
        __file__,
        1,
        '%s - "%s %s HTTP/%s" %d',
        ("10.0.0.2:5000", "GET", path, "1.1", 303),
        None,
    )


def test_callback_query_string_is_redacted() -> None:
    record = access_record("/auth/callback?code=secret-code&state=s1")
    assert RedactOAuthCallback().filter(record) is True
    assert "secret-code" not in record.getMessage()
    assert "/auth/callback?[redacted]" in record.getMessage()


def test_other_paths_are_left_alone() -> None:
    record = access_record("/api/search?q=lion")
    RedactOAuthCallback().filter(record)
    assert "/api/search?q=lion" in record.getMessage()


def test_configure_logging_quiets_httpx_and_filters_access_log_once() -> None:
    configure_logging("INFO")
    configure_logging("INFO")
    assert logging.getLogger("httpx").level == logging.WARNING
    assert logging.getLogger("httpcore").level == logging.WARNING
    access = logging.getLogger("uvicorn.access")
    assert sum(isinstance(f, RedactOAuthCallback) for f in access.filters) == 1
