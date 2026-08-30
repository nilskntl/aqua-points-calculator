"""What a swim was swum in."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from .enums import Course, Gender, Stroke


class Event(BaseModel):
    """An event, as far as scoring is concerned.

    The five facets modelled here are exactly what selects a base time, which is
    why the shipped tables are keyed on this type. Everything else a meet
    programme carries about an event — heat, session, age group, entry deadline —
    has no bearing on a point score and is the caller's business.

    Frozen, so it can be used as a dictionary key: a base-time table is a mapping
    from event to time, and that is how :mod:`aqua_points_calculator.data` holds
    one.
    """

    model_config = ConfigDict(frozen=True)

    distance: int = Field(gt=0, description="Race distance in metres, per leg for a relay.")
    stroke: Stroke = Field(description="The stroke swum.")
    course: Course = Field(description="Long or short course.")
    gender: Gender = Field(description="The classification the event is scored under.")
    legs: int = Field(
        default=1,
        ge=1,
        description="Number of swimmers. 1 is an individual event, 4 a relay.",
    )

    @property
    def is_relay(self) -> bool:
        """Whether this is a relay rather than an individual event."""
        return self.legs > 1

    def label(self) -> str:
        """A short human-readable name.

        Returns:
            Something like ``"100 butterfly (long, female)"``, or
            ``"4x100 medley (long, mixed)"`` for a relay.
        """
        distance = f"{self.legs}x{self.distance}" if self.is_relay else str(self.distance)
        return f"{distance} {self.stroke} ({self.course}, {self.gender})"
