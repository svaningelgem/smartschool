from __future__ import annotations

import json
from abc import ABC
from dataclasses import dataclass
from datetime import date, timedelta
from typing import TYPE_CHECKING, ClassVar

from logprise import logger
from pydantic import ValidationError
from pydantic.dataclasses import dataclass as pydantic_dataclass

from . import _objects as objects
from ._common import convert_to_datetime, html_to_text
from ._objects import StudentNoteParamType
from ._xml_interface import SmartschoolXmlNoCache, _ItemT_co

if TYPE_CHECKING:
    from datetime import datetime

    from ._objects import StudentNoteParam

__all__ = ["StudentAbsences", "StudentNoteDetail", "StudentNoteDetails", "StudentNotes"]

_DISPATCHER = "/?module=LVS&file=dispatcher"
# Smartschool wants a date range; this one reaches back before any pupil's file starts.
_EARLIEST = date(2000, 1, 1)


@dataclass(kw_only=True)
class _PupilOverview(SmartschoolXmlNoCache[_ItemT_co], ABC):
    """`getUserData` returns the notes and the absences of a pupil in one answer: both views share its request."""

    _url: ClassVar[str] = _DISPATCHER
    _subsystem: ClassVar[str] = "lvs_pupils"
    _action: ClassVar[str] = "getUserData"

    user_id: str = ""
    """The full Smartschool user id (`<platform>_<id>_<role>`, e.g. `49_10880_2`), sent as is. Empty: the logged-in user."""
    group_id: int = 0
    since: date | None = None
    """Start of the period (default: everything)."""
    until: date | None = None
    """End of the period (default: a year from today)."""

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

    _xpath: ClassVar[str] = ".//notes/note"
    _object_to_instantiate: ClassVar[type[objects.StudentNote]] = objects.StudentNote


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

    _xpath: ClassVar[str] = ".//absents/absent"
    _object_to_instantiate: ClassVar[type[objects.StudentAbsence]] = objects.StudentAbsence


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
    def choice(self) -> str:
        """The label chosen in the first select parameter (the measure of an "ordemaatregel", for instance); empty when there is none."""
        param = self._first(StudentNoteParamType.SELECT)
        return param.option_value if param else ""

    @property
    def attachments(self) -> list[objects.StudentNoteAttachment]:
        """The files attached to the note (Smartschool sends `{"<file id>": {...}}`, or `[]`); an empty list when there are none."""
        param = self._first(StudentNoteParamType.ATTACHMENTS)
        if not param or not param.option_value:
            return []
        try:
            decoded = json.loads(param.option_value)
            files = decoded.items() if isinstance(decoded, dict) else []
            return [objects.StudentNoteAttachment(file_id=file_id, **info) for file_id, info in files]
        except (json.JSONDecodeError, TypeError, ValidationError):
            logger.warning("Cannot decode the attachments of note {}", self.item_id)
            return []

    @property
    def fields(self) -> dict[str, str]:
        """
        Every parameter the other properties don't show (e.g. the teacher, or a second date) by title; a select by its label.

        With equal titles the last wins; the option ids behind a label stay in `params`.
        """
        consumed = {
            p.param_id
            for t in (StudentNoteParamType.TEXT, StudentNoteParamType.SELECT, StudentNoteParamType.ATTACHMENTS, StudentNoteParamType.DATE)
            if (p := self._first(t))
        }
        return {p.title: p.option_value or p.value for p in self.params if p.param_id not in consumed and p.param_type != StudentNoteParamType.INSTRUCTION}


@dataclass(kw_only=True)
class StudentNoteDetails(SmartschoolXmlNoCache[StudentNoteDetail]):
    """
    The content of one `StudentNote`: it yields a single `StudentNoteDetail`.

    To reproduce: open the pupil-follow-up system and expand a line; watch the XHR calls (`module=LVS&file=dispatcher`, action `getItemParams`).

    Example:
    -------
    >>> detail = StudentNoteDetails(session, item_id=note.item_id).get()
    >>> print(detail.text)
    Morgen is er geen les.

    """

    _url: ClassVar[str] = _DISPATCHER
    _subsystem: ClassVar[str] = "lvs_pupils"
    _action: ClassVar[str] = "getItemParams"
    _xpath: ClassVar[str] = ".//items"
    _object_to_instantiate: ClassVar[type[StudentNoteDetail]] = StudentNoteDetail

    item_id: int

    @property
    def _params(self) -> dict:
        return {"userID": 0, "itemID": self.item_id}

    def _post_process_element(self, element: dict) -> None:
        items = element.pop("item", None) or []  # <items/> arrives as {}; a single <item> is not a list
        element["params"] = items if isinstance(items, list) else [items]
        element["item_id"] = self.item_id
