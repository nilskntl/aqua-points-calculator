"""The result of scoring one swim.

The model carries both representations of every time — the milliseconds it was
computed from and the string a human reads — so a consumer never has to
reimplement the formatting to display a payload, and never has to reparse a
string to do arithmetic on one.

Two ways in. :meth:`Score.for_swim` takes an explicit base time and looks
nothing up; :meth:`Score.for_event` reads the base time from the shipped tables.
They are separate rather than one method with mutually exclusive arguments, so
neither has a state it can be called in that makes no sense.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from ..core.points import points as compute_points
from ..core.times import coerce_time, format_time
from .event import Event


class Score(BaseModel):
    """A swim, its reference, and what the swim is worth."""

    points: int = Field(description="The World Aquatics point score, truncated.")
    time_millis: int = Field(gt=0, description="The time swum, in milliseconds.")
    time: str = Field(description="The time swum, as written.")
    base_time_millis: int = Field(gt=0, description="The base time scored against.")
    base_time: str = Field(description="The base time, as written.")
    event: Event | None = Field(
        default=None,
        description="The event, when the caller named one.",
    )
    season: int | None = Field(
        default=None,
        description="The season whose table supplied the base time, when it came "
        "from one. Absent when the caller passed the base time in.",
    )

    @classmethod
    def for_swim(
        cls,
        base_time: str | int,
        time: str | int,
        event: Event | None = None,
    ) -> Score:
        """Score a swim against a base time the caller supplies.

        Nothing is looked up: ``event`` rides along on the result as a label and
        has no bearing on the score.

        Args:
            base_time: The event's base time, written or in milliseconds.
            time: The time swum, written or in milliseconds.
            event: The event, if the caller wants it carried through.

        Returns:
            The populated score.

        Raises:
            InvalidTimeError: If either time is not readable or not positive.
        """
        base_millis = coerce_time(base_time)
        swum_millis = coerce_time(time)
        return cls(
            points=compute_points(base_millis, swum_millis),
            time_millis=swum_millis,
            time=format_time(swum_millis),
            base_time_millis=base_millis,
            base_time=format_time(base_millis),
            event=event,
        )

    @classmethod
    def for_event(
        cls,
        event: Event,
        time: str | int,
        season: int | None = None,
    ) -> Score:
        """Score a swim against the shipped base time for its event.

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
        # Imported here rather than at module scope: `data` imports this
        # package's models, so a top-level import would close a cycle.
        from ..data.tables import resolve_base_time

        base_millis, resolved = resolve_base_time(event, season)
        score = cls.for_swim(base_millis, time, event)
        return score.model_copy(update={"season": resolved})
