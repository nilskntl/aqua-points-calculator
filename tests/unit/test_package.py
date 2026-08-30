"""The package's own public surface."""

from __future__ import annotations

import aqua_points_calculator as apc


def test_the_convenience_score_matches_the_model(base_time: str) -> None:
    from aqua_points_calculator.model.score import Score

    assert apc.score(base_time, "51.35") == Score.for_swim(base_time, "51.35")


def test_the_event_reaches_the_result(base_time: str, event: apc.Event) -> None:
    assert apc.score(base_time, "51.35", event).event == event


def test_every_exported_name_exists() -> None:
    missing = [name for name in apc.__all__ if not hasattr(apc, name)]
    assert missing == []


def test_a_version_is_always_reported() -> None:
    # Falls back to 0.0.0 from a bare checkout rather than raising.
    assert apc.__version__


def test_score_for_matches_the_model(event: apc.Event) -> None:
    from aqua_points_calculator.model.score import Score

    assert apc.score_for(event, "51.35") == Score.for_event(event, "51.35")


def test_score_for_accepts_a_season(event: apc.Event) -> None:
    assert apc.score_for(event, "51.35", 2022).season == 2022


def test_the_table_helpers_are_exported(event: apc.Event) -> None:
    assert apc.base_time(event) > 0
    assert apc.latest_season(apc.Course.LONG) in apc.available_seasons(apc.Course.LONG)
