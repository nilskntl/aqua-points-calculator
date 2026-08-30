# Getting Started

## Install

As a dependency:

```bash
pip install aqua-points-calculator            # library + CLI
pip install "aqua-points-calculator[api]"     # plus the FastAPI service
uv add aqua-points-calculator
```

To work on the calculator itself:

```bash
git clone https://github.com/nilskntl/aqua-points-calculator
cd aqua-points-calculator
make install
```

`make install` runs `uv sync --extra api`, which fetches Python 3.12 from
`.python-version` if it is not already there. Nothing else is needed.

## Score a swim

Scoring needs a reference time, and there are two ways to get one.

**Name the event** and the base time comes from the tables this package ships:

```python
from aqua_points_calculator import Course, Event, Gender, Stroke, score_for

event = Event(distance=100, stroke=Stroke.FREESTYLE, course=Course.LONG, gender=Gender.MALE)

score_for(event, "51.35").points  # 737
score_for(event, "51.35", 2022).points  # 762, against the 2022 table
```

**Or supply the base time yourself**, and no table is read:

```python
from aqua_points_calculator import points

points("46.40", "51.35")  # 737
```

Here the first argument is always the base time and the second the time swum.
Both take either the written form or raw milliseconds:

```python
points(46_400, 51_350)  # 737 — the same swim
points("1:02,34", "1:05.10")  # minutes optional, comma or dot
```

## Get the full result

`score` and `score_for` return the pydantic model the HTTP surface serialises,
which carries both representations of both times:

```python
from aqua_points_calculator import score, score_for

result = score("46.40", "51.35")
result.points  # 737
result.time  # '51.35'
result.time_millis  # 51350
result.base_time  # '46.40'
result.season  # None — you supplied the base time

looked_up = score_for(event, "51.35")
looked_up.season  # 2026 — which table the base time came from
looked_up.event.label()  # '100 freestyle (long, male)'
```

`season` is what keeps a stored score interpretable later: it says which
season's record the number was measured against.

With an explicit base time you can still attach an event as a label. It is
carried through untouched and has no bearing on the score:

```python
score("48.50", "51.35", event).event.label()  # '100 freestyle (long, male)'
```

## Relays

A relay is the same model with `legs`, and has its own entry in every table:

```python
relay = Event(distance=100, stroke=Stroke.MEDLEY, course=Course.LONG, gender=Gender.MIXED, legs=4)
score_for(relay, "3:40.00").base_time  # '3:37.43'
relay.label()  # '4x100 medley (long, mixed)'
```

## Invert it

What must be swum to reach 800 points?

```python
from aqua_points_calculator import format_time, time_for_points

millis = time_for_points("46.40", 800)  # 49982
format_time(millis)  # '49.98'
```

The guarantee is exact: `points(base, time_for_points(base, n)) == n` for every
positive `n`. One millisecond slower no longer reaches it.

## See which tables ship

```bash
aqua-points-calculator seasons
aqua-points-calculator base-times --course long --season 2025
```

```python
from aqua_points_calculator import Course, available_seasons, latest_season

available_seasons(Course.LONG)  # (2022, 2023, 2024, 2025, 2026)
latest_season(Course.SHORT)  # 2025
```

Long course and short course run on different calendars, so their seasons are
numbered independently — see [Base times](./base-times.md).

## Run the service

```bash
make serve       # uvicorn on :8000 with reload
make up          # the same in Docker
```

Then:

```bash
curl -X POST http://localhost:8000/points \
  -H 'content-type: application/json' \
  -d '{"base_time": "46.40", "time": "51.35"}'

curl -X POST http://localhost:8000/points \
  -H 'content-type: application/json' \
  -d '{"event": {"distance": 100, "stroke": "freestyle", "course": "long", "gender": "male"}, "time": "51.35"}'
```

Interactive documentation is at `http://localhost:8000/docs`, the schema at
`/openapi.json`.

## Run the checks

```bash
make test        # unit tests, fast, no coverage gate
make test-it     # everything, incl. integration and the coverage threshold
make lint
make typecheck
```

`make help` lists every target.
