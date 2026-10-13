from __future__ import annotations

import json
from abc import ABC
from dataclasses import dataclass
from datetime import date, timedelta

from . import _objects as objects
from ._xml_interface import SmartschoolXmlNoCache, _ItemT_co

__all__ = ["StudentAbsences", "StudentNoteDetails", "StudentNotes"]

# Smartschool wants a date range; this one reaches back before any pupil's file starts.
_EARLIEST = date(2000, 1, 1)


class _StudentNotesPoster:  # pylint: disable=too-few-public-methods  # mixin pinning the endpoint
    _url = "/?module=LVS&file=dispatcher"


@dataclass(kw_only=True)
class _PupilOverview(_StudentNotesPoster, SmartschoolXmlNoCache[_ItemT_co], ABC):
    """`getUserData` returns the notes and the absences of a pupil in one answer: both views share its request."""

    pupil_id: str | None = None
    """The pupil to query. Defaults (also when empty) to the logged-in user. The full id, e.g. `49_10880_2`, is sent as is."""
    group_id: int = 0
    since: date | None = None
    """Only ask for the period starting here (default: everything)."""

    @property
    def _subsystem(self) -> str:
        return "lvs_pupils"

    @property
    def _action(self) -> str:
        return "getUserData"

    @property
    def _params(self) -> dict:
        return {
            "userID": self.pupil_id or self.session.authenticated_user["id"],
            "groupID": self.group_id,
            "toolbarType": "main",
            "syRange": json.dumps({"from": (self.since or _EARLIEST).isoformat(), "until": (date.today() + timedelta(days=366)).isoformat()}),
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


@dataclass(kw_only=True)
class StudentNoteDetails(_StudentNotesPoster, SmartschoolXmlNoCache[objects.StudentNoteDetail]):
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
        return ".//items[item]"

    @property
    def _object_to_instantiate(self) -> type[objects.StudentNoteDetail]:
        return objects.StudentNoteDetail

    def _post_process_element(self, element: dict) -> None:
        # A single <item> is not parsed as a list.
        items = element["item"]
        element["params"] = items if isinstance(items, list) else [items]
        element["item_id"] = self.item_id
