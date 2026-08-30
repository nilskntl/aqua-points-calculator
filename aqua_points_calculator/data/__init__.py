"""The base-time tables that ship with the package.

Scoring needs a reference time, and this is where one comes from when the caller
does not supply their own::

    from aqua_points_calculator import Course, Event, Gender, Stroke
    from aqua_points_calculator.data import base_time

    event = Event(distance=100, stroke=Stroke.FREESTYLE, course=Course.LONG, gender=Gender.MALE)
    base_time(event)            # the latest shipped season
    base_time(event, 2023)      # a historical one

Passing an explicit base time to :func:`aqua_points_calculator.score` still works
and still bypasses all of this — the tables are a convenience, not a gate.
"""

from .tables import (
    BaseTimeTable,
    Source,
    UnknownEventError,
    UnknownSeasonError,
    available_seasons,
    base_time,
    latest_season,
    table,
)

__all__ = [
    "BaseTimeTable",
    "Source",
    "UnknownEventError",
    "UnknownSeasonError",
    "available_seasons",
    "base_time",
    "latest_season",
    "table",
]
