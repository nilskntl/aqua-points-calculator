"""The data schema.

Pydantic models, so the same definitions validate input, serialise output and
render themselves into the OpenAPI document the HTTP surface publishes. Other
services consume this schema; they should not need the Python objects.
"""

from .enums import Course, Gender, Stroke
from .event import Event
from .score import Score

__all__ = ["Course", "Event", "Gender", "Score", "Stroke"]
