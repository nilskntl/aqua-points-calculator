# Introduction

Aqua Points Calculator turns a swim time into a World Aquatics point score, and
turns a point score back into the slowest time that still reaches it.

## One formula

```
P = 1000 · (B / T)³
```

`B` is the base time for the event, `T` is the time swum. A swim exactly on the
base time scores 1000; a swim twice as slow scores 125. The result is truncated,
not rounded — 999.97 points is 999, which is how the published tables read.

## Two ways to a base time

The package ships the official World Aquatics tables for the last five seasons
of each course, so naming an event is enough:

```python
score_for(event, "51.35")
```

A base time you supply still works and reads no table, which is what covers a
national record, an age-group standard or a season older than those shipped:

```python
score("48.50", "51.35")
```

Because the table is a per-season snapshot, a score is only meaningful together
with the season it was measured against — so the result records which one it
used. See [Base times](./base-times.md).

## Integers all the way down

Times are `int` milliseconds inside the package, never `float` seconds. The
formula cubes a ratio, so a binary float would make the last digit of a score
depend on how the input happened to round. Milliseconds are also what result
files and timing systems carry, so no precision is invented on the way in.

The inverse is computed the same way: an integer cube root, corrected by hand,
so that feeding its answer back into the formula returns exactly the score that
was asked for. A float cube root is off by one often enough at these magnitudes
to shift the returned time by a millisecond.

## Three surfaces, one core

The Python library, the CLI and the FastAPI service all go through the same
`core/`. The service publishes the schema as OpenAPI, so consumers in Go, Java or
TypeScript can generate a client instead of reimplementing the formula.

## Where to go next

|                                         |                                          |
| --------------------------------------- | ---------------------------------------- |
| [Getting Started](./getting-started.md) | Install, score a swim, run the service   |
| [Architecture](./architecture.md)       | The pipeline and the integer decision    |
| [Scoring](./scoring.md)                 | The formula, the truncation, the inverse |
| [Data Schema](./data-schema.md)         | How a score is laid out                  |
| [HTTP API](./api.md)                    | Endpoints, payloads, client generation   |
| [CLI](./cli.md)                         | Subcommands, flags, exit codes           |
| [Extending](./extending.md)             | Wiring in a base-time table              |

## Out of scope

No age-group, para or masters classification factors: those are separate scoring
systems layered on top of this one, and a caller that needs them can apply them
to the score this returns.

No live record tracking. A base time is a snapshot taken on the first day of a
season, which is what World Aquatics defines it to be, so a record broken
mid-season changes the next table rather than the current one.
