import logging
import sys

from app.core.config import settings


def setup_logging() -> logging.Logger:
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    if settings.LOG_FORMAT == 'json':
        fmt = '{"time":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s","msg":"%(message)s"}'
    else:
        fmt = '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s'

    formatter = logging.Formatter(
        fmt=fmt,
        datefmt='%Y-%m-%d %H:%M:%S',
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    if not root_logger.handlers:
        root_logger.addHandler(handler)

    logging.getLogger('uvicorn.access').setLevel(logging.WARNING)

    return logging.getLogger(settings.APP_NAME)


logger = setup_logging()
