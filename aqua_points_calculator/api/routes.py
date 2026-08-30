"""The HTTP endpoints.

All stateless and all synchronous. Scoring is a handful of integer operations
and a table lookup against data already parsed into memory, so the handlers are
plain ``def`` — FastAPI runs those in a worker thread, which keeps the event
loop free without the ceremony of an executor.

Every content problem is a 422: unlike a file parser, there is no partial
success here. A time either reads or it does not, an event is either in the
table or it is not, and a caller that got it wrong has a bug rather than a
degraded result.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Path, status

from .. import __version__
from ..core.points import InvalidScoreError, time_for_points
from ..core.times import InvalidTimeError, coerce_time, format_time
from ..data.tables import (
    UnknownEventError,
    UnknownSeasonError,
    resolve_base_time,
    table,
)
from ..model.enums import Course
from ..model.score import Score
from .schemas import (
    BaseTimesResponse,
    HealthResponse,
    ScoreRequest,
    ScoreResponse,
    SeasonsResponse,
    TimeRequest,
    TimeResponse,
)

router = APIRouter()

#: Everything the calculator raises for a request it cannot honour. All of them
#: mean the same thing to a client — the request described a swim that cannot be
#: scored — so they share one status code.
_BAD_REQUEST = (InvalidTimeError, InvalidScoreError, UnknownSeasonError, UnknownEventError)


def _unprocessable(error: Exception) -> HTTPException:
    """Wrap a calculator error as a 422.

    Args:
        error: What the core raised.

    Returns:
        The HTTP exception to raise in its place.
    """
    return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error))


@router.post("/points", response_model=ScoreResponse, tags=["scoring"])
def score_swim(request: ScoreRequest) -> ScoreResponse:
    """Score a swim.

    Send either a `base_time` of your own, or an `event` whose base time this
    service looks up in the season's table.

    Args:
        request: The reference, the time swum and optionally the season.

    Returns:
        The scored swim.

    Raises:
        HTTPException: 422 if the swim cannot be scored.
    """
    # The either/or is already validated on the schema, so exactly one branch
    # applies — and each maps onto the Score constructor built for it.
    try:
        if request.event is not None:
            result = Score.for_event(request.event, request.time, request.season)
        else:
            assert request.base_time is not None
            result = Score.for_swim(request.base_time, request.time)
    except _BAD_REQUEST as error:
        raise _unprocessable(error) from error
    return ScoreResponse(score=result)


@router.post("/time", response_model=TimeResponse, tags=["scoring"])
def time_for_score(request: TimeRequest) -> TimeResponse:
    """The slowest time still worth a given score.

    Takes the same either/or reference as `/points`.

    Args:
        request: The reference and the score to reach.

    Returns:
        The time, written and in milliseconds.

    Raises:
        HTTPException: 422 if the request cannot be answered.
    """
    try:
        if request.event is not None:
            base_millis, season = resolve_base_time(request.event, request.season)
        else:
            assert request.base_time is not None
            base_millis, season = coerce_time(request.base_time), None
        millis = time_for_points(base_millis, request.points)
    except _BAD_REQUEST as error:
        raise _unprocessable(error) from error

    return TimeResponse(
        time=format_time(millis),
        time_millis=millis,
        points=request.points,
        base_time=format_time(base_millis),
        base_time_millis=base_millis,
        event=request.event,
        season=season,
    )


@router.get("/seasons", response_model=SeasonsResponse, tags=["base times"])
def seasons() -> SeasonsResponse:
    """Every base-time table this service ships.

    Long course and short course are numbered independently, so the two lists
    do not line up and `latest` names one season per course.

    Returns:
        The tables and the per-course defaults.
    """
    return SeasonsResponse.shipped()


@router.get("/base-times/{course}/{season}", response_model=BaseTimesResponse, tags=["base times"])
def base_times(
    course: Course = Path(description="Long or short course."),
    season: int = Path(description="The season, as listed by `/seasons`."),
) -> BaseTimesResponse:
    """One whole base-time table.

    Args:
        course: Long or short course.
        season: The season number.

    Returns:
        Every event in that table with its base time.

    Raises:
        HTTPException: 422 if no such table ships.
    """
    try:
        loaded = table(course, season)
    except UnknownSeasonError as error:
        raise _unprocessable(error) from error

    return BaseTimesResponse.for_table(loaded)


@router.get("/health", response_model=HealthResponse, tags=["meta"])
def health() -> HealthResponse:
    """Liveness probe.

    Returns:
        The status and the running version.
    """
    return HealthResponse(status="ok", version=__version__)
