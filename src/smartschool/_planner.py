from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import TYPE_CHECKING
from zoneinfo import ZoneInfo

from ._objects import ApplicableAssignmentType, PlannedElement, PlannedElementDetail
from ._session import SessionMixin

if TYPE_CHECKING:
    from collections.abc import Iterator
    from datetime import date

    from ._objects import PlannedElementAttachment

__all__ = ["ApplicableAssignmentTypes", "PlannedElementDetails", "PlannedElements"]


@dataclass
class ApplicableAssignmentTypes(SessionMixin, Iterable[ApplicableAssignmentType]):
    def __iter__(self) -> Iterator[ApplicableAssignmentType]:
        for type_ in self.session.json("/lesson-content/api/v1/assignments/applicable-assigment-types"):
            yield ApplicableAssignmentType(**type_)


@dataclass
class PlannedElements(SessionMixin, Iterable[PlannedElement]):
    from_date: date = field(default_factory=lambda: datetime.now(tz=ZoneInfo("Europe/Brussels")).replace(hour=0, minute=0, second=0, microsecond=0))
    till_date: date | None = None

    def __post_init__(self):
        if self.till_date is None:
            self.till_date = self.from_date + timedelta(days=34, seconds=-1)

    def __iter__(self) -> Iterator[PlannedElement]:
        assert self.till_date is not None  # set in __post_init__
        data = self.session.json(
            f"/planner/api/v1/planned-elements/user/{self.session.authenticated_user['id']}",
            data={"from": self.from_date.isoformat(), "to": self.till_date.isoformat(), "types": "planned-assignments,planned-to-dos"},
        )
        for element in data:
            yield PlannedElement(**element)


@dataclass
class PlannedElementDetails(SessionMixin):
    """
    The detail view of one planned element (a lesson or an assignment) from `PlannedElements`.

    The list only holds the headers; the detail adds the teacher's info for the pupils ('Info voor de leerling'),
    the attachments, the weblinks and the linked curriculum goals.

    To reproduce: open the planner and click a lesson; watch the XHR calls (`/planner/api/v1/<type>/<platform>/<id>`).

    Example:
    -------
    >>> detail = PlannedElementDetails(session, element=lesson).get()
    >>> print(detail.public_info)
    <p>Lees hoofdstuk 3 voor de volgende les.</p>
    >>> for attachment in detail.attachments:
    >>>     Path(attachment.file_name).write_bytes(PlannedElementDetails(session, element=lesson).download(attachment))

    """

    element: PlannedElement

    @property
    def _url(self) -> str:
        return f"/planner/api/v1/{self.element.planned_element_type}/{self.element.platform_id}/{self.element.id}"

    def get(self) -> PlannedElementDetail:
        return PlannedElementDetail(**self.session.json(self._url))

    def download(self, attachment: PlannedElementAttachment) -> bytes:
        return self.session.get(f"{self._url}/attachments/{attachment.id}/download").content
