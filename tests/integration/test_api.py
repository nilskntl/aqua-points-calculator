"""The HTTP surface, against the real FastAPI application."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from aqua_points_calculator.api import create_app

pytestmark = pytest.mark.integration

EVENT = {"distance": 100, "stroke": "freestyle", "course": "long", "gender": "male"}


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())


def test_health_reports_a_version(client: TestClient) -> None:
    body = client.get("/health").json()
    assert body["status"] == "ok"
    assert body["version"]


# --- scoring against a caller-supplied base time ------------------------------


def test_points_scores_against_an_explicit_base_time(client: TestClient) -> None:
    response = client.post("/points", json={"base_time": "46.40", "time": "51.35"})
    assert response.status_code == 200
    score = response.json()["score"]
    assert score["points"] == 737
    assert score["base_time_millis"] == 46_400
    assert score["event"] is None
    assert score["season"] is None


def test_points_accepts_milliseconds(client: TestClient) -> None:
    response = client.post("/points", json={"base_time": 46_400, "time": 51_350})
    assert response.json()["score"]["points"] == 737


def test_an_unreadable_time_is_a_422(client: TestClient) -> None:
    response = client.post("/points", json={"base_time": "46.40", "time": "nonsense"})
    assert response.status_code == 422


# --- scoring against the shipped tables ---------------------------------------


def test_points_looks_the_base_time_up_from_an_event(client: TestClient) -> None:
    response = client.post("/points", json={"event": EVENT, "time": "51.35"})
    assert response.status_code == 200
    score = response.json()["score"]
    assert score["points"] == 737
    assert score["base_time"] == "46.40"
    assert score["event"]["distance"] == 100
    assert score["season"] == 2026


def test_a_season_selects_a_historical_table(client: TestClient) -> None:
    response = client.post("/points", json={"event": EVENT, "time": "51.35", "season": 2022})
    body = response.json()["score"]
    assert body["season"] == 2022
    assert body["base_time"] == "46.91"
    assert body["points"] == 762


def test_the_course_selects_the_table(client: TestClient) -> None:
    short = client.post(
        "/points", json={"event": {**EVENT, "course": "short"}, "time": "51.35"}
    ).json()["score"]
    long = client.post("/points", json={"event": EVENT, "time": "51.35"}).json()["score"]
    assert short["base_time"] != long["base_time"]


def test_a_relay_is_scored_from_its_own_entry(client: TestClient) -> None:
    relay = {"distance": 100, "stroke": "medley", "course": "long", "gender": "mixed", "legs": 4}
    response = client.post("/points", json={"event": relay, "time": "3:40.00"})
    assert response.status_code == 200
    assert response.json()["score"]["base_time"] == "3:37.43"


def test_an_unshipped_season_is_a_422(client: TestClient) -> None:
    response = client.post("/points", json={"event": EVENT, "time": "51.35", "season": 1999})
    assert response.status_code == 422
    assert "1999" in response.json()["detail"]


def test_an_event_outside_the_table_is_a_422(client: TestClient) -> None:
    response = client.post("/points", json={"event": {**EVENT, "distance": 125}, "time": "51.35"})
    assert response.status_code == 422


# --- the either/or ------------------------------------------------------------


def test_both_references_together_are_refused(client: TestClient) -> None:
    response = client.post("/points", json={"base_time": "46.40", "event": EVENT, "time": "51.35"})
    assert response.status_code == 422


def test_neither_reference_is_refused(client: TestClient) -> None:
    assert client.post("/points", json={"time": "51.35"}).status_code == 422


def test_a_season_without_an_event_is_refused(client: TestClient) -> None:
    # Silently ignoring it would let a caller believe a historical table was used.
    response = client.post("/points", json={"base_time": "46.40", "time": "51.35", "season": 2022})
    assert response.status_code == 422


# --- the inverse --------------------------------------------------------------


def test_time_inverts_the_formula(client: TestClient) -> None:
    body = client.post("/time", json={"base_time": "46.40", "points": 800}).json()
    assert body["points"] == 800
    back = client.post("/points", json={"base_time": "46.40", "time": body["time_millis"]})
    assert back.json()["score"]["points"] == 800


def test_time_takes_an_event_too(client: TestClient) -> None:
    body = client.post("/time", json={"event": EVENT, "points": 800}).json()
    assert body["season"] == 2026
    assert body["event"]["distance"] == 100
    assert body["base_time"] == "46.40"


def test_time_rejects_a_non_positive_score(client: TestClient) -> None:
    assert client.post("/time", json={"base_time": "46.40", "points": 0}).status_code == 422


def test_time_rejects_an_unreadable_base_time(client: TestClient) -> None:
    response = client.post("/time", json={"base_time": "nonsense", "points": 800})
    assert response.status_code == 422


def test_time_rejects_an_unreachable_score(client: TestClient) -> None:
    # A score beyond what a 1 ms swim reaches has no answer; it must be a 422,
    # not a 500 from formatting a zero time.
    response = client.post("/time", json={"base_time": "46.40", "points": 10**18})
    assert response.status_code == 422


# --- the table endpoints ------------------------------------------------------


def test_seasons_lists_every_table(client: TestClient) -> None:
    body = client.get("/seasons").json()
    assert len(body["seasons"]) == 10
    assert body["latest"] == {"long": 2026, "short": 2025}


def test_every_listed_season_names_its_source(client: TestClient) -> None:
    for season in client.get("/seasons").json()["seasons"]:
        assert season["source_url"].startswith("https://")
        assert season["events"] > 0


def test_base_times_returns_a_whole_table(client: TestClient) -> None:
    body = client.get("/base-times/short/2025").json()
    assert body["season"] == 2025
    assert len(body["base_times"]) == 48
    assert body["valid_from"] == "2025-09-01"


def test_base_times_rejects_an_unshipped_table(client: TestClient) -> None:
    assert client.get("/base-times/long/1999").status_code == 422


def test_base_times_rejects_a_nonsense_course(client: TestClient) -> None:
    assert client.get("/base-times/olympic/2025").status_code == 422


def test_a_misconfigured_log_level_does_not_prevent_startup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # A cosmetic misconfiguration must not become a hard outage at import time.
    from aqua_points_calculator.api.app import configure_logging

    monkeypatch.setenv("LOG_LEVEL", "verbose")
    configure_logging()


def test_the_openapi_document_publishes_the_schema(client: TestClient) -> None:
    schemas = client.get("/openapi.json").json()["components"]["schemas"]
    assert "Score" in schemas
    assert "Event" in schemas
    assert "BaseTimesResponse" in schemas
