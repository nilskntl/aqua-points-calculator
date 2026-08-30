"""Swim times as integer milliseconds.

Times are held as ``int`` milliseconds everywhere inside the package, never as
``float`` seconds: the point formula cubes a ratio of two times, and a binary
float would make the last digit of a score depend on how the input happened to
round. Milliseconds are also what result files and timing systems actually
carry, so no precision is invented on the way in.

The textual form is the one used on start lists and result sheets —
``mm:ss,hh`` or ``mm:ss.hh``, with the minutes optional::

    >>> parse_time("1:02.34")
    62340
    >>> format_time(62340)
    '1:02.34'
"""

from __future__ import annotations

import re

#: ``[[h:]mm:]ss[.hh]`` with either a comma or a dot as the decimal separator —
#: result sheets in the German-speaking world use the comma, timing exports the
#: dot, and both mean the same thing.
_TIME_RE = re.compile(
    r"""
    ^\s*
    (?:(?:(?P<hours>\d+):)?(?P<minutes>\d{1,2}):)?
    (?P<seconds>\d{1,2})
    (?:[.,](?P<fraction>\d{1,3}))?
    \s*$
    """,
    re.VERBOSE,
)


class InvalidTimeError(ValueError):
    """Raised when a string is not a readable swim time."""


def parse_time(value: str) -> int:
    """Read a swim time into milliseconds.

    Args:
        value: The time, as ``ss``, ``ss.hh``, ``mm:ss.hh`` or ``h:mm:ss.hh``.
            The decimal separator may be a dot or a comma.

    Returns:
        The time in milliseconds.

    Raises:
        InvalidTimeError: If the string does not look like a swim time, or the
            time is not positive.
    """
    match = _TIME_RE.match(value)
    if match is None:
        raise InvalidTimeError(f"not a swim time: {value!r}")

    hours = int(match["hours"] or 0)
    minutes = int(match["minutes"] or 0)
    seconds = int(match["seconds"])
    # "1:02.3" is three tenths, not three milliseconds — pad on the right, which
    # is what the written form means, rather than reading the digits as an int.
    fraction = int((match["fraction"] or "").ljust(3, "0") or 0)

    if minutes > 59 or seconds > 59:
        raise InvalidTimeError(f"not a swim time: {value!r}")

    total = ((hours * 60 + minutes) * 60 + seconds) * 1000 + fraction
    if total <= 0:
        raise InvalidTimeError(f"a swim time must be positive: {value!r}")
    return total


def format_time(millis: int) -> str:
    """Render milliseconds as a swim time.

    The inverse of :func:`parse_time` for every value it produces: hundredths,
    because that is the resolution a swim is timed and published at, with the
    minutes and hours dropped while they are zero. Below one hundredth the
    milliseconds are kept — truncating there would render ``"0.00"``, which
    :func:`parse_time` rightly rejects, and every rendering must reparse.

    Args:
        millis: The time in milliseconds.

    Returns:
        The time as ``ss.hh``, ``mm:ss.hh`` or ``h:mm:ss.hh``.

    Raises:
        InvalidTimeError: If ``millis`` is not positive.
    """
    if millis <= 0:
        raise InvalidTimeError(f"a swim time must be positive: {millis}")
    if millis < 10:
        return f"0.00{millis}"

    hundredths = millis // 10
    seconds, hundredths = divmod(hundredths, 100)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)

    if hours:
        return f"{hours}:{minutes:02d}:{seconds:02d}.{hundredths:02d}"
    if minutes:
        return f"{minutes}:{seconds:02d}.{hundredths:02d}"
    return f"{seconds}.{hundredths:02d}"


def coerce_time(value: str | int) -> int:
    """Accept a time as either its written form or raw milliseconds.

    The library, the CLI and the HTTP surface all take times from users who have
    one or the other at hand; normalising here keeps that convenience out of
    three separate call sites. Milliseconds also arrive as strings — the CLI
    only ever sees strings — so a bare run of digits that does not read as a
    written time (the seconds field stops at two digits) means milliseconds too.

    Args:
        value: A time string, or milliseconds already.

    Returns:
        The time in milliseconds.

    Raises:
        InvalidTimeError: If the value is not a readable, positive time.
    """
    if isinstance(value, int):
        if value <= 0:
            raise InvalidTimeError(f"a swim time must be positive: {value}")
        return value
    try:
        return parse_time(value)
    except InvalidTimeError:
        if value.strip().isdigit():
            return coerce_time(int(value))
        raise
