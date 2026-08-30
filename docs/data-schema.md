# Data Schema

Everything is a pydantic model, so the same definitions validate input,
serialise output and render themselves into the OpenAPI document. A consumer in
another language generates a client from `/openapi.json` rather than
reimplementing any of this.

## Score

The result of scoring one swim.

| Field              | Type            | Meaning                              |
| ------------------ | --------------- | ------------------------------------ |
| `points`           | `int`           | The point score, truncated           |
| `time_millis`      | `int`           | The time swum, in milliseconds       |
| `time`             | `str`           | The same time, as written            |
| `base_time_millis` | `int`           | The base time scored against         |
| `base_time`        | `str`           | The same base time, as written       |
| `event`            | `Event \| null` | The event, when the caller named one |

Both representations of both times are carried on purpose: a consumer never has
to reimplement the formatting to display a payload, and never has to reparse a
string to do arithmetic on one.

```json
{
  "points": 737,
  "time_millis": 51350,
  "time": "51.35",
  "base_time_millis": 46400,
  "base_time": "46.40",
  "event": null,
  "season": null
}
```

`season` records which shipped table the base time came from. It is `null` when
the caller passed the base time in — that score belongs to no table, and
claiming one would misreport where the number came from.

Build one either way:

| Constructor                                   | Package-level    | Base time                 |
| --------------------------------------------- | ---------------- | ------------------------- |
| `Score.for_swim(base_time, time, event=None)` | `score(...)`     | Supplied by the caller    |
| `Score.for_event(event, time, season=None)`   | `score_for(...)` | Read from a shipped table |

They are two methods rather than one with mutually exclusive arguments, so
neither has a call that makes no sense. See [Base times](./base-times.md).

## Event

What a swim was swum in — only the four facets that select a base time.

| Field      | Type      | Meaning                         |
| ---------- | --------- | ------------------------------- |
| `distance` | `int > 0` | Race distance in metres         |
| `stroke`   | `Stroke`  | The stroke swum                 |
| `course`   | `Course`  | Long or short                   |
| `gender`   | `Gender`  | The classification scored under |

Everything else a meet programme carries about an event — heat, session, age
group, entry deadline — has no bearing on a point score and is the caller's
business.

`Event.label()` renders it as `"100 freestyle (long, male)"`, or
`"4x100 medley (long, mixed)"` for a relay. `Event.is_relay` is `legs > 1`.

The model is **frozen**, and therefore hashable. That is not decoration: a
base-time table is a mapping from event to time, and this is the key type — both
for the tables that ship and for any set of standards you keep yourself.

Whether the event is an input depends on how you scored. With `score_for` it
selects the base time. With `score` it is only a label riding along on the
result so a batch of scores stays self-describing, and the base time you passed
is what the score was computed from.

A relay is a **separate entry** from the individual event of the same distance,
and `legs` is the only thing distinguishing them.

## Vocabularies

All three are `StrEnum`, so they serialise as words. A JSON consumer reads
`"freestyle"` and needs no lookup table; `"S"` would need one.

| `Course` |           |
| -------- | --------- |
| `long`   | 50 m pool |
| `short`  | 25 m pool |

| `Stroke`       |
| -------------- |
| `freestyle`    |
| `backstroke`   |
| `breaststroke` |
| `butterfly`    |
| `medley`       |

| `Gender` |
| -------- |
| `female` |
| `male`   |
| `mixed`  |

Course is part of the event because base times differ between the two: a score
is only meaningful together with the course it was computed for. It also selects
which table a lookup reads, and the two courses run on different season
calendars — see [Base times](./base-times.md).

## Wire models

`api/schemas.py` holds `ScoreRequest`, `ScoreResponse`, `TimeRequest`,
`TimeResponse`, `SeasonsResponse`, `BaseTimesResponse` and `HealthResponse`.
They are documented in the [HTTP API](./api.md) and are deliberately separate
from the models above — see
[Architecture](./architecture.md#why-the-api-models-are-separate-from-the-domain-models).

`SeasonsResponse` and `BaseTimesResponse` are also what the CLI's `--json`
prints for its table listings — one construction behind both surfaces, and the
module needs only pydantic, so the CLI imports it without the `api` extra.

`ScoreRequest` and `TimeRequest` share a `_Reference` base that validates the
`base_time`/`event` either/or. The library keeps those two paths in two
functions and needs no such validation; one HTTP endpoint has to accept both
shapes, so the check lives there and nowhere else.

## BaseTimeTable

What `aqua_points_calculator.data.table(course, season)` returns — one shipped
table, loaded from its YAML file and parsed once per process.

| Field         | Type               | Meaning                                   |
| ------------- | ------------------ | ----------------------------------------- |
| `course`      | `Course`           | The course the table applies to           |
| `season`      | `int`              | The season, numbered per course           |
| `valid_from`  | `date`             | First day the table applies               |
| `valid_until` | `date`             | Last day the table applies                |
| `source`      | `Source`           | The official publication behind it        |
| `times`       | `dict[Event, int]` | Base time in milliseconds, keyed by event |

`times` is excluded from serialisation — the HTTP surface publishes it through
`BaseTimesResponse` as a list, because a JSON object cannot be keyed on a model.
Use `table.base_time(event)` for one entry and `table.events()` for the keys.

`Source` is a `title` and a `url`, so any score can be traced back to the
document its base time was printed in.
