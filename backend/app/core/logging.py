import logging

from app.core.config import settings


def configure_logging() -> None:
    """Configure root logging once at application startup."""
    level = logging.DEBUG if settings.DEBUG else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    )
