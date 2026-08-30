# CLI

Installed as `aqua-points-calculator`, and runnable without installing as
`python -m aqua_points_calculator` or `make dev`.

```
aqua-points-calculator [--json] {points,time,convert,seasons,base-times} ...
```

## Naming the base time

`points` and `time` both need a reference, and take it either way. The two forms
are mutually exclusive and argparse enforces that, so there is no combination to
get wrong:

| Flags                                             | Effect                              |
| ------------------------------------------------- | ----------------------------------- |
| `--base-time 46.40`                               | Use exactly this. No table is read. |
| `--distance 100 --stroke freestyle --gender male` | Look it up in a shipped table.      |

The lookup form also takes `--course` (`long` by default), `--legs` (`1` by
default, `4` for a relay) and `--season` (the latest shipped by default).

Those lookup flags are refused alongside `--base-time` rather than ignored —
silently dropping a `--season` would let you believe a historical table was
used. The HTTP API refuses the same combination.

## points

Score a swim. The time swum is the positional argument.

```bash
$ aqua-points-calculator points 51.35 --base-time 46.40
737

$ aqua-points-calculator points 51.35 --distance 100 --stroke freestyle --gender male
737

$ aqua-points-calculator points 51.35 --distance 100 --stroke freestyle --gender male --season 2022
762

$ aqua-points-calculator points 3:40.00 --distance 100 --stroke medley --gender mixed --legs 4
965
```

## time

The slowest time still worth a given score — the qualifying time a meet
announcement is after. Takes the same reference flags.

```bash
$ aqua-points-calculator time 800 --base-time 46.40
49.98

$ aqua-points-calculator time 800 --distance 100 --stroke freestyle --gender male
49.98
```

## convert

Normalise a written time to milliseconds, which is what a script piping times
between systems needs.

```bash
$ aqua-points-calculator convert 1:02,34
62340

$ aqua-points-calculator convert 62340
62340
```

## seasons

List the base-time tables that ship, with the window each one covers. The two
courses are numbered independently, and `(default)` marks the one a lookup uses
when `--season` is omitted.

```bash
$ aqua-points-calculator seasons
long   2022  2022-01-01 – 2022-12-31  42 events
long   2023  2023-01-01 – 2023-12-31  42 events
long   2024  2024-01-01 – 2024-12-31  42 events
long   2025  2025-01-01 – 2025-12-31  42 events
long   2026  2026-01-01 – 2026-12-31  42 events (default)
short  2021  2021-09-01 – 2022-08-31  46 events
short  2022  2022-09-01 – 2023-08-31  48 events
short  2023  2023-09-01 – 2024-08-31  48 events
short  2024  2024-09-01 – 2025-08-31  48 events
short  2025  2025-09-01 – 2026-08-31  48 events (default)
```

## base-times

Print one whole table, with the official document it came from.

```bash
$ aqua-points-calculator base-times --course long --season 2025
# long course, season 2025 (2025-01-01 – 2025-12-31)
# World Aquatics Points - Base Times SCM and LCM 2025
50 freestyle (long, male)              20.91
50 freestyle (long, female)            23.61
100 freestyle (long, male)             46.40
...
```

`--season` defaults to the latest shipped for that course.

## --json

By default each subcommand prints one bare value, so it drops straight into a
shell pipeline. `--json` emits the full result instead, including — for a
looked-up base time — the event and the season it came from:

```bash
$ aqua-points-calculator --json points 51.35 --base-time 46.40
{"points": 737, "base_time": "46.40", "time": "51.35"}

$ aqua-points-calculator --json points 51.35 --distance 100 --stroke freestyle --gender male
{"points": 737, "base_time": "46.40", "time": "51.35", "event": {"distance": 100, "stroke": "freestyle", "course": "long", "gender": "male", "legs": 1}, "season": 2026}

$ aqua-points-calculator --json time 800 --base-time 46.40
{"time": "49.98", "time_millis": 49982, "points": 800, "base_time": "46.40"}

$ aqua-points-calculator --json convert 1:02,34
{"time": "1:02.34", "time_millis": 62340}
```

An explicit base time yields no `event` or `season` key at all, rather than a
null one: the score belongs to no table, and saying otherwise would misreport
where the number came from.

For `seasons` and `base-times` the payload is exactly the HTTP API's
[`/seasons` and `/base-times` response](./api.md) — built by the same code — so
a script can switch between the two surfaces without remapping keys.

The flag goes before the subcommand.

## --version

```bash
aqua-points-calculator --version
```

Reads the installed distribution metadata, so it cannot drift from what was
released.

## Exit codes

| Code | Meaning                                                                                                          |
| ---- | ---------------------------------------------------------------------------------------------------------------- |
| `0`  | Success — the answer is on stdout                                                                                |
| `2`  | A bad argument: missing, not a readable time, not a positive score, or an event or season the tables do not hold |

There is nothing between the two.

An unreadable input writes to stderr and leaves stdout empty, so a pipeline
reading stdout never sees an error message where a number should be:

```bash
$ aqua-points-calculator points nonsense --base-time 46.40
error: not a swim time: 'nonsense'
$ echo $?
2
```

The same applies to a lookup that misses:

```bash
$ aqua-points-calculator points 51.35 --distance 100 --stroke freestyle --gender male --season 1999
error: no shipped base times for long course, season 1999; available: 2022, 2023, 2024, 2025, 2026
```

## Scripting

```bash
# Score a column of times for one event.
while read -r t; do
  aqua-points-calculator points "$t" --distance 100 --stroke freestyle --gender male
done < times.txt

# Pull one base time out for use elsewhere.
aqua-points-calculator --json base-times --course long \
  | jq -r '.base_times[] | select(.event.distance == 100 and .event.stroke == "freestyle" and .event.gender == "male" and .event.legs == 1) | .base_time'

# Fail the script on the first unreadable time.
set -e
aqua-points-calculator points "$time" --base-time 46.40
```
