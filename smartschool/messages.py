from __future__ import annotations

from abc import ABC, ABCMeta
from enum import Enum

from ._xml_interface import SmartschoolXML, SmartschoolXML_NoCache
from .objects import Attachment, FullMessage, ShortMessage

__all__ = ["SortField", "SortOrder", "BoxType", "MessageHeaders", "Message", "Attachments"]


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


class _MessagesPoster:
    _url = '/?module=Messages&file=dispatcher'


class MessageHeaders(_MessagesPoster, SmartschoolXML_NoCache):
    """
    Interfaces the mailbox principle in Smartschool.

    To reproduce: Open the messages and watch the XHR calls.

    Example:
    -------
    >>> for message in MessageHeaders():
    >>>     print(message.subject)
    Re: LO les
    Frans
    """

    def __init__(
        self,
        box_type: BoxType = BoxType.INBOX,
        sort_by: SortField = SortField.DATE,
        sort_order: SortOrder = SortOrder.DESC,
        already_seen_message_ids: list[int] | None = None,
    ):
        super().__init__()

        self.box_type = box_type
        self.sort_by = sort_by
        self.sort_order = sort_order
        self.already_seen_message_ids = already_seen_message_ids or []

    @property
    def _subsystem(self) -> str:
        return "postboxes"

    @property
    def _action(self) -> str:
        return "message list"

    @property
    def _params(self) -> dict:
        return {
            "boxType": self.box_type.value,
            "boxID": "0",
            "sortField": self.sort_by.value,
            "sortKey": self.sort_order.value,
            "poll": "false" if not self.already_seen_message_ids else "true",
            "poll_ids": ",".join(str(x) for x in self.already_seen_message_ids),
            "layout": "new",
        }

    @property
    def _xpath(self) -> str:
        return ".//messages/message"

    @property
    def _object_to_instantiate(self) -> type[ShortMessage]:
        return ShortMessage


class _FetchOneMessage(_MessagesPoster, SmartschoolXML, ABC):
    def __init__(self, msg_id: int, box_type: BoxType = BoxType.INBOX):
        super().__init__()

        self.msg_id = msg_id
        self.box_type = box_type

    @property
    def _subsystem(self) -> str:
        return "postboxes"

    @property
    def _params(self) -> dict:
        return {
            "msgID": self.msg_id,
            "boxType": self.box_type.value,
            "limitList": "true",
        }

    def _get_from_cache(self) -> object:
        return self.cache[(self.msg_id, self.box_type)]

    def _store_into_cache(self, obj: object) -> None:
        self.cache[(self.msg_id, self.box_type)] = obj


class Message(_FetchOneMessage):
    """
    Interface to fetch one message based on its MessageID.

    To reproduce: just go to a message and click it.

    Example:
    -------
    >>> message: FullMessage = list(Message(123))[0]
    >>> message.subject
    Griezelfestijn
    """

    @property
    def _action(self) -> str:
        return "show message"

    @property
    def _xpath(self) -> str:
        return ".//data/message"

    @property
    def _object_to_instantiate(self) -> type[FullMessage]:
        return FullMessage

    def _post_process_element(self, element: dict) -> None:
        for modify_this in ["receivers", "ccreceivers", "bccreceivers"]:
            if not element[modify_this]:
                element[modify_this] = []
                continue

            element[modify_this] = element[modify_this]["to"]

            if not isinstance(element[modify_this], list):
                element[modify_this] = [element[modify_this]]


class Attachments(_FetchOneMessage):
    """
    Interface to fetch one message based on its MessageID.

    To reproduce: just go to a message (with the attachment symbol) and click it.

    Example:
    -------
    >>> for attachment in Attachments(123):
    >>>     print(attachment.name)
    Oproep figuranten en helpers.pdf
    Poster griezelfestijn.pdf
    """

    @property
    def _action(self) -> str:
        return "attachment list"

    @property
    def _xpath(self) -> str:
        return ".//attachmentlist/attachment"

    @property
    def _object_to_instantiate(self) -> type[Attachment]:
        return Attachment
