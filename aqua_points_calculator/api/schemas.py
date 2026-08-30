"""Request and response models for the JSON surfaces.

Separate from the domain models on purpose: ``Score`` is what the calculator
computes, these are what the wire carries. Keeping them apart means a field can
be added to the API payload — a request echo, a version stamp — without it
appearing on the library's return type.

The response models double as the CLI's ``--json`` payloads for the table
listings, built through the classmethods below: one construction, so a script
can switch between the two surfaces without remapping keys. This module needs
only pydantic — no FastAPI — so the CLI can import it without the ``api`` extra.

The library keeps its two reference sources in two functions, because neither
should have an argument combination that makes no sense. The wire cannot: one
endpoint has to accept both shapes, so the either/or is validated here, at the
boundary, and nowhere else.
"""

from __future__ import annotations

from typing import Self

from pydantic import BaseModel, Field, model_validator

from ..core.times import format_time
from ..data.tables import BaseTimeTable, available_seasons, latest_season, table
from ..model.enums import Course
from ..model.event import Event
from ..model.score import Score


class _Reference(BaseModel):
    """Shared either/or: an explicit base time, or an event to look one up for."""

    base_time: str | int | None = Field(
        default=None,
        description="An explicit base time — written (`46.40`, `1:02,34`) or in "
        "milliseconds. Mutually exclusive with `event`.",
        examples=["46.40"],
    )
    event: Event | None = Field(
        default=None,
        description="An event, whose base time is read from the tables this service "
        "ships. Mutually exclusive with `base_time`.",
    )
    season: int | None = Field(
        default=None,
        description="Which season's table to read, defaulting to the latest shipped "
        "for the event's course. Only meaningful together with `event`.",
        examples=[2025],
    )

    @model_validator(mode="after")
    def _exactly_one_reference(self) -> Self:
        """Require exactly one of `base_time` and `event`.

        Returns:
            The validated model.

        Raises:
            ValueError: If both or neither were given, or if `season` was sent
                without an `event` to apply it to.
        """
        if (self.base_time is None) == (self.event is None):
            raise ValueError("give exactly one of 'base_time' or 'event'")
        if self.season is not None and self.event is None:
            raise ValueError("'season' only applies together with 'event'")
        return self


class ScoreRequest(_Reference):
    """Score one swim."""

    time: str | int = Field(
        description="The time swum — written or in milliseconds.",
        examples=["51.35"],
    )


class TimeRequest(_Reference):
    """Invert the formula."""

    points: int = Field(gt=0, description="The point score to reach.", examples=[800])


class TimeResponse(BaseModel):
    """The slowest time still worth the requested score."""

    time: str = Field(description="The time, as written.")
    time_millis: int = Field(gt=0, description="The time in milliseconds.")
    points: int = Field(description="The score that time is worth — the one requested.")
    base_time: str = Field(description="The base time, as written.")
    base_time_millis: int = Field(gt=0, description="The base time in milliseconds.")
    event: Event | None = Field(default=None, description="The event, if one was given.")
    season: int | None = Field(
        default=None, description="The season whose table supplied the base time."
    )


class ScoreResponse(BaseModel):
    """A scored swim."""

    score: Score = Field(description="The swim, its reference, and what it is worth.")


class SeasonInfo(BaseModel):
    """One shipped base-time table, without its times."""

    course: Course = Field(description="The course the table applies to.")
    season: int = Field(description="The season, numbered per course.")
    valid_from: str = Field(description="First day the table applies (ISO date).")
    valid_until: str = Field(description="Last day the table applies (ISO date).")
    events: int = Field(description="How many events the table covers.")
    source_title: str = Field(description="The official publication behind it.")
    source_url: str = Field(description="A link to that publication.")

    @classmethod
    def for_table(cls, loaded: BaseTimeTable) -> Self:
        """Describe one shipped table.

        Args:
            loaded: The parsed table.

        Returns:
            The populated row.
        """
        return cls(
            course=loaded.course,
            season=loaded.season,
            valid_from=loaded.valid_from.isoformat(),
            valid_until=loaded.valid_until.isoformat(),
            events=len(loaded.times),
            source_title=loaded.source.title,
            source_url=loaded.source.url,
        )


class SeasonsResponse(BaseModel):
    """Every base-time table this service ships."""

    seasons: list[SeasonInfo] = Field(description="The tables, oldest first per course.")
    latest: dict[str, int] = Field(
        description="The season used per course when a request names none."
    )

    @classmethod
    def shipped(cls) -> Self:
        """List every table in the installed package.

        Returns:
            The tables, oldest first per course, with the per-course defaults.
        """
        return cls(
            seasons=[
                SeasonInfo.for_table(table(course, season))
                for course in Course
                for season in available_seasons(course)
            ],
            latest={course: latest_season(course) for course in Course},
        )


class BaseTimeEntry(BaseModel):
    """One event's base time within a table."""

    event: Event = Field(description="The event.")
    base_time: str = Field(description="The base time, as written.")
    base_time_millis: int = Field(gt=0, description="The base time in milliseconds.")


class BaseTimesResponse(BaseModel):
    """A whole base-time table."""

    course: Course = Field(description="The course the table applies to.")
    season: int = Field(description="The season.")
    valid_from: str = Field(description="First day the table applies (ISO date).")
    valid_until: str = Field(description="Last day the table applies (ISO date).")
    source_title: str = Field(description="The official publication behind it.")
    source_url: str = Field(description="A link to that publication.")
    base_times: list[BaseTimeEntry] = Field(description="Every event in the table.")

    @classmethod
    def for_table(cls, loaded: BaseTimeTable) -> Self:
        """Render one whole table.

        Args:
            loaded: The parsed table.

        Returns:
            Every event in it with its base time, and the source document.
        """
        return cls(
            course=loaded.course,
            season=loaded.season,
            valid_from=loaded.valid_from.isoformat(),
            valid_until=loaded.valid_until.isoformat(),
            source_title=loaded.source.title,
            source_url=loaded.source.url,
            base_times=[
                BaseTimeEntry(
                    event=event,
                    base_time=format_time(millis),
                    base_time_millis=millis,
                )
                for event, millis in loaded.times.items()
            ],
        )


class HealthResponse(BaseModel):
    """Liveness."""

    status: str = Field(description="Always `ok` when the service is answering.")
    version: str = Field(description="The installed package version.")
