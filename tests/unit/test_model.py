"""The data schema."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from aqua_points_calculator.core.times import InvalidTimeError
from aqua_points_calculator.model.enums import Course, Gender, Stroke
from aqua_points_calculator.model.event import Event
from aqua_points_calculator.model.score import Score


def test_a_score_carries_both_representations_of_both_times(base_time: str) -> None:
    result = Score.for_swim(base_time, "51.35")
    assert result.time == "51.35"
    assert result.time_millis == 51_350
    assert result.base_time == "46.40"
    assert result.base_time_millis == 46_400


def test_a_score_matches_the_bare_formula(base_time: str) -> None:
    from aqua_points_calculator.core.points import points

    assert Score.for_swim(base_time, "51.35").points == points(base_time, "51.35")


def test_the_event_is_carried_through_untouched(base_time: str, event: Event) -> None:
    result = Score.for_swim(base_time, "51.35", event)
    assert result.event == event


def test_the_event_is_optional(base_time: str) -> None:
    assert Score.for_swim(base_time, "51.35").event is None


def test_an_unreadable_time_is_rejected(base_time: str) -> None:
    with pytest.raises(InvalidTimeError):
        Score.for_swim(base_time, "nonsense")


def test_an_event_labels_itself(event: Event) -> None:
    assert event.label() == "100 freestyle (long, male)"


def test_an_event_needs_a_positive_distance() -> None:
    with pytest.raises(ValidationError):
        Event(
            distance=0,
            stroke=Stroke.FREESTYLE,
            course=Course.LONG,
            gender=Gender.MALE,
        )


def test_the_vocabularies_serialise_as_words(event: Event) -> None:
    # A JSON consumer reads "freestyle", never the single letter a result file uses.
    payload = event.model_dump(mode="json")
    assert payload == {
        "distance": 100,
        "stroke": "freestyle",
        "course": "long",
        "gender": "male",
        "legs": 1,
    }


def test_a_relay_labels_itself_with_its_legs(relay: Event) -> None:
    assert relay.label() == "4x100 medley (long, mixed)"
    assert relay.is_relay


def test_an_individual_event_is_not_a_relay(event: Event) -> None:
    assert not event.is_relay
    assert event.legs == 1


def test_an_event_is_hashable_so_it_can_key_a_table(event: Event) -> None:
    # The shipped tables are dicts keyed on Event; that needs frozen models.
    assert {event: 1}[event.model_copy()] == 1


def test_a_relay_and_its_individual_event_are_different_keys(event: Event) -> None:
    assert event.model_copy(update={"legs": 4}) != event


def test_for_event_reads_the_shipped_table(event: Event) -> None:
    from aqua_points_calculator.core.points import points

    result = Score.for_event(event, "51.35")
    assert result.base_time == "46.40"
    assert result.points == points("46.40", "51.35")


def test_for_event_records_which_season_it_used(event: Event) -> None:
    from aqua_points_calculator.data.tables import latest_season

    assert Score.for_event(event, "51.35").season == latest_season(event.course)
    assert Score.for_event(event, "51.35", 2022).season == 2022


def test_for_event_carries_the_event_through(event: Event) -> None:
    assert Score.for_event(event, "51.35").event == event


def test_for_swim_records_no_season(base_time: str) -> None:
    # A caller-supplied base time belongs to no season, and claiming one would
    # misreport where the number came from.
    assert Score.for_swim(base_time, "51.35").season is None


def test_a_historical_season_scores_differently(event: Event) -> None:
    assert Score.for_event(event, "51.35", 2022).points != Score.for_event(event, "51.35").points
