"""The optional HTTP surface.

The service requires the ``api`` extra (``uv sync --extra api``). Run it with::

    uvicorn aqua_points_calculator.api:app --host 0.0.0.0 --port 8000

The re-exports are lazy (PEP 562) for two reasons: :mod:`.schemas` is shared
with the CLI and must stay importable without FastAPI installed, and importing
this package must not build an application or reconfigure logging as a side
effect — that happens on first access to ``app``.
"""

from __future__ import annotations

from importlib import import_module
from types import ModuleType
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .app import app, create_app
    from .routes import router

__all__ = ["app", "create_app", "router"]


def __getattr__(name: str) -> Any:
    """Resolve the re-exports on first access.

    Args:
        name: The attribute being looked up.

    Returns:
        The application, the factory, or the router.

    Raises:
        AttributeError: For any name not in ``__all__``.
    """
    if name in {"app", "create_app"}:
        # import_module rather than `from . import app`: the latter resolves
        # the submodule through getattr on this package, which is this very
        # function — instant recursion.
        value = getattr(import_module(".app", __name__), name)
        # Importing the submodule binds this package's ``app`` attribute to the
        # module object, which would shadow this function on every later
        # lookup. Drop that binding (and cache what was asked for), so
        # ``aqua_points_calculator.api:app`` resolves to the ASGI application
        # however the accesses were interleaved.
        if isinstance(globals().get("app"), ModuleType):
            del globals()["app"]
        globals()[name] = value
        return value
    if name == "router":
        from .routes import router

        return router
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
