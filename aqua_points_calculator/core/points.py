"""The World Aquatics point score.

One formula, stated once::

    P = 1000 · (B / T)³

``B`` is the base time for the event — the reference performance World Aquatics
publishes once a year — and ``T`` is the time swum. A swim exactly on the base
time scores 1000; a swim twice as slow scores 125. The result is truncated, not
rounded: 999.97 points is 999, which is how the published tables read.

The base time is an argument rather than a lookup in this package. The official
table changes every season and is a licensed document, so the caller supplies
the reference it is scoring against and stays in control of which season's
figures a result was computed with. See ``docs/extending.md``.
"""

from __future__ import annotations

from .times import coerce_time

#: A swim on the base time scores exactly this.
BASE_POINTS = 1000


class InvalidScoreError(ValueError):
    """Raised when a point score is outside what the formula can invert."""


def points(base_time: str | int, time: str | int) -> int:
    """Score a swim against a base time.

    Args:
        base_time: The event's base time, written or in milliseconds.
        time: The time swum, written or in milliseconds.

    Returns:
        The point score, truncated towards zero.

    Raises:
        InvalidTimeError: If either time is not readable or not positive.
    """
    base_millis = coerce_time(base_time)
    swum_millis = coerce_time(time)
    # Integer arithmetic throughout: the ratio is cubed before the division, so
    # the truncation happens exactly once, at the end, rather than accumulating
    # through three float multiplications.
    return BASE_POINTS * base_millis**3 // swum_millis**3


def time_for_points(base_time: str | int, score: int) -> int:
    """The slowest time that still reaches a given score.

    The inverse of :func:`points`: feeding the result back in returns ``score``
    again. "Slowest that still reaches" is the useful reading of the inverse —
    it is the qualifying time a meet announcement is after.

    Args:
        base_time: The event's base time, written or in milliseconds.
        score: The point score to reach; must be positive.

    Returns:
        The time in milliseconds.

    Raises:
        InvalidTimeError: If the base time is not readable or not positive.
        InvalidScoreError: If ``score`` is not positive, or so high that no
            positive time reaches it.
    """
    if score <= 0:
        raise InvalidScoreError(f"a point score must be positive: {score}")
    base_millis = coerce_time(base_time)

    # Integer cube root of (1000 · B³ / P), then walk the last step by hand: the
    # float cube root is off by one often enough at these magnitudes to shift the
    # returned time by a millisecond, and this function's contract is that
    # points(base, result) == score exactly.
    target = BASE_POINTS * base_millis**3 // score
    if target < 1:
        # Even a 1 ms swim scores only 1000 · B³ against this base time; beyond
        # that the walk below would hand back a time of zero.
        raise InvalidScoreError(f"no positive time reaches {score} points against this base time")
    candidate = max(int(round(target ** (1 / 3))), 1)
    while candidate**3 > target:
        candidate -= 1
    while (candidate + 1) ** 3 <= target:
        candidate += 1
    return candidate
