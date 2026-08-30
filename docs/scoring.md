# Scoring

## The formula

```
P = 1000 · (B / T)³
```

|     |                       |
| --- | --------------------- |
| `P` | the point score       |
| `B` | the event's base time |
| `T` | the time swum         |

A swim exactly on the base time scores 1000. The cube means the score falls away
fast: half the speed is an eighth of the points.

| T relative to B | Score |
| --------------- | ----- |
| 0.9 × (faster)  | 1371  |
| 1.0 ×           | 1000  |
| 1.1 ×           | 751   |
| 1.5 ×           | 296   |
| 2.0 ×           | 125   |

Scores above 1000 are normal and are not capped — a world record beats the base
time it was set against as soon as the table ages.

## Truncation, not rounding

The score is truncated towards zero:

```python
points(1_000_000, 1_000_010)  # 999, not 1000
```

That swim is worth 999.97 points. The published tables read 999, so this does
too. It is the one place where "close enough" would produce a number that
disagrees with a printed result sheet.

## The inverse

`time_for_points(base, n)` returns the **slowest** time that still scores `n`:

```python
millis = time_for_points("46.40", 800)  # 49982
points("46.40", millis)  # 800
points("46.40", millis + 1)  # 799
```

"Slowest that still reaches" is the useful reading — it is the qualifying time a
meet announcement is after. The round trip is exact for every positive score;
see [Architecture](./architecture.md#why-the-inverse-walks-the-last-step) for
why that needs more than a float cube root.

## Time formats

`parse_time` accepts `[[h:]mm:]ss[.hh]`, with a dot or a comma as the decimal
separator — result sheets in the German-speaking world use the comma, timing
exports the dot.

| Written      | Milliseconds |
| ------------ | ------------ |
| `9`          | 9000         |
| `51.35`      | 51350        |
| `51,35`      | 51350        |
| `51.3`       | 51300        |
| `51.357`     | 51357        |
| `1:02.34`    | 62340        |
| `16:23.11`   | 983110       |
| `1:02:03.04` | 3723040      |

A short fraction is padded on the right, not read as an integer: `51.3` is three
tenths, which is 300 ms.

`format_time` is the inverse at hundredths, the resolution a swim is timed and
published at, dropping the minutes and hours while they are zero. `format_time`
truncates below a hundredth for the same reason the score does.

Anything else — an empty string, `0`, a negative time, `51:99.00` — raises
`InvalidTimeError`.

## Where the base time comes from

The formula is indifferent to it: `B` is a number, and `points()` takes it
directly. Two ways to obtain one are described in
[Base times](./base-times.md) — the tables this package ships for the last five
seasons of each course, or one you supply yourself.

## What is not modelled

No age-group, para or masters factors. Those are separate scoring systems
layered on top of this one; apply them to the score this returns.

Relays need nothing special from the formula: a relay is scored against a relay
base time exactly like an individual swim. The shipped tables carry those base
times as their own entries, keyed by `legs`.
