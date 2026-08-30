"""The command line surface.

Five subcommands over the same core the library exposes:

``points``
    Score a swim.
``time``
    Invert it — the slowest time still worth a given score.
``convert``
    Normalise a written time to milliseconds and back, which is what a script
    piping times between systems actually needs.
``seasons``
    List the base-time tables that ship with the package.
``base-times``
    Print one whole table.

``points`` and ``time`` take their reference either way: ``--base-time`` for one
you supply, or ``--distance/--stroke/--gender`` (plus ``--course``, and
``--season`` for a historical table) to look one up.

Exit codes: ``0`` on success, ``2`` on a bad argument (argparse's own code, and
what a shell script checks), ``1`` on nothing else.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence

from . import __version__

# schemas needs only pydantic, not FastAPI, so this import works without the
# ``api`` extra — the CLI's --json table listings are the API's payloads.
from .api.schemas import BaseTimesResponse, SeasonsResponse
from .core.points import InvalidScoreError, points, time_for_points
from .core.times import InvalidTimeError, coerce_time, format_time
from .data.tables import (
    UnknownEventError,
    UnknownSeasonError,
    resolve_base_time,
    resolve_table,
)
from .model.enums import Course, Gender, Stroke
from .model.event import Event

#: Everything the calculator raises for input it cannot use. All of it means the
#: same thing at a shell: the arguments did not describe a swim.
_BAD_INPUT = (InvalidTimeError, InvalidScoreError, UnknownSeasonError, UnknownEventError)


def _fail(message: str) -> SystemExit:
    """A bad argument the parser could not catch itself.

    Args:
        message: What was wrong with it.

    Returns:
        The exception to raise: exit code 2, like every other bad argument.
    """
    print(f"error: {message}", file=sys.stderr)
    return SystemExit(2)


def _positive_int(value: str) -> int:
    """argparse type for the flags the event model requires to be positive.

    Rejecting here keeps a ``--distance -100`` inside argparse's own error
    path — a clean message and exit code 2 — instead of surfacing as a pydantic
    traceback from the model.

    Args:
        value: The raw argument.

    Returns:
        The parsed number.

    Raises:
        argparse.ArgumentTypeError: If the value is not a positive integer.
    """
    try:
        number = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"not a whole number: {value!r}") from None
    if number <= 0:
        raise argparse.ArgumentTypeError(f"must be positive: {value}")
    return number


def _add_reference(parser: argparse.ArgumentParser) -> None:
    """Add the base-time either/or to a subcommand.

    argparse enforces the exclusivity itself, so neither the handler nor the
    user has to think about the combination that makes no sense.

    Args:
        parser: The subcommand parser to extend.
    """
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--base-time", help="an explicit base time, e.g. 46.40")
    group.add_argument(
        "--distance", type=_positive_int, help="race distance in metres — looks the base time up"
    )
    parser.add_argument(
        "--stroke", choices=[s.value for s in Stroke], help="stroke, with --distance"
    )
    parser.add_argument(
        "--gender", choices=[g.value for g in Gender], help="classification, with --distance"
    )
    parser.add_argument(
        "--course",
        choices=[c.value for c in Course],
        default=Course.LONG.value,
        help="pool length (default: long)",
    )
    parser.add_argument("--legs", type=_positive_int, default=1, help="4 for a relay (default: 1)")
    parser.add_argument(
        "--season", type=int, help="which season's table (default: the latest shipped)"
    )


def _build_parser() -> argparse.ArgumentParser:
    """Assemble the argument parser.

    Returns:
        The parser, with every subcommand registered.
    """
    parser = argparse.ArgumentParser(
        prog="aqua-points-calculator",
        description="World Aquatics point scores for swimming performances.",
    )
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument(
        "--json",
        action="store_true",
        help="emit the result as a JSON object instead of a bare value",
    )
    subcommands = parser.add_subparsers(dest="command", required=True)

    score_cmd = subcommands.add_parser("points", help="score a swim")
    score_cmd.add_argument("time", help="the time swum, e.g. 51.35")
    _add_reference(score_cmd)

    time_cmd = subcommands.add_parser("time", help="the slowest time still worth a score")
    time_cmd.add_argument("points", type=int, help="the point score to reach")
    _add_reference(time_cmd)

    convert_cmd = subcommands.add_parser("convert", help="normalise a time")
    convert_cmd.add_argument("time", help="a written time, or milliseconds")

    subcommands.add_parser("seasons", help="list the shipped base-time tables")

    dump_cmd = subcommands.add_parser("base-times", help="print one base-time table")
    dump_cmd.add_argument("--course", choices=[c.value for c in Course], default=Course.LONG.value)
    dump_cmd.add_argument("--season", type=int, help="default: the latest shipped")

    return parser


def _event_from(args: argparse.Namespace) -> Event:
    """Build the event a lookup needs from the parsed arguments.

    Args:
        args: The parsed namespace.

    Returns:
        The event.

    Raises:
        SystemExit: With code 2 if --distance was given without its companions.
    """
    if args.stroke is None or args.gender is None:
        raise _fail("--distance also needs --stroke and --gender")
    return Event(
        distance=args.distance,
        stroke=Stroke(args.stroke),
        course=Course(args.course),
        gender=Gender(args.gender),
        legs=args.legs,
    )


def _reference(args: argparse.Namespace) -> tuple[int, Event | None, int | None]:
    """Resolve the base time a subcommand was pointed at.

    Args:
        args: The parsed namespace.

    Returns:
        The base time in milliseconds, the event if one was named, and the
        season the base time came from if it was looked up.

    Raises:
        SystemExit: With code 2 if a lookup flag was sent alongside --base-time.
    """
    if args.base_time is not None:
        # Silently dropping these would let the caller believe a table was
        # consulted; the API refuses the same combination.
        ignored = [
            flag
            for flag, given in (
                ("--stroke", args.stroke is not None),
                ("--gender", args.gender is not None),
                ("--legs", args.legs != 1),
                ("--season", args.season is not None),
            )
            if given
        ]
        if ignored:
            raise _fail(f"{', '.join(ignored)} only apply with --distance, not --base-time")
        return coerce_time(args.base_time), None, None
    event = _event_from(args)
    base_millis, season = resolve_base_time(event, args.season)
    return base_millis, event, season


def _emit(payload: dict[str, object], plain: str, as_json: bool) -> None:
    """Print a result in whichever form was asked for.

    Args:
        payload: The full result, for ``--json``.
        plain: The single value a shell script wants by default.
        as_json: Whether ``--json`` was passed.
    """
    if as_json:
        print(json.dumps(payload, ensure_ascii=False))
    else:
        print(plain)


def _reference_payload(event: Event | None, season: int | None) -> dict[str, object]:
    """The part of a JSON result that records where the base time came from.

    Args:
        event: The event, if one was named.
        season: The season, if the base time was looked up.

    Returns:
        The fields to merge into the payload.
    """
    if event is None:
        return {}
    return {"event": event.model_dump(mode="json"), "season": season}


def _run_seasons(as_json: bool) -> None:
    """List every shipped table.

    The JSON form is the API's ``/seasons`` payload, built by the same code, so
    a script can switch between the two surfaces without remapping keys.

    Args:
        as_json: Whether ``--json`` was passed.
    """
    listing = SeasonsResponse.shipped()
    if as_json:
        print(listing.model_dump_json())
        return
    for info in listing.seasons:
        marker = " (default)" if info.season == listing.latest[info.course] else ""
        print(
            f"{info.course:<6} {info.season}  "
            f"{info.valid_from} – {info.valid_until}  "
            f"{info.events:>2} events{marker}"
        )


def _run_base_times(args: argparse.Namespace, as_json: bool) -> None:
    """Print one whole table.

    The JSON form is the API's ``/base-times/{course}/{season}`` payload, built
    by the same code, so a script can switch between the two surfaces without
    remapping keys.

    Args:
        args: The parsed namespace.
        as_json: Whether ``--json`` was passed.
    """
    listing = BaseTimesResponse.for_table(resolve_table(Course(args.course), args.season))
    if as_json:
        print(listing.model_dump_json())
        return
    print(
        f"# {listing.course} course, season {listing.season} "
        f"({listing.valid_from} – {listing.valid_until})"
    )
    print(f"# {listing.source_title}")
    for entry in listing.base_times:
        print(f"{entry.event.label():<38} {entry.base_time}")


def main(argv: Sequence[str] | None = None) -> int:
    """Run the CLI.

    Args:
        argv: The arguments, defaulting to ``sys.argv[1:]``.

    Returns:
        The process exit code.
    """
    args = _build_parser().parse_args(argv)

    try:
        if args.command == "points":
            base_millis, event, season = _reference(args)
            swum_millis = coerce_time(args.time)
            result = points(base_millis, swum_millis)
            _emit(
                {
                    "points": result,
                    "base_time": format_time(base_millis),
                    # The canonical rendering, not the argv echo: "1:02,34" and
                    # "1:02.34" must land in the payload identically, the way
                    # the API's Score does.
                    "time": format_time(swum_millis),
                    **_reference_payload(event, season),
                },
                str(result),
                args.json,
            )
        elif args.command == "time":
            base_millis, event, season = _reference(args)
            millis = time_for_points(base_millis, args.points)
            _emit(
                {
                    "time": format_time(millis),
                    "time_millis": millis,
                    "points": args.points,
                    "base_time": format_time(base_millis),
                    **_reference_payload(event, season),
                },
                format_time(millis),
                args.json,
            )
        elif args.command == "convert":
            millis = coerce_time(args.time)
            _emit(
                {"time": format_time(millis), "time_millis": millis},
                str(millis),
                args.json,
            )
        elif args.command == "seasons":
            _run_seasons(args.json)
        else:
            _run_base_times(args, args.json)
    except _BAD_INPUT as error:
        # argparse's own code for a bad argument: to the caller this is the same
        # class of problem as a missing one, and shell scripts branch on it.
        print(f"error: {error}", file=sys.stderr)
        return 2

    return 0
