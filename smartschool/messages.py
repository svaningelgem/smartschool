from __future__ import annotations

from enum import Enum

from ._xml_interface import SmartschoolXML
from .objects import Message

__all__ = ["SortField", "SortOrder", "BoxType", "Messages"]


class SortField(Enum):
    DATE = "date"
    FROM = "from"
    READ_UNREAD = "status"
    ATTACHMENT = "attachment"
    FLAG = "label"


class SortOrder(Enum):
    ASC = "asc"
    DESC = "desc"


class BoxType(Enum):
    INBOX = "inbox"
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    SENT = "outbox"
    TRASH = "trash"


class Messages(SmartschoolXML):
    """
    Interfaces the mailbox principle in Smartschool.

    To reproduce: Open the messages and watch the XHR calls.

    Example:
    -------
    >>> for message in Messages():
    >>>     print(message.subject)
    Re: LO les
    Frans
    """

    __is_cached__ = False

    def __init__(
        self,
        box_type: BoxType = BoxType.INBOX,
        sort_by: SortField = SortField.DATE,
        sort_order: SortOrder = SortOrder.DESC,
        already_seen_message_ids: list[int] | None = None,
    ):
        self._box_type = box_type
        self._sort_by = sort_by
        self._sort_order = sort_order
        self._already_seen_message_ids = already_seen_message_ids or []

    @property
    def _subsystem(self) -> str:
        return "postboxes"

    @property
    def _action(self) -> str:
        return "message list"

    @property
    def _params(self) -> dict:
        return {
            "boxType": self._box_type.value,
            "boxID": "0",
            "sortField": self._sort_by.value,
            "sortKey": self._sort_order.value,
            "poll": "false" if not self._already_seen_message_ids else "true",
            "poll_ids": ",".join(str(x) for x in self._already_seen_message_ids),
            "layout": "new",
        }

    @property
    def _xpath(self) -> str:
        return ".//messages/message"

    @property
    def _object_to_instantiate(self) -> type[Message]:
        return Message
