from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import TYPE_CHECKING
from zoneinfo import ZoneInfo

from ._objects import ApplicableAssignmentType, PlannedElement
from ._session import SessionMixin

if TYPE_CHECKING:
    from collections.abc import Iterator
    from datetime import date

__all__ = ["ApplicableAssignmentTypes", "PlannedElements"]


@dataclass
class ApplicableAssignmentTypes(SessionMixin, Iterable[ApplicableAssignmentType]):
    def __iter__(self) -> Iterator[ApplicableAssignmentType]:
        for type_ in self.session.json("/lesson-content/api/v1/assignments/applicable-assigment-types"):
            yield ApplicableAssignmentType(**type_)


@dataclass
class PlannedElements(SessionMixin, Iterable[PlannedElement]):
    """
    The elements in the planner of the logged-in user between `from_date` and `till_date`.

    `element_types` picks what the planner returns: one type name or several. The default is the assignments and to-dos;
    nothing (`None`, an empty tuple) asks for everything. Other types the planner knows include `planned-lessons` (the
    timetable, with each lesson's subject as its name) and `planned-placeholders` (timetable slots without content).

    Example:
    -------
    >>> for lesson in PlannedElements(session, element_types="planned-lessons"):
    >>>     print(lesson.period.date_time_from, lesson.courses[0].name, lesson.name)
    2025-05-06 08:30:00+02:00 Wiskunde Tweedegraadsvergelijkingen

    """

    from_date: date = field(default_factory=lambda: datetime.now(tz=ZoneInfo("Europe/Brussels")).replace(hour=0, minute=0, second=0, microsecond=0))
    till_date: date | None = None
    element_types: str | Iterable[str] | None = ("planned-assignments", "planned-to-dos")

    def __post_init__(self):
        if self.till_date is None:
            self.till_date = self.from_date + timedelta(days=34, seconds=-1)

        types = self.element_types or ()
        self.element_types = (types,) if isinstance(types, str) else tuple(types)

    def __iter__(self) -> Iterator[PlannedElement]:
        assert self.till_date is not None  # set in __post_init__
        params = {"from": self.from_date.isoformat(), "to": self.till_date.isoformat()}
        if self.element_types:
            params["types"] = ",".join(self.element_types)

        for element in self.session.json(f"/planner/api/v1/planned-elements/user/{self.session.authenticated_user['id']}", data=params):
            yield PlannedElement(**element)
