# Extending

## Adding a season

The YAML tables under `aqua_points_calculator/data/base_times/` are **generated,
not hand-maintained**. `tools/generate_base_times.py` builds them from the text
of the official World Aquatics PDFs, and re-running it reproduces the shipped
files byte for byte.

To add a season:

1. Download the new publication and extract its text layout:

   ```bash
   mkdir -p work
   curl -sL <pdf-url> -o work/base2027.pdf
   pdftotext -layout work/base2027.pdf work/base2027.txt
   ```

2. Register it in `tools/generate_base_times.py` — add the document to
   `BASE_DOCS` (or to `SCORING`, if World Aquatics only published the full
   point-scoring tables that year) and add the season to `WANTED`.

3. Regenerate and check the diff:

   ```bash
   python tools/generate_base_times.py work/
   git diff aqua_points_calculator/data/base_times/
   ```

   Only the new file should appear. A change to an existing one means the parser
   read something differently than before, and is a bug until explained.

4. `make test-it`. The invariants in `tests/unit/test_data.py` run over every
   shipped file, so a new table is checked the moment it lands.

The parser cross-checks each value against the second column the PDFs print for
it. Where the two disagree, resolve it against the point-scoring table for the
same season and record the finding in `NOTES` — there is one such case already,
documented in `short-2022.yaml`.

## Adding a stroke or a course

`model/enums.py` holds the three vocabularies. Adding a member is one line, and
because they are `StrEnum` the new value serialises and appears in the OpenAPI
document with no further work:

```python
class Stroke(StrEnum):
    ...
    KICK = "kick"
```

Two consequences worth knowing. An added member is a breaking change for a
generated client that exhaustively switches on the enum. And a stroke with no
entry in any shipped table will raise `UnknownEventError` on every lookup, which
is correct — but if the tables should cover it, they need regenerating too.

## Using a reference the tables do not hold

Nothing needs extending for this. A national record, an age-group standard, a
club benchmark or a season older than the five shipped is just a base time you
pass in:

```python
from aqua_points_calculator import score

score("48.50", "51.35")
```

That path reads no table and takes no season. If you maintain a whole set of
such standards, keep them in your own mapping keyed on `Event` — the model is
frozen and hashable precisely so it can be a dictionary key:

```python
CLUB_STANDARDS = {
    Event(distance=100, stroke=Stroke.FREESTYLE, course=Course.LONG, gender=Gender.MALE): "48.50",
}

score(CLUB_STANDARDS[event], swum, event)
```

## Adding an endpoint

Handlers live in `api/routes.py`, their request and response models in
`api/schemas.py`. Keep them apart: `Score` is what the calculator computes, the
schemas are what the wire carries.

Four things a new route should keep doing:

- Be a plain `def`. Scoring is a handful of integer operations against data
  already in memory; FastAPI runs sync handlers in a worker thread, which keeps
  the event loop free without an executor.
- Translate every calculator error into a 422 through `_unprocessable`. The core
  raises its own exception types precisely so the HTTP layer decides the status
  code, not the core.
- Validate an either/or on the schema, not in the handler. `_Reference` is where
  the `base_time`/`event` exclusivity lives, so both endpoints get it and
  neither hand-rolls it.
- Hold no state. The tables are read from the installed package and cached by
  `functools.cache`; there is nothing else to keep.

## Adding a subcommand

`cli.py` builds its parser in `_build_parser` and dispatches in `main`. A new
subcommand needs an `add_parser(...)` block and a branch that calls `_emit` with
both forms — the bare value for a pipeline, the full dict for `--json`.

If it needs a base time, call `_add_reference(parser)` and then `_reference(args)`
rather than re-deriving the either/or; argparse enforces the exclusivity itself.

Keep the exit codes as they are: `0` or `2`, nothing between.

## Running the checks

```bash
make format      # before committing; the pre-commit hook does the staged files
make lint
make typecheck
make test-it     # unit + integration + the 80% coverage gate
make audit
```

CI runs exactly these through the same Makefile, so a green `make` locally is a
green CI. The single required check is `CI passed`.

## Releasing

Commits follow Conventional Commits. Release Please reads them on every push to
main and maintains a Release PR; merging that PR tags the version, publishes the
GitHub Release and uploads to PyPI.

| Prefix                                  | Effect                  |
| --------------------------------------- | ----------------------- |
| `fix:`                                  | patch                   |
| `feat:`                                 | minor                   |
| `feat!:` / `BREAKING CHANGE:`           | major                   |
| `chore:` `docs:` `ci:` `test:` `build:` | no release on their own |

A new base-time season is a `feat:` — it changes what the package answers.

The version lives only in `pyproject.toml` and the release manifest;
`__version__` reads it from the installed distribution metadata, so there is
nothing to bump by hand.
