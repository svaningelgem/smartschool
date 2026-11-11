from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from functools import cached_property
from typing import TYPE_CHECKING
from zoneinfo import ZoneInfo

from ._common import DownloadableFile, create_filesystem_safe_filename
from ._objects import ApplicableAssignmentType, PlannedElement, PlannedElementDetail
from ._session import SessionMixin

if TYPE_CHECKING:
    from collections.abc import Iterator
    from datetime import date
    from pathlib import Path

    from ._objects import PlannedElementAttachment

__all__ = ["ApplicableAssignmentTypes", "PlannedElementDetails", "PlannedElementFile", "PlannedElements"]


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


@dataclass
class PlannedElementFile(DownloadableFile, SessionMixin):
    """An attachment of a planned element, as a file to download."""

    attachment: PlannedElementAttachment
    download_url: str = field(repr=False)

    @cached_property
    def filename(self) -> str:
        return create_filesystem_safe_filename(self.attachment.file_name)

    def _real_download(self, target: Path | None) -> bytes | Path:
        response = self.session.get(self.download_url)
        response.raise_for_status()
        return self._write_or_return(response.content, target)


@dataclass
class PlannedElementDetails(SessionMixin):
    """
    The detail view of one planned element from `PlannedElements`.

    The list only holds the headers; the detail adds the teacher's info for the pupils ('Info voor de leerling'),
    the attachments, the weblinks and the linked curriculum goals.

    To reproduce: open the planner and click a lesson; watch the XHR calls (`/planner/api/v1/<type>/<platform>/<id>`).
    An occurrence of a recurring meeting is addressed by its original element and date instead of its own id.

    Example:
    -------
    >>> details = PlannedElementDetails(session, element=lesson)
    >>> print(details.get().public_info)
    <p>Lees hoofdstuk 3 voor de volgende les.</p>
    >>> for file in details.files():
    >>>     file.download_to_dir(Path("downloads"))

    """

    element: PlannedElement

    @property
    def _url(self) -> str:
        element = self.element
        if (recurrence := element.recurrence) is not None:
            element_id = f"{recurrence.original_planned_element_id}_{recurrence.original_recurrence_date}"
        else:
            element_id = str(element.id)
        return f"/planner/api/v1/{element.planned_element_type}/{element.platform_id}/{element_id}"

    @cached_property
    def _detail(self) -> PlannedElementDetail:
        return PlannedElementDetail(**self.session.json(self._url))

    def get(self) -> PlannedElementDetail:
        return self._detail

    def files(self) -> list[PlannedElementFile]:
        """The attachments, ready to download."""
        return [
            PlannedElementFile(session=self.session, attachment=attachment, download_url=f"{self._url}/attachments/{attachment.id}/download")
            for attachment in self._detail.attachments
        ]
