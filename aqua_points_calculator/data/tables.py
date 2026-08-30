"""The shipped World Aquatics base-time tables.

One YAML file per course and season under ``base_times/``, each a snapshot of the
world records that stood approved on the first day of that season's validity
period — which is what World Aquatics defines a base time to be.

Long course and short course run on different calendars and are therefore
numbered independently: the long-course season is a calendar year, the
short-course season runs 1 September to 31 August. ``long-2025`` and
``short-2024`` overlap in real time; they are not the same season.

The files are generated from the official publications by
``tools/generate_base_times.py`` and are not hand-maintained. Each carries the
document it came from in its ``source`` block.
"""

from __future__ import annotations

import functools
from datetime import date
from importlib import resources

import yaml
from pydantic import BaseModel, Field

from ..core.times import coerce_time
from ..model.enums import Course, Gender, Stroke
from ..model.event import Event

#: The directory of YAML tables inside the installed package.
PACKAGE = "aqua_points_calculator.data.base_times"


class UnknownSeasonError(LookupError):
    """Raised when no shipped table covers the requested course and season."""


class UnknownEventError(LookupError):
    """Raised when a season's table has no base time for an event."""


class Source(BaseModel):
    """Where a table's numbers came from."""

    title: str = Field(description="The title of the official publication.")
    url: str = Field(description="A link to it.")


class BaseTimeTable(BaseModel):
    """One course-season's base times."""

    course: Course = Field(description="The course this table applies to.")
    season: int = Field(description="The season, numbered per course.")
    valid_from: date = Field(description="First day the table applies.")
    valid_until: date = Field(description="Last day the table applies.")
    source: Source = Field(description="The official publication behind it.")
    times: dict[Event, int] = Field(
        description="Base time in milliseconds, keyed by event.",
        exclude=True,
    )

    def base_time(self, event: Event) -> int:
        """Look up one base time.

        Args:
            event: The event to score.

        Returns:
            The base time in milliseconds.

        Raises:
            UnknownEventError: If this table has no entry for the event.
        """
        try:
            return self.times[event]
        except KeyError:
            raise UnknownEventError(
                f"no base time for {event.label()} in {self.course} {self.season}"
            ) from None

    def events(self) -> list[Event]:
        """Every event this table covers, in file order."""
        return list(self.times)


def _load(course: Course, season: int) -> BaseTimeTable:
    """Read and validate one YAML table.

    Args:
        course: Long or short course.
        season: The season number.

    Returns:
        The parsed table.

    Raises:
        UnknownSeasonError: If no such file ships with the package.
    """
    name = f"{course}-{season}.yaml"
    resource = resources.files(PACKAGE) / name
    if not resource.is_file():
        raise UnknownSeasonError(
            f"no shipped base times for {course} course, season {season}; "
            f"available: {', '.join(str(s) for s in available_seasons(course))}"
        )
    raw = yaml.safe_load(resource.read_text(encoding="utf-8"))

    times: dict[Event, int] = {}
    for record in raw["records"]:
        event = Event(
            distance=record["distance"],
            stroke=Stroke(record["stroke"]),
            course=Course(raw["course"]),
            gender=Gender(record["gender"]),
            legs=record.get("legs", 1),
        )
        if event in times:
            raise ValueError(f"{name}: duplicate entry for {event.label()}")
        times[event] = coerce_time(record["time"])

    return BaseTimeTable(
        course=Course(raw["course"]),
        season=raw["season"],
        valid_from=raw["valid_from"],
        valid_until=raw["valid_until"],
        source=Source(**raw["source"]),
        times=times,
    )


# Tables are immutable data read from files inside the installed package, so a
# table is parsed at most once per process and then shared.
table = functools.cache(_load)


@functools.cache
def available_seasons(course: Course) -> tuple[int, ...]:
    """Every season shipped for a course, oldest first.

    Args:
        course: Long or short course.

    Returns:
        The season numbers.
    """
    prefix = f"{course}-"
    seasons = [
        int(entry.name[len(prefix) : -len(".yaml")])
        for entry in resources.files(PACKAGE).iterdir()
        if entry.name.startswith(prefix) and entry.name.endswith(".yaml")
    ]
    return tuple(sorted(seasons))


def latest_season(course: Course) -> int:
    """The most recent shipped season for a course.

    This is what a lookup uses when the caller names no season, so a caller that
    does not care about historical tables never has to pass one.

    Args:
        course: Long or short course.

    Returns:
        The highest season number shipped.

    Raises:
        UnknownSeasonError: If no table ships for the course at all.
    """
    seasons = available_seasons(course)
    if not seasons:
        raise UnknownSeasonError(f"no shipped base times for {course} course")
    return seasons[-1]


def resolve_table(course: Course, season: int | None = None) -> BaseTimeTable:
    """The table for a course, with the season default applied.

    The rule — no season means the latest shipped for the course — lives here
    and nowhere else, so the library, the CLI and the HTTP surface cannot drift
    apart on which table answers a lookup.

    Args:
        course: Long or short course.
        season: The season, defaulting to the latest shipped for the course.

    Returns:
        The parsed table; its ``season`` records which one was chosen.

    Raises:
        UnknownSeasonError: If no table ships for that course and season.
    """
    return table(course, latest_season(course) if season is None else season)


def resolve_base_time(event: Event, season: int | None = None) -> tuple[int, int]:
    """The base time for an event, and the season it actually came from.

    The season a caller passed and the season that answered can differ — passing
    none means the latest shipped — and a surface stamping its result with a
    season must report the latter.

    Args:
        event: The event to score. Its ``course`` selects which table is read.
        season: The season, defaulting to the latest shipped for that course.

    Returns:
        The base time in milliseconds, and the season it was read from.

    Raises:
        UnknownSeasonError: If no table ships for that course and season.
        UnknownEventError: If the table has no entry for the event.
    """
    loaded = resolve_table(event.course, season)
    return loaded.base_time(event), loaded.season


def base_time(event: Event, season: int | None = None) -> int:
    """The base time for an event, from the shipped tables.

    Args:
        event: The event to score. Its ``course`` selects which table is read.
        season: The season, defaulting to the latest shipped for that course.

    Returns:
        The base time in milliseconds.

    Raises:
        UnknownSeasonError: If no table ships for that course and season.
        UnknownEventError: If the table has no entry for the event.
    """
    return resolve_base_time(event, season)[0]
