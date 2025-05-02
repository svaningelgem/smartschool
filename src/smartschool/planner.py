from collections.abc import Iterator
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from .objects import ApplicableAssignmentType, PlannedElement
from .session import session


class ApplicableAssignmentTypes:
    def __iter__(self) -> Iterator[ApplicableAssignmentType]:
        for type_ in session.json("/lesson-content/api/v1/assignments/applicable-assigment-types"):
            yield ApplicableAssignmentType(**type_)


class PlannedElements:
    from_date: date = datetime.now(tz=ZoneInfo("Europe/Brussels")).replace(hour=0, minute=0, second=0, microsecond=0)
    till_date: date = from_date + timedelta(days=5, seconds=-1)

    def __iter__(self) -> Iterator[PlannedElement]:
        for element in session.json(
            f"/planner/api/v1/planned-elements/user/{session.authenticated_user['id']}",
            data={"from": self.from_date.isoformat(), "till": self.till_date.isoformat()},
        ):
            yield PlannedElement(**element)
