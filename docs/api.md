# HTTP API

Requires the `api` extra. Run it with `make serve`, `make up`, or:

```bash
uvicorn aqua_points_calculator.api:app --host 0.0.0.0 --port 8000
```

Interactive documentation is at `/docs`, the schema at `/openapi.json`.

## Endpoints

| Method | Path                            | Purpose                                    |
| ------ | ------------------------------- | ------------------------------------------ |
| `POST` | `/points`                       | Score a swim                               |
| `POST` | `/time`                         | The slowest time still worth a given score |
| `GET`  | `/seasons`                      | Every base-time table the service ships    |
| `GET`  | `/base-times/{course}/{season}` | One whole table                            |
| `GET`  | `/health`                       | Liveness and the running version           |
| `GET`  | `/openapi.json`                 | The schema, for generated clients          |

## Naming the base time

`/points` and `/time` both need a reference and accept it two ways. Send
**exactly one** of `base_time` and `event`:

| Field       | Effect                                                                                |
| ----------- | ------------------------------------------------------------------------------------- |
| `base_time` | Use exactly this — written (`46.40`, `1:02,34`) or in milliseconds. No table is read. |
| `event`     | Look the base time up in a shipped table.                                             |

`season` selects which table, and defaults to the latest shipped for the event's
course. Sending it alongside `base_time` is refused rather than ignored, because
ignoring it would let a caller believe a historical table was used.

## POST /points

Against a base time of your own:

```json
{ "base_time": "46.40", "time": "51.35" }
```

```json
{
  "score": {
    "points": 737,
    "time_millis": 51350,
    "time": "51.35",
    "base_time_millis": 46400,
    "base_time": "46.40",
    "event": null,
    "season": null
  }
}
```

Against a shipped table:

```json
{
  "event": {
    "distance": 100,
    "stroke": "freestyle",
    "course": "long",
    "gender": "male"
  },
  "time": "51.35",
  "season": 2025
}
```

```json
{
  "score": {
    "points": 737,
    "time_millis": 51350,
    "time": "51.35",
    "base_time_millis": 46400,
    "base_time": "46.40",
    "event": {
      "distance": 100,
      "stroke": "freestyle",
      "course": "long",
      "gender": "male",
      "legs": 1
    },
    "season": 2025
  }
}
```

`season` on the response says which table the base time came from, and is `null`
when the caller supplied it. A stored score therefore stays interpretable
without the request beside it.

```bash
curl -X POST http://localhost:8000/points \
  -H 'content-type: application/json' \
  -d '{"base_time": "46.40", "time": "51.35"}'
```

Relays use the same shape, with `legs`:

```json
{
  "event": {
    "distance": 100,
    "stroke": "medley",
    "course": "long",
    "gender": "mixed",
    "legs": 4
  },
  "time": "3:40.00"
}
```

## POST /time

```json
{ "event": { "distance": 100, "stroke": "freestyle", "course": "long", "gender": "male" }, "points": 800 }
```

```json
{
  "time": "49.98",
  "time_millis": 49982,
  "points": 800,
  "base_time": "46.40",
  "base_time_millis": 46400,
  "event": {
    "distance": 100,
    "stroke": "freestyle",
    "course": "long",
    "gender": "male",
    "legs": 1
  },
  "season": 2026
}
```

`time_millis` is the slowest time still worth `points`; posting it back to
`/points` returns exactly that score.

## GET /seasons

```json
{
  "seasons": [
    {
      "course": "long",
      "season": 2022,
      "valid_from": "2022-01-01",
      "valid_until": "2022-12-31",
      "events": 42,
      "source_title": "FINA Point Scoring 2022 - Long Course (50m)",
      "source_url": "https://resources.fina.org/fina/document/..."
    }
  ],
  "latest": { "long": 2026, "short": 2025 }
}
```

`latest` is what a request without a `season` will use. The two courses are on
different calendars, so the numbers differ and neither should be assumed from
the other — see [Base times](./base-times.md).

## GET /base-times/{course}/{season}

One whole table, every event with its base time, plus the official document
behind it.

```bash
curl http://localhost:8000/base-times/short/2025
```

```json
{
  "course": "short",
  "season": 2025,
  "valid_from": "2025-09-01",
  "valid_until": "2026-08-31",
  "source_title": "World Aquatics Points - Base Times SCM and LCM 2026",
  "source_url": "https://resources.fina.org/fina/document/...",
  "base_times": [
    {
      "event": {
        "distance": 50,
        "stroke": "freestyle",
        "course": "short",
        "gender": "male",
        "legs": 1
      },
      "base_time": "19.90",
      "base_time_millis": 19900
    }
  ]
}
```

## GET /health

```json
{ "status": "ok", "version": "0.1.0" }
```

## Status codes

| Code  | When                                               |
| ----- | -------------------------------------------------- |
| `200` | The request was answered                           |
| `422` | The request described a swim that cannot be scored |

Unlike a file parser, there is no partial success here, so everything that goes
wrong is a 422: an unreadable time, both references or neither, a season that
does not ship, an event the table does not hold. A caller that hit one has a
bug, not a degraded result.

Two layers produce it and both look the same to a client — pydantic rejects a
malformed body, a non-positive `points`, or the wrong combination of reference
fields before the handler runs; the handler raises for a time or a lookup that
fails:

```json
{ "detail": "not a swim time: 'nonsense'" }
```

```json
{
  "detail": "no shipped base times for long course, season 1999; available: 2022, 2023, 2024, 2025, 2026"
}
```

## Generating a client

The schema is complete, so the usual generators work without hand-editing:

```bash
npx @hey-api/openapi-ts -i http://localhost:8000/openapi.json -o src/client
openapi-generator-cli generate -i http://localhost:8000/openapi.json -g go -o ./client
```

## Embedding it

The service is stateless, so it mounts into another app with one line:

```python
import aqua_points_calculator.api

app.include_router(aqua_points_calculator.api.router)
```

## Configuration

| Variable    | Default | Effect    |
| ----------- | ------- | --------- |
| `LOG_LEVEL` | `INFO`  | Log level |

A level name the logging module does not know falls back to `INFO` with a
warning — a cosmetic misconfiguration must not keep the service from starting.

There is nothing else. The base-time tables are read from the installed package
and parsed once per process; there is nothing to point at a directory or a
database.
