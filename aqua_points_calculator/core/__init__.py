"""The scoring core — times in, points out, no I/O and no framework.

Everything here is pure: the modules import nothing but the standard library,
which is what lets the same code back the library, the CLI and the HTTP service
without any of them leaking into the others.
"""

from .points import BASE_POINTS, InvalidScoreError, points, time_for_points
from .times import InvalidTimeError, coerce_time, format_time, parse_time

__all__ = [
    "BASE_POINTS",
    "InvalidScoreError",
    "InvalidTimeError",
    "coerce_time",
    "format_time",
    "parse_time",
    "points",
    "time_for_points",
]
