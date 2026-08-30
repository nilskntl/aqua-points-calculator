"""World Aquatics point-score calculator for swimming performances.

Scoring a swim needs a reference time. There are two ways to get one, and they
are separate functions rather than one function with an either/or argument::

    from aqua_points_calculator import Course, Event, Gender, Stroke, score, score_for

    score("46.40", "51.35")             # a base time you supply
    score_for(event, "51.35")           # the base time this package ships

``points`` is the bare formula for callers that want an integer and nothing
else. Everything else — the time parsing, the event model, the tables — is
available for a caller that needs it, but scoring a swim needs none of it.
"""

from importlib.metadata import PackageNotFoundError, version

from .core.points import BASE_POINTS, InvalidScoreError, points, time_for_points
from .core.times import InvalidTimeError, format_time, parse_time
from .data.tables import (
    UnknownEventError,
    UnknownSeasonError,
    available_seasons,
    base_time,
    latest_season,
)
from .model.enums import Course, Gender, Stroke
from .model.event import Event
from .model.score import Score

__all__ = [
    "BASE_POINTS",
    "Course",
    "Event",
    "Gender",
    "InvalidScoreError",
    "InvalidTimeError",
    "Score",
    "Stroke",
    "UnknownEventError",
    "UnknownSeasonError",
    "available_seasons",
    "base_time",
    "format_time",
    "latest_season",
    "parse_time",
    "points",
    "score",
    "score_for",
    "time_for_points",
]


def score(base_time: str | int, time: str | int, event: Event | None = None) -> Score:
    """Score a swim against a base time you supply.

    The convenience form of :meth:`Score.for_swim`, so the common case is one
    import from the package root. Nothing is looked up.

    Args:
        base_time: The event's base time, written or in milliseconds.
        time: The time swum, written or in milliseconds.
        event: The event, if the caller wants it carried through onto the result.

    Returns:
        The populated score.

    Raises:
        InvalidTimeError: If either time is not readable or not positive.
    """
    return Score.for_swim(base_time, time, event)


def score_for(event: Event, time: str | int, season: int | None = None) -> Score:
    """Score a swim against the base time this package ships for its event.

    The convenience form of :meth:`Score.for_event`.

    Args:
        event: The event. Its ``course`` selects which table is read.
        time: The time swum, written or in milliseconds.
        season: The season, defaulting to the latest shipped for that course.

    Returns:
        The populated score, with ``season`` recording which table was used.

    Raises:
        InvalidTimeError: If the time is not readable or not positive.
        UnknownSeasonError: If no table ships for that course and season.
        UnknownEventError: If the table has no entry for the event.
    """
    return Score.for_event(event, time, season)


#: Read from the installed distribution metadata, so the version lives in exactly one
#: place (``pyproject.toml``, bumped by Release Please) and cannot drift from it.
try:
    __version__ = version("aqua-points-calculator")
except PackageNotFoundError:  # pragma: no cover - only when running from a bare checkout
    __version__ = "1.0.0"
