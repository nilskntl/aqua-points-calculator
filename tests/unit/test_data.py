"""The shipped base-time tables.

Two kinds of check. The first few assert the loader's behaviour; the rest are
invariants over every YAML file that ships, so a regenerated or hand-edited
table cannot quietly land wrong.
"""

from __future__ import annotations

import pytest

from aqua_points_calculator.core.times import format_time
from aqua_points_calculator.data.tables import (
    PACKAGE,
    UnknownEventError,
    UnknownSeasonError,
    available_seasons,
    base_time,
    latest_season,
    table,
)
from aqua_points_calculator.model.enums import Course, Gender, Stroke
from aqua_points_calculator.model.event import Event

ALL_TABLES = [(course, season) for course in Course for season in available_seasons(course)]


def test_five_seasons_ship_for_each_course() -> None:
    assert len(available_seasons(Course.LONG)) == 5
    assert len(available_seasons(Course.SHORT)) == 5


def test_seasons_come_back_oldest_first() -> None:
    for course in Course:
        seasons = available_seasons(course)
        assert list(seasons) == sorted(seasons)


def test_the_two_courses_are_numbered_independently() -> None:
    # Long course runs on the calendar year, short course from September, so the
    # latest season of each is not the same number and must not be assumed to be.
    assert latest_season(Course.LONG) != latest_season(Course.SHORT)


def test_a_lookup_defaults_to_the_latest_season(event: Event) -> None:
    assert base_time(event) == base_time(event, latest_season(event.course))


def test_a_historical_season_gives_a_different_base_time(event: Event) -> None:
    # The men's 100 free record moved between 2022 and now; if this ever stops
    # holding, the fixture event should change, not the assertion.
    assert base_time(event, 2022) != base_time(event, latest_season(Course.LONG))


def test_an_unshipped_season_is_rejected(event: Event) -> None:
    with pytest.raises(UnknownSeasonError):
        base_time(event, 1999)


def test_the_error_names_what_is_available(event: Event) -> None:
    with pytest.raises(UnknownSeasonError, match="2026"):
        base_time(event, 1999)


def test_an_event_outside_the_table_is_rejected() -> None:
    # 100 m breaststroke exists; 125 m does not.
    nonsense = Event(
        distance=125, stroke=Stroke.BREASTSTROKE, course=Course.LONG, gender=Gender.MALE
    )
    with pytest.raises(UnknownEventError):
        base_time(nonsense)


def test_long_course_has_no_100_medley() -> None:
    # 100 IM is a short-course-only event; the long-course table must not carry one.
    event = Event(distance=100, stroke=Stroke.MEDLEY, course=Course.LONG, gender=Gender.MALE)
    with pytest.raises(UnknownEventError):
        base_time(event)


def test_short_course_does_have_a_100_medley() -> None:
    event = Event(distance=100, stroke=Stroke.MEDLEY, course=Course.SHORT, gender=Gender.MALE)
    assert base_time(event) > 0


def test_relays_are_covered() -> None:
    relay = Event(
        distance=100,
        stroke=Stroke.MEDLEY,
        course=Course.LONG,
        gender=Gender.MIXED,
        legs=4,
    )
    assert base_time(relay) > 0


def test_a_relay_is_not_the_same_entry_as_the_individual_event() -> None:
    kwargs = {
        "distance": 100,
        "stroke": Stroke.FREESTYLE,
        "course": Course.LONG,
        "gender": Gender.MALE,
    }
    assert base_time(Event(**kwargs, legs=4)) != base_time(Event(**kwargs))


def test_a_table_is_parsed_once_and_shared() -> None:
    # The tables are immutable package data; re-reading them per call would be
    # pure waste on a service that scores in a loop.
    assert table(Course.LONG, 2025) is table(Course.LONG, 2025)


# --- invariants over every shipped file --------------------------------------


@pytest.mark.parametrize(("course", "season"), ALL_TABLES)
def test_every_table_is_internally_consistent(course: Course, season: int) -> None:
    loaded = table(course, season)
    assert loaded.course == course
    assert loaded.season == season
    assert loaded.valid_from < loaded.valid_until
    assert loaded.source.url.startswith("https://")
    assert loaded.times


@pytest.mark.parametrize(("course", "season"), ALL_TABLES)
def test_every_base_time_is_a_plausible_swim(course: Course, season: int) -> None:
    for event, millis in table(course, season).times.items():
        assert millis > 0, event.label()
        # A 50 m sprint is over 15 s and a 1500 m under 20 min; anything outside
        # that band means a column slipped during extraction.
        assert 15_000 < millis < 1_200_000, (event.label(), format_time(millis))


@pytest.mark.parametrize(("course", "season"), ALL_TABLES)
def test_longer_races_take_longer(course: Course, season: int) -> None:
    # Within one stroke, gender and leg count, the base times must increase with
    # distance. This is what catches two events swapped in a row of the source.
    loaded = table(course, season)
    grouped: dict[tuple[Stroke, Gender, int], list[tuple[int, int]]] = {}
    for event, millis in loaded.times.items():
        key = (event.stroke, event.gender, event.legs)
        grouped.setdefault(key, []).append((event.distance, millis))
    for key, entries in grouped.items():
        ordered = sorted(entries)
        times = [millis for _, millis in ordered]
        assert times == sorted(times), (key, ordered)


@pytest.mark.parametrize(("course", "season"), ALL_TABLES)
def test_the_men_are_faster_than_the_women_in_every_event(course: Course, season: int) -> None:
    # True of every world record, and a sharp check that the two side-by-side
    # columns of the source PDF did not get crossed.
    loaded = table(course, season)
    for event, millis in loaded.times.items():
        if event.gender is not Gender.MALE:
            continue
        womens = event.model_copy(update={"gender": Gender.FEMALE})
        assert loaded.times[womens] > millis, event.label()


@pytest.mark.parametrize(("course", "season"), ALL_TABLES)
def test_the_validity_window_matches_the_course(course: Course, season: int) -> None:
    loaded = table(course, season)
    if course is Course.LONG:
        # A calendar year.
        assert (loaded.valid_from.month, loaded.valid_from.day) == (1, 1)
        assert loaded.valid_from.year == season == loaded.valid_until.year
    else:
        # 1 September to 31 August of the following year.
        assert (loaded.valid_from.month, loaded.valid_from.day) == (9, 1)
        assert loaded.valid_from.year == season
        assert loaded.valid_until.year == season + 1


def test_the_windows_of_one_course_tile_without_gaps() -> None:
    for course in Course:
        seasons = available_seasons(course)
        for earlier, later in zip(seasons, seasons[1:], strict=False):
            end = table(course, earlier).valid_until
            start = table(course, later).valid_from
            assert (start - end).days == 1, (course, earlier, later)


def test_no_table_file_is_unreachable() -> None:
    # Guards the packaging: a YAML that ships but that available_seasons cannot
    # see would be dead weight in the wheel.
    from importlib import resources

    on_disk = {
        entry.name for entry in resources.files(PACKAGE).iterdir() if entry.name.endswith(".yaml")
    }
    reachable = {f"{course}-{season}.yaml" for course, season in ALL_TABLES}
    assert on_disk == reachable
