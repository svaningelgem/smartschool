# Auto-generated stub file
from __future__ import annotations

from abc import ABC
from collections.abc import Iterator
from enum import Enum

from . import _objects as objects
from ._session import SessionMixin, Smartschool
from ._xml_interface import SmartschoolXML, SmartschoolXmlNoCache

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

class MessageLabel(Enum):
    NO_FLAG = 0
    GREEN_FLAG = 1
    YELLOW_FLAG = 2
    RED_FLAG = 3
    BLUE_FLAG = 4

class _MessagesPoster: ...

class MessageHeaders(_MessagesPoster, SmartschoolXmlNoCache):
    session: Smartschool
    cache: dict
    box_type: BoxType
    sort_by: SortField
    sort_order: SortOrder
    already_seen_message_ids: list[int] | None
    def __init__(
        self,
        session: Smartschool,
        cache: dict = ...,
        box_type: BoxType = BoxType.INBOX,
        sort_by: SortField = SortField.DATE,
        sort_order: SortOrder = SortOrder.DESC,
        already_seen_message_ids: list[int] | None = ...,
    ): ...

class _FetchOneMessage(_MessagesPoster, SmartschoolXML, ABC):
    session: Smartschool
    cache: dict
    def __init__(self, session: Smartschool, msg_id: int, box_type: BoxType = BoxType.INBOX): ...

class Message(_FetchOneMessage):
    session: Smartschool
    cache: dict
    def __init__(self, session: Smartschool, msg_id: int, box_type: BoxType = BoxType.INBOX): ...

class Attachment(SessionMixin, objects.Attachment):
    file_id: int
    name: str
    mime: str
    size: str
    icon: str
    wopi_allowed: bool
    order: int
    session: Smartschool
    def __init__(self, file_id: int, name: str, mime: str, size: str, icon: str, wopi_allowed: bool, order: int, session: Smartschool): ...
    def download(self) -> bytes: ...

class Attachments(_FetchOneMessage):
    session: Smartschool
    cache: dict
    def __init__(self, session: Smartschool, msg_id: int, box_type: BoxType = BoxType.INBOX): ...

class MarkMessageUnread(_FetchOneMessage):
    session: Smartschool
    cache: dict
    def __init__(self, session: Smartschool, msg_id: int, box_type: BoxType = BoxType.INBOX): ...

class AdjustMessageLabel(_FetchOneMessage):
    session: Smartschool
    cache: dict
    def __init__(self, session: Smartschool, msg_id: int, box_type: BoxType = BoxType.INBOX, label: MessageLabel = MessageLabel.NO_FLAG): ...

class MessageMoveToArchive(SessionMixin):
    session: Smartschool
    def __init__(self, session: Smartschool, msg_id: int | list[int]): ...
    def get(self) -> objects.MessageChanged: ...
    def __iter__(self) -> Iterator[objects.MessageChanged]: ...

class MessageMoveToTrash(_MessagesPoster, SmartschoolXmlNoCache):
    session: Smartschool
    cache: dict
    def __init__(self, session: Smartschool, msg_id: int): ...
