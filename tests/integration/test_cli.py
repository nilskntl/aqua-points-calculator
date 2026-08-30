"""The CLI, end to end through its own argument parser."""

from __future__ import annotations

import json

import pytest

from aqua_points_calculator.cli import main

pytestmark = pytest.mark.integration

EVENT = ["--distance", "100", "--stroke", "freestyle", "--gender", "male"]


def test_points_prints_the_bare_score(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["points", "51.35", "--base-time", "46.40"]) == 0
    assert capsys.readouterr().out.strip() == "737"


def test_points_as_json(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["--json", "points", "51.35", "--base-time", "46.40"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload == {"points": 737, "base_time": "46.40", "time": "51.35"}


def test_points_can_look_the_base_time_up(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["points", "51.35", *EVENT]) == 0
    assert capsys.readouterr().out.strip() == "737"


def test_a_looked_up_score_reports_its_event_and_season(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main(["--json", "points", "51.35", *EVENT]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["event"]["distance"] == 100
    assert payload["season"] == 2026


def test_an_explicit_base_time_reports_no_event(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["--json", "points", "51.35", "--base-time", "46.40"]) == 0
    assert "event" not in json.loads(capsys.readouterr().out)


def test_a_historical_season_changes_the_score(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["points", "51.35", *EVENT, "--season", "2022"]) == 0
    assert capsys.readouterr().out.strip() == "762"


def test_short_course_is_a_different_table(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["points", "51.35", *EVENT, "--course", "short"]) == 0
    short = capsys.readouterr().out.strip()
    assert main(["points", "51.35", *EVENT]) == 0
    assert short != capsys.readouterr().out.strip()


def test_a_relay_needs_its_legs(capsys: pytest.CaptureFixture[str]) -> None:
    assert (
        main(
            [
                "points",
                "3:20.00",
                "--distance",
                "100",
                "--stroke",
                "medley",
                "--gender",
                "mixed",
                "--legs",
                "4",
            ]
        )
        == 0
    )
    assert int(capsys.readouterr().out.strip()) > 0


def test_time_inverts_the_formula(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["time", "800", "--base-time", "46.40"]) == 0
    written = capsys.readouterr().out.strip()
    assert main(["points", written, "--base-time", "46.40"]) == 0
    assert capsys.readouterr().out.strip() == "800"


def test_time_can_look_the_base_time_up(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["--json", "time", "800", *EVENT]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["points"] == 800
    assert payload["season"] == 2026


def test_convert_normalises_to_milliseconds(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["convert", "1:02,34"]) == 0
    assert capsys.readouterr().out.strip() == "62340"


def test_convert_accepts_milliseconds(capsys: pytest.CaptureFixture[str]) -> None:
    # "a written time, or milliseconds", as the help and docs promise.
    assert main(["convert", "62340"]) == 0
    assert capsys.readouterr().out.strip() == "62340"


def test_points_accepts_milliseconds(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["points", "51350", "--base-time", "46400"]) == 0
    assert capsys.readouterr().out.strip() == "737"


def test_the_json_payload_carries_the_canonical_time(capsys: pytest.CaptureFixture[str]) -> None:
    # The argv spelling ("1:02,34") must not leak into the payload — the API's
    # Score renders the dotted canonical form.
    assert main(["--json", "points", "1:02,34", "--base-time", "1:00.00"]) == 0
    assert json.loads(capsys.readouterr().out)["time"] == "1:02.34"


def test_an_unreachable_score_exits_two(capsys: pytest.CaptureFixture[str]) -> None:
    # A score no positive time reaches must be a clean error, not a zero time.
    assert main(["time", str(10**18), "--base-time", "46.40"]) == 2
    assert "error:" in capsys.readouterr().err


def test_convert_as_json(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["--json", "convert", "1:02,34"]) == 0
    assert json.loads(capsys.readouterr().out) == {"time": "1:02.34", "time_millis": 62340}


def test_seasons_lists_every_shipped_table(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["seasons"]) == 0
    lines = capsys.readouterr().out.strip().splitlines()
    assert len(lines) == 10
    assert sum("(default)" in line for line in lines) == 2


def test_seasons_as_json(capsys: pytest.CaptureFixture[str]) -> None:
    # The payload is the API's /seasons response, shared construction.
    assert main(["--json", "seasons"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert {row["course"] for row in payload["seasons"]} == {"long", "short"}
    assert all(row["source_url"] for row in payload["seasons"])
    assert payload["latest"]["long"] == 2026


def test_base_times_prints_a_whole_table(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["base-times", "--course", "short", "--season", "2025"]) == 0
    out = capsys.readouterr().out
    assert "50 freestyle (short, male)" in out
    assert "4x50 medley (short, mixed)" in out


def test_base_times_as_json(capsys: pytest.CaptureFixture[str]) -> None:
    # The payload is the API's /base-times response, shared construction.
    assert main(["--json", "base-times", "--course", "long"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["season"] == 2026
    assert len(payload["base_times"]) == 42
    assert payload["source_url"].startswith("https://")
    assert payload["base_times"][0]["event"]["distance"] > 0


def test_an_unreadable_time_exits_two(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["points", "nonsense", "--base-time", "46.40"]) == 2
    assert "error:" in capsys.readouterr().err


def test_an_unshipped_season_exits_two(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["points", "51.35", *EVENT, "--season", "1999"]) == 2
    assert "error:" in capsys.readouterr().err


def test_an_event_outside_the_table_exits_two(capsys: pytest.CaptureFixture[str]) -> None:
    assert (
        main(["points", "51.35", "--distance", "125", "--stroke", "freestyle", "--gender", "male"])
        == 2
    )
    assert "error:" in capsys.readouterr().err


def test_a_non_positive_score_exits_two(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["time", "0", "--base-time", "46.40"]) == 2
    assert "error:" in capsys.readouterr().err


def test_distance_without_stroke_is_refused(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as excinfo:
        main(["points", "51.35", "--distance", "100"])
    # The documented contract: every bad argument is exit code 2.
    assert excinfo.value.code == 2
    assert "error:" in capsys.readouterr().err


def test_a_non_positive_distance_is_an_argparse_error() -> None:
    # Caught by the parser, not surfaced as a pydantic traceback.
    with pytest.raises(SystemExit) as excinfo:
        main(["points", "51.35", "--distance", "-100", "--stroke", "freestyle", "--gender", "male"])
    assert excinfo.value.code == 2


def test_non_positive_legs_are_an_argparse_error() -> None:
    with pytest.raises(SystemExit) as excinfo:
        main(["points", "51.35", *EVENT, "--legs", "0"])
    assert excinfo.value.code == 2


def test_a_season_with_an_explicit_base_time_is_refused(
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Silently ignoring it would let the caller believe a historical table was
    # used — the API refuses the same combination.
    with pytest.raises(SystemExit) as excinfo:
        main(["points", "51.35", "--base-time", "46.40", "--season", "2022"])
    assert excinfo.value.code == 2
    assert "--season" in capsys.readouterr().err


def test_a_base_time_and_an_event_together_are_refused() -> None:
    # argparse enforces the either/or itself, so the handler never sees both.
    with pytest.raises(SystemExit) as excinfo:
        main(["points", "51.35", "--base-time", "46.40", *EVENT])
    assert excinfo.value.code == 2


def test_no_reference_at_all_is_refused() -> None:
    with pytest.raises(SystemExit) as excinfo:
        main(["points", "51.35"])
    assert excinfo.value.code == 2


def test_no_subcommand_is_an_argparse_error() -> None:
    with pytest.raises(SystemExit) as excinfo:
        main([])
    assert excinfo.value.code == 2
