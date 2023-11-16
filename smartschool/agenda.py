from __future__ import annotations

import time
import xml.etree.ElementTree as ET
from abc import ABC, abstractmethod
from datetime import date
from typing import ClassVar, Iterator, TypeVar
from xml.sax.saxutils import quoteattr

from .common import xml_to_dict
from .objects import AgendaHour, AgendaLesson, AgendaMomentInfo
from .session import session

_T = TypeVar("_T")


class AgendaXML(ABC):
    def _construct_command(self) -> str:
        txt = "<request><command>"
        txt += f"<subsystem>{self._subsystem}</subsystem>"
        txt += f"<action>{self._action}</action>"
        txt += "<params>"

        for k, v in self._params.items():
            txt += f'<param name="{quoteattr(k)}"><![CDATA[{v}]]></param>'

        txt += "</params></command></request>"
        return txt

    def __iter__(self) -> Iterator[_T]:
        yield from self._xml()

    def _xml(self, date_to_use: date | None = None):
        today = date_to_use or date.today()
        current_week = today.strftime("%Y-%U")
        if current_week in self.cache:
            return self.cache[current_week]

        response = session.post(
            "/?module=Agenda&file=dispatcher",
            data={"command": self._construct_command()},
            headers={
                "X-Requested-With": "XMLHttpRequest",
            },
        )

        root = ET.fromstring(response.text)

        all_entries = []
        as_obj = self._object_to_instantiate
        for el in root.findall(self._xpath):
            as_dict = xml_to_dict(el)
            self._post_process_element(as_dict)
            obj = as_obj(**as_dict)
            all_entries.append(obj)

        self.cache[current_week] = all_entries

        return self.cache[current_week]

    @property
    @abstractmethod
    def _subsystem(self) -> str:
        """Returns the subsystem to request the info from."""

    @property
    @abstractmethod
    def _action(self) -> str:
        """Returns the action to send."""

    @property
    @abstractmethod
    def _params(self) -> dict:
        """Returns the parameters to send."""

    @property
    @abstractmethod
    def _xpath(self) -> str:
        """Returns the xpath to investigate."""

    @property
    @abstractmethod
    def _object_to_instantiate(self) -> type[_T]:
        """Returns the object to instantiate."""

    def _post_process_element(self, element: dict) -> None:  # noqa: B027
        """By default, this doesn't do anything, but you can adjust it when needed."""


class AgendaLessons(AgendaXML):
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

    cache: ClassVar[dict[str, list[AgendaLessons]]] = {}

    @property
    def _xpath(self) -> str:
        return ".//lesson"

    @property
    def _object_to_instantiate(self) -> type[AgendaLesson]:
        return AgendaLesson

    @property
    def _subsystem(self) -> str:
        return "agenda"

    @property
    def _action(self) -> str:
        return "get lessons"

    @property
    def _params(self) -> dict:
        now = int(time.time())
        in_5_days = now + 5 * 24 * 3600

        return {
            "startDateTimestamp": now,  # 1700045313
            "endDateTimestamp": in_5_days,  # 1700477313
            "filterType": "false",
            "filterID": "false",
            "gridType": "1",
            "classID": "0",
            "endDateTimestampOld": in_5_days,  # 1700477313
            "forcedTeacher": "0",
            "forcedClass": "0",
            "forcedClassroom": "0",
            "assignmentTypeID": "1",
        }


class AgendaHours(AgendaXML):
    """
    Interface to the retrieval of periods (called Hours in smartschool).

    To reproduce: open the agenda, one of the XHR calls is this one.

    This includes (for an example check the tests):
    - hourID: unique identifier for this period
    - start: HH:MM starting time
    - end: HH:MM ending time
    - title: how it is called in the agenda
    """

    cache: ClassVar[dict[str, list[AgendaHours]]] = {}

    @property
    def _xpath(self) -> str:
        return ".//hour"

    @property
    def _object_to_instantiate(self) -> type[AgendaHour]:
        return AgendaHour

    @property
    def _subsystem(self) -> str:
        return "grid"

    @property
    def _action(self) -> str:
        return "get hours"

    @property
    def _params(self) -> dict:
        return {"date": int(time.time())}

    def search_by_hourId(self, hourId: str, *, date_to_use: date | None = None):
        for hour in self._xml(date_to_use):
            if hour.hourID == hourId:
                return hour

        raise ValueError(f"Couldn't find {hourId}")


class AgendaMomentInfos(AgendaXML):
    """
    Interface to the retrieval of one particular moment (a book-symbol in smartschool).

    To reproduce: open the agenda, click on a yellow/red book. This is the XHR call that appears.

    This includes (for an example check the tests):
    - hourID: unique identifier for this period
    - start: HH:MM starting time
    - end: HH:MM ending time
    - title: how it is called in the agenda
    """

    cache: ClassVar[dict[str, list[AgendaMomentInfo]]] = {}

    def __init__(self, moment_id: str):
        moment_id = str(moment_id).strip()
        if not moment_id:
            raise ValueError("Please provide a valid MomentID")

        self._moment_id = moment_id

    @property
    def _xpath(self) -> str:
        return ".//class"

    @property
    def _object_to_instantiate(self) -> type[AgendaMomentInfo]:
        return AgendaMomentInfo

    @property
    def _subsystem(self) -> str:
        return "agenda"

    @property
    def _action(self) -> str:
        return "get moment info"

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
