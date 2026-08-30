"""FastAPI application factory.

The service is a pure function over its request body — no database, no cache, no
background work, no state between requests — so there is no lifespan, no
settings object and nothing to warm up. Keeping it that way is the point: it
scales by replication and it can be embedded in another app with
``app.include_router(aqua_points_calculator.api.router)``.

Importing this module has no side effects. The ``app`` instance is built lazily
on first access (which is when ``uvicorn aqua_points_calculator.api:app`` asks
for it), and only that path touches the logging configuration — an embedding
host keeps its own handlers.
"""

from __future__ import annotations

import logging
import os

from fastapi import FastAPI

from .. import __version__
from .routes import router

DESCRIPTION = """
Computes World Aquatics point scores for swimming performances, and inverts the
formula to give the slowest time still worth a given score.

The base time is supplied by the caller rather than looked up here: the official
table is republished every season, so the reference a result was scored against
stays an explicit part of the request.
""".strip()


def configure_logging(level: str | None = None) -> None:
    """Install a root log handler.

    uvicorn leaves the root logger without a handler, which silently drops every
    record the package's module loggers emit.

    A level name the logging module does not know falls back to ``INFO`` with a
    warning: a cosmetic misconfiguration must not keep the service from
    starting.

    Args:
        level: The level name; defaults to ``$LOG_LEVEL`` or ``INFO``.
    """
    requested = (level or os.getenv("LOG_LEVEL") or "INFO").upper()
    resolved = requested if requested in logging.getLevelNamesMapping() else "INFO"
    logging.basicConfig(
        level=resolved,
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
        force=True,
    )
    if resolved != requested:
        logging.getLogger(__name__).warning("unknown LOG_LEVEL %r, using INFO", requested)


def create_app() -> FastAPI:
    """Build the application.

    Returns:
        The configured FastAPI app.
    """
    application = FastAPI(
        title="Aqua Points Calculator",
        description=DESCRIPTION,
        version=__version__,
    )
    application.include_router(router)
    return application


def __getattr__(name: str) -> FastAPI:
    """Build the ``app`` instance for ``uvicorn aqua_points_calculator.api.app:app``.

    Lazily (PEP 562) rather than at module scope, so importing the module — as
    an embedding host or a test does — neither constructs an application nor
    reconfigures logging as a side effect.

    Args:
        name: The attribute being looked up.

    Returns:
        The application, built and cached on first access.

    Raises:
        AttributeError: For any attribute other than ``app``.
    """
    if name == "app":
        configure_logging()
        application = create_app()
        globals()["app"] = application
        return application
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
