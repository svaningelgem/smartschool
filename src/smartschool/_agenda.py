from __future__ import annotations

import time
from abc import ABC
from dataclasses import dataclass
from typing import TYPE_CHECKING, ClassVar

from . import _objects as objects
from ._common import convert_to_datetime
from ._session import SessionMixin
from ._xml_interface import SmartschoolXmlWeeklyCache, _ItemT_co

if TYPE_CHECKING:
    from ._session import Smartschool


__all__ = ["AgendaLesson", "AgendaPoster", "SmartschoolHours", "SmartschoolLessons", "SmartschoolMomentInfos"]


@dataclass
class AgendaPoster(SmartschoolXmlWeeklyCache[_ItemT_co], ABC):
    """Caches the information on a weekly basis, and posts to the mentioned URL."""

    _url: ClassVar[str] = "/?module=Agenda&file=dispatcher"


@dataclass
class AgendaLesson(SessionMixin, objects.AgendaLesson):
    @property
    def hour_details(self) -> objects.AgendaHour:
        return SmartschoolHours(self.session).search_by_hour_id(self.hour_id)


@dataclass
class SmartschoolLessons(AgendaPoster[AgendaLesson]):
    """
    Interface to the retrieval of lessons for a certain date.

    To reproduce: open the agenda, one of the XHR calls is this one.

    This includes (for an example check the tests):
    - momentID: a unique identifier for this specific lesson
    - lessonID: a group id
    - hourID: link to `AgendaHours`
    - date: YYYY-mm-dd
    - subject: explanation by the teacher
    - course
    - courseTitle
    - classroom: what classroom this is in
    - classroomTitle: same as `classroom`?
    - teacher: name of the teacher (Lastname + initial of firstname)
    - teacherTitle:
    - klassen
    - klassenTitle
    - classIDs
    - bothStartStatus
    - assignmentEndStatus
    - testDeadlineStatus
    - noteStatus
    - note
    - date_listview
    - hour
    - activity
    - activityID
    - color
    - hourValue
    - components_hidden
    - freedayIcon
    - someSubjectsEmpty
    """

    _subsystem: ClassVar[str] = "agenda"
    _action: ClassVar[str] = "get lessons"
    _xpath: ClassVar[str] = ".//lesson"
    _object_to_instantiate: ClassVar[type[AgendaLesson]] = AgendaLesson

    @property
    def _params(self) -> dict:
        now = convert_to_datetime(self.timestamp_to_use).timestamp()
        in_20_days = now + 20 * 24 * 3600

        return {
            "startDateTimestamp": now,  # 1700045313
            "endDateTimestamp": in_20_days,  # 1700477313
            "filterType": "false",
            "filterID": "false",
            "gridType": "1",
            "classID": "0",
            "endDateTimestampOld": in_20_days,  # 1700477313
            "forcedTeacher": "0",
            "forcedClass": "0",
            "forcedClassroom": "0",
            "assignmentTypeID": "1",
        }


class SmartschoolHours(AgendaPoster[objects.AgendaHour]):
    """
    Interface to the retrieval of periods (called Hours in smartschool).

    To reproduce: open the agenda, one of the XHR calls is this one.

    This includes (for an example check the tests):
    - hourID: unique identifier for this period
    - start: HH:MM starting time
    - end: HH:MM ending time
    - title: how it is called in the agenda
    """

    _subsystem: ClassVar[str] = "grid"
    _action: ClassVar[str] = "get hours"
    _xpath: ClassVar[str] = ".//hour"
    _object_to_instantiate: ClassVar[type[objects.AgendaHour]] = objects.AgendaHour

    @property
    def _params(self) -> dict:
        return {"date": int(time.time())}

    def search_by_hour_id(self, hour_id: str):
        for hour in self._xml():
            if hour.hour_id == hour_id:
                return hour

        raise ValueError(f"Couldn't find {hour_id}")


class SmartschoolMomentInfos(AgendaPoster[objects.AgendaMomentInfo]):  # pylint: disable=too-few-public-methods  # query object: iterate or get()
    """
    Interface to the retrieval of one particular moment (a book-symbol in smartschool).

    To reproduce: open the agenda, click on a yellow/red book. This is the XHR call that appears.

    This includes (for an example check the tests):
    - hourID: unique identifier for this period
    - start: HH:MM starting time
    - end: HH:MM ending time
    - title: how it is called in the agenda
    """

    _subsystem: ClassVar[str] = "agenda"
    _action: ClassVar[str] = "get moment info"
    _xpath: ClassVar[str] = ".//class"
    _object_to_instantiate: ClassVar[type[objects.AgendaMomentInfo]] = objects.AgendaMomentInfo

    def __init__(self, session: Smartschool, moment_id: str):
        super().__init__(session=session)

        self._moment_id = str(moment_id).strip()
        if not self._moment_id:
            raise ValueError("Please provide a valid MomentID")

    @property
    def _params(self) -> dict:
        return {
            "momentID": self._moment_id,
            "dateID": "",
            "assignmentIDs": "",
            "activityID": "0",
        }

    def _post_process_element(self, element: dict) -> None:
        """In this XML we have `assignments.assignment`, but I don't need that `assignment` tag."""
        if element["assignments"] is None:
            element["assignments"] = []
            return

        if isinstance(element["assignments"]["assignment"], list):
            element["assignments"] = element["assignments"]["assignment"]
        else:
            element["assignments"] = [element["assignments"]["assignment"]]
