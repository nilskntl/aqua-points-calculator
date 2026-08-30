"""The point formula and its inverse."""

from __future__ import annotations

import pytest

from aqua_points_calculator.core.points import (
    BASE_POINTS,
    InvalidScoreError,
    points,
    time_for_points,
)
from aqua_points_calculator.core.times import InvalidTimeError


def test_a_swim_on_the_base_time_scores_exactly_a_thousand(base_time: str) -> None:
    assert points(base_time, base_time) == BASE_POINTS


def test_a_swim_twice_as_slow_scores_an_eighth(base_time: str) -> None:
    # The formula cubes the ratio, so half the speed is 1000/8.
    assert points(46_400, 92_800) == 125


def test_a_faster_swim_scores_above_a_thousand(base_time: str) -> None:
    assert points(base_time, "45.00") > BASE_POINTS


def test_the_score_is_truncated_not_rounded() -> None:
    # 1000 · (1000/1000.01)³ = 999.97…, which the published tables read as 999.
    assert points(1_000_000, 1_000_010) == 999


def test_both_representations_agree(base_time: str) -> None:
    assert points(base_time, "51.35") == points(46_400, 51_350)


@pytest.mark.parametrize("bad", ["", "nonsense", "0.00"])
def test_an_unreadable_time_is_rejected(base_time: str, bad: str) -> None:
    with pytest.raises(InvalidTimeError):
        points(base_time, bad)


@pytest.mark.parametrize("score", [1, 125, 500, 767, 999, 1000, 1100, 5000])
def test_the_inverse_round_trips(base_time: str, score: int) -> None:
    # The contract of time_for_points: feed its answer back in and the same score
    # comes out. This is the property the float cube root gets wrong.
    assert points(base_time, time_for_points(base_time, score)) == score


def test_the_inverse_returns_the_slowest_qualifying_time(base_time: str) -> None:
    millis = time_for_points(base_time, 800)
    assert points(base_time, millis) == 800
    # One millisecond slower no longer reaches it — that is what "slowest" means.
    assert points(base_time, millis + 1) < 800


def test_the_base_time_is_its_own_thousand_point_time(base_time: str) -> None:
    assert time_for_points(base_time, BASE_POINTS) == 46_400


@pytest.mark.parametrize("score", [0, -1])
def test_the_inverse_rejects_a_non_positive_score(base_time: str, score: int) -> None:
    with pytest.raises(InvalidScoreError):
        time_for_points(base_time, score)


def test_the_inverse_rejects_an_unreadable_base_time() -> None:
    with pytest.raises(InvalidTimeError):
        time_for_points("nonsense", 800)


def test_the_inverse_rejects_an_unreachable_score(base_time: str) -> None:
    # Beyond 1000 · B³ even a 1 ms swim falls short; walking the candidate down
    # to a zero time would break every caller that formats the result.
    with pytest.raises(InvalidScoreError):
        time_for_points(base_time, 10**18)
