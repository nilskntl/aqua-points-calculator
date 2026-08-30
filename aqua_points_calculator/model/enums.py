"""The coded vocabularies an event is described by.

Values are lowercase English words rather than the single letters result files
use, because these are what a JSON consumer reads: ``"butterfly"`` needs no
lookup table on the other side, ``"S"`` does.
"""

from __future__ import annotations

from enum import StrEnum


class Course(StrEnum):
    """The pool a time was swum in.

    Base times differ between the two, so a score is only meaningful together
    with the course it was computed for.
    """

    LONG = "long"
    """50 m pool."""

    SHORT = "short"
    """25 m pool."""


class Stroke(StrEnum):
    """The stroke of an event."""

    FREESTYLE = "freestyle"
    BACKSTROKE = "backstroke"
    BREASTSTROKE = "breaststroke"
    BUTTERFLY = "butterfly"
    MEDLEY = "medley"


class Gender(StrEnum):
    """The classification an event is scored under."""

    FEMALE = "female"
    MALE = "male"
    MIXED = "mixed"
