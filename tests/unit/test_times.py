"""Time parsing and rendering."""

from __future__ import annotations

import pytest

from aqua_points_calculator.core.times import (
    InvalidTimeError,
    coerce_time,
    format_time,
    parse_time,
)


@pytest.mark.parametrize(
    ("written", "millis"),
    [
        ("51.35", 51_350),
        ("51,35", 51_350),
        ("1:02.34", 62_340),
        ("1:02,34", 62_340),
        ("16:23.11", 983_110),
        ("1:02:03.04", 3_723_040),
        ("9", 9_000),
        ("  51.35  ", 51_350),
    ],
)
def test_parse_reads_every_written_form(written: str, millis: int) -> None:
    assert parse_time(written) == millis


def test_a_short_fraction_is_padded_not_read_as_an_int() -> None:
    # "51.3" is three tenths — 300 ms, not 3 ms.
    assert parse_time("51.3") == 51_300


def test_milliseconds_survive_the_round_trip() -> None:
    assert parse_time("51.357") == 51_357


@pytest.mark.parametrize(
    "written",
    ["", "abc", "51.35.11", "1:2:3:4", "0", "0.00", "-51.35", "51:99.00", "99:00.00"],
)
def test_parse_rejects_what_is_not_a_time(written: str) -> None:
    with pytest.raises(InvalidTimeError):
        parse_time(written)


@pytest.mark.parametrize(
    ("millis", "written"),
    [
        (51_350, "51.35"),
        (62_340, "1:02.34"),
        (983_110, "16:23.11"),
        (3_723_040, "1:02:03.04"),
        (9_000, "9.00"),
    ],
)
def test_format_renders_hundredths_and_drops_leading_zero_units(millis: int, written: str) -> None:
    assert format_time(millis) == written


def test_format_truncates_below_a_hundredth() -> None:
    # Published results are hundredths; the extra digit is dropped, not rounded.
    assert format_time(51_359) == "51.35"


def test_format_rejects_a_non_positive_time() -> None:
    with pytest.raises(InvalidTimeError):
        format_time(0)


def test_format_keeps_milliseconds_below_a_hundredth() -> None:
    # Truncating would render "0.00", which parse_time rightly rejects; every
    # rendering must reparse to a positive time.
    assert format_time(5) == "0.005"
    assert parse_time(format_time(5)) == 5


def test_coerce_accepts_both_representations() -> None:
    assert coerce_time("51.35") == coerce_time(51_350) == 51_350


def test_coerce_reads_digit_strings_as_milliseconds() -> None:
    # The CLI only ever sees strings, and "62340" is no written time at all.
    assert coerce_time("62340") == 62_340


def test_coerce_keeps_the_written_reading_when_there_is_one() -> None:
    # "9" reads as nine seconds, so it stays nine seconds.
    assert coerce_time("9") == 9_000


def test_coerce_rejects_non_positive_milliseconds() -> None:
    with pytest.raises(InvalidTimeError):
        coerce_time(-1)
    with pytest.raises(InvalidTimeError):
        coerce_time("0")
