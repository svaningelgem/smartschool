from __future__ import annotations

import json
from abc import ABC
from dataclasses import dataclass
from datetime import date, timedelta
from typing import TYPE_CHECKING, Any

from logprise import logger
from pydantic.dataclasses import dataclass as pydantic_dataclass

from . import _objects as objects
from ._common import convert_to_datetime, html_to_text
from ._objects import StudentNoteParamType
from ._xml_interface import SmartschoolXmlNoCache, _ItemT_co

if TYPE_CHECKING:
    from datetime import datetime

    from ._objects import StudentNoteParam

__all__ = ["StudentAbsences", "StudentNoteDetail", "StudentNoteDetails", "StudentNotes"]

# Smartschool wants a date range; this one reaches back before any pupil's file starts.
_EARLIEST = date(2000, 1, 1)


class _StudentNotesPoster:  # pylint: disable=too-few-public-methods  # mixin pinning the endpoint
    _url = "/?module=LVS&file=dispatcher"


@dataclass(kw_only=True)
class _PupilOverview(_StudentNotesPoster, SmartschoolXmlNoCache[_ItemT_co], ABC):
    """`getUserData` returns the notes and the absences of a pupil in one answer: both views share its request."""

    user_id: str = ""
    """The full Smartschool user id (`<platform>_<id>_<role>`, e.g. `49_10880_2`), sent as is. Empty: the logged-in user."""
    group_id: int = 0
    since: date | None = None
    """Start of the period (default: everything)."""
    until: date | None = None
    """End of the period (default: a year from today)."""

    @property
    def _subsystem(self) -> str:
        return "lvs_pupils"

    @property
    def _action(self) -> str:
        return "getUserData"

    @property
    def _params(self) -> dict:
        since = self.since or _EARLIEST
        until = self.until or date.today() + timedelta(days=366)
        return {
            "userID": self.user_id or self.session.authenticated_user["id"],
            "groupID": self.group_id,
            "toolbarType": "main",
            "syRange": json.dumps({"from": since.strftime("%Y-%m-%d"), "until": until.strftime("%Y-%m-%d")}),
            "viewAllFilter": "[]",
            "filterData": "0",
        }


@dataclass
class StudentNotes(_PupilOverview[objects.StudentNote]):
    """
    The notes ("dossierlijnen") in the pupil-follow-up system (leerlingvolgsysteem, LVS) of a pupil.

    This only lists the headers: use `StudentNoteDetails` for the content of one note. Notes with `private` set are
    meant for staff: the server decides what a logged-in pupil gets to see, this class doesn't filter.

    To reproduce: open the pupil-follow-up system -> 'Alle informatie' and watch the XHR calls (`module=LVS&file=dispatcher`, action `getUserData`).

    Example:
    -------
    >>> for note in StudentNotes(session):
    >>>     print(note.date.date(), note.cat_name, note.title)
    2025-10-02 Mededeling Excursie naar het museum

    """

    @property
    def _xpath(self) -> str:
        return ".//notes/note"

    @property
    def _object_to_instantiate(self) -> type[objects.StudentNote]:
        return objects.StudentNote


@dataclass
class StudentAbsences(_PupilOverview[objects.StudentAbsence]):
    """
    The absences of a pupil, as registered in the pupil-follow-up system (leerlingvolgsysteem, LVS).

    To reproduce: open the pupil-follow-up system -> 'Alle informatie' and watch the XHR calls (`module=LVS&file=dispatcher`, action `getUserData`).

    Example:
    -------
    >>> for absence in StudentAbsences(session):
    >>>     print(absence.date, absence.part_of_day, absence.description)
    2025-10-02 VM Ziek

    """

    @property
    def _xpath(self) -> str:
        return ".//absents/absent"

    @property
    def _object_to_instantiate(self) -> type[objects.StudentAbsence]:
        return objects.StudentAbsence


@pydantic_dataclass
class StudentNoteDetail(objects.StudentNoteDetail):
    """
    The content of one `StudentNote`, interpreted from its parameters. Which parameters exist differs per category.

    `params` is the complete view; the properties interpret the first parameter of each type. A property whose parameter
    is missing answers empty (`""`, `[]`, `{}`); only `date` is `None` then.
    """

    def _first(self, param_type: StudentNoteParamType) -> StudentNoteParam | None:
        return next((p for p in self.params if p.param_type == param_type), None)

    @property
    def text_html(self) -> str:
        """The free text of an announcement as the HTML Smartschool sends it; empty when the note has none."""
        param = self._first(StudentNoteParamType.TEXT)
        return param.value if param else ""

    @property
    def text(self) -> str:
        """The free text of an announcement without HTML; empty when the note has none."""
        return html_to_text(self.text_html)

    @property
    def date(self) -> datetime | None:
        """The date parameter, for categories that have one (an announcement doesn't: use `StudentNote.date`)."""
        param = self._first(StudentNoteParamType.DATE)
        return convert_to_datetime(param.value) if param and param.value else None

    @property
    def measure(self) -> str:
        """The text of the disciplinary measure ("ordemaatregel") that was chosen; empty when there is none."""
        param = self._first(StudentNoteParamType.MEASURE)
        return param.option_value if param else ""

    @property
    def attachments(self) -> list[Any]:
        """The attachments, as decoded from the JSON Smartschool sends; an empty list when there are none."""
        param = self._first(StudentNoteParamType.ATTACHMENTS)
        if not param or not param.option_value:
            return []
        try:
            decoded = json.loads(param.option_value)
        except json.JSONDecodeError:
            logger.warning("Cannot decode the attachments of note {}", self.item_id)
            return []
        return decoded if isinstance(decoded, list) else []

    @property
    def fields(self) -> dict[str, str]:
        """Every parameter the other properties don't show (e.g. the teacher, or a second date) by title; with equal titles the last wins."""
        consumed = {
            p.param_id
            for t in (StudentNoteParamType.TEXT, StudentNoteParamType.MEASURE, StudentNoteParamType.ATTACHMENTS, StudentNoteParamType.DATE)
            if (p := self._first(t))
        }
        return {p.title: p.value for p in self.params if p.param_id not in consumed and p.param_type != StudentNoteParamType.INSTRUCTION}


@dataclass(kw_only=True)
class StudentNoteDetails(_StudentNotesPoster, SmartschoolXmlNoCache[StudentNoteDetail]):
    """
    The content of one `StudentNote`: it yields a single `StudentNoteDetail`.

    To reproduce: open the pupil-follow-up system and expand a line; watch the XHR calls (`module=LVS&file=dispatcher`, action `getItemParams`).

    Example:
    -------
    >>> detail = StudentNoteDetails(session, item_id=note.item_id).get()
    >>> print(detail.text)
    Morgen is er geen les.

    """

    item_id: int

    @property
    def _subsystem(self) -> str:
        return "lvs_pupils"

    @property
    def _action(self) -> str:
        return "getItemParams"

    @property
    def _params(self) -> dict:
        return {"userID": 0, "itemID": self.item_id}

    @property
    def _xpath(self) -> str:
        return ".//items"

    @property
    def _object_to_instantiate(self) -> type[StudentNoteDetail]:
        return StudentNoteDetail

    def _post_process_element(self, element: dict) -> None:
        items = element.pop("item", None) or []  # <items/> arrives as {}; a single <item> is not a list
        element["params"] = items if isinstance(items, list) else [items]
        element["item_id"] = self.item_id
