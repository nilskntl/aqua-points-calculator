"""Shared fixtures.

The base time used across the suite is the real World Aquatics figure for the
men's 100 m freestyle, long course — the same number the shipped 2025 and 2026
tables carry. Using a real one keeps the formula tests and the table tests
talking about the same swim.
"""

from __future__ import annotations

import pytest

from aqua_points_calculator.model.enums import Course, Gender, Stroke
from aqua_points_calculator.model.event import Event


@pytest.fixture
def base_time() -> str:
    """The base time for the 100 m freestyle, long course, men."""
    return "46.40"


@pytest.fixture
def event() -> Event:
    """The event that base time belongs to."""
    return Event(
        distance=100,
        stroke=Stroke.FREESTYLE,
        course=Course.LONG,
        gender=Gender.MALE,
    )


@pytest.fixture
def relay() -> Event:
    """A relay event, to cover the multi-leg path."""
    return Event(
        distance=100,
        stroke=Stroke.MEDLEY,
        course=Course.LONG,
        gender=Gender.MIXED,
        legs=4,
    )
