from __future__ import annotations

import mimetypes
from dataclasses import dataclass, field
from enum import Enum
from html.parser import HTMLParser
from pathlib import Path
from typing import TYPE_CHECKING
from xml.etree import ElementTree as ET

from requests import Session as RequestsSession

from . import objects
from .messages import BoxType
from .session import SessionMixin

if TYPE_CHECKING:
    from requests import Response

    from .session import Smartschool

__all__ = [
    "GetComposeForm",
    "MessageComposerForm",
    "RecipientType",
]


class RecipientType(Enum):
    """Recipient type for message composition (TO, CC, BCC)."""

    TO = "to"
    CC = "cc"
    BCC = "bcc"

    @property
    def request_type(self) -> str:
        return {
            RecipientType.TO: "0",
            RecipientType.CC: "2",
            RecipientType.BCC: "3",
        }[self]

    @property
    def parent_node_id(self) -> str:
        return f"insertSearchFieldContainer_{self.request_type}_0"


class _ComposeFormParser(HTMLParser):
    """Extract hidden input values from compose form HTML."""

    def __init__(self):
        super().__init__()
        self.fields: dict[str, str] = {}

    def handle_starttag(self, tag, attrs):
        if tag != "input":
            return

        attrs_dict = dict(attrs)
        if attrs_dict.get("type") != "hidden":
            return

        name = attrs_dict.get("name")
        value = attrs_dict.get("value", "")
        if name:
            self.fields[name] = value


@dataclass
class MessageComposerForm(SessionMixin):
    """
    Compose and send messages in Smartschool.

    To reproduce: Open the message compose dialog and observe network requests.

    Example:
    -------
    >>> form = MessageComposerForm.create(session=session)
    >>> form.set_subject("Hello")
    >>> form.set_message_html("<p>My message</p>")
    >>> users, groups = form.search_users("John")
    >>> form.add_recipient(users[0], RecipientType.TO)
    >>> form.add_attachment("README.md")
    >>> response = form.send()
    >>> print(response.status_code)
    200

    """

    box_type: BoxType = BoxType.INBOX
    compose_type: int = 0
    msg_id: str = "undefined"
    payload: dict[str, str] = field(default_factory=dict)
    hidden_fields: dict[str, str] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        session: Smartschool,
        box_type: BoxType = BoxType.INBOX,
        compose_type: int = 0,
        msg_id: str = "undefined",
    ) -> MessageComposerForm:
        form = cls(session=session, box_type=box_type, compose_type=compose_type, msg_id=msg_id)
        form.refresh()
        return form

    @property
    def _url(self) -> str:
        return f"/?module=Messages&file=composeMessage&boxType={self.box_type.value}&composeType={self.compose_type}&msgID={self.msg_id}"

    def refresh(self) -> MessageComposerForm:
        resp = self.session.get(self._url)
        resp.raise_for_status()

        parser = _ComposeFormParser()
        parser.feed(resp.text)
        self.hidden_fields = parser.fields

        self.payload = {
            "module": "Messages",
            "file": "composeMessage",
            "boxType": self.box_type.value,
            "composeType": str(self.compose_type),
            "msgID": str(self.msg_id),
            "encryptedSender": self.hidden_fields.get("encryptedSender", ""),
            "send": "send",
            "origMsgID": self.hidden_fields.get("origMsgID", "0"),
            "composeAction": self.hidden_fields.get("composeAction", "0"),
            "randomDir": self.hidden_fields.get("randomDir", ""),
            "uniqueUsc": self.hidden_fields.get("uniqueUsc", ""),
            "showTab": self.hidden_fields.get("showTab", "tab1Container"),
            "delFile": self.hidden_fields.get("delFile", "0"),
            "msgFormSelectedTab": self.hidden_fields.get("msgFormSelectedTab", ""),
            "sendDate": self.hidden_fields.get("sendDate", ""),
            "searchField3": "",
            "searchField1": "",
            "searchField4": "",
            "searchField5": "",
            "subject": "",
            "copyToLVS": "dontCopyToLVS",
            "message": "",
            "bcc": "0",
        }

        return self

    def set_field(self, key: str, value: str | int) -> MessageComposerForm:
        self.payload[key] = str(value)
        return self

    def set_subject(self, subject: str) -> MessageComposerForm:
        return self.set_field("subject", subject)

    def set_message_html(self, message_html: str) -> MessageComposerForm:
        return self.set_field("message", message_html)

    def search_users(self, search_text: str) -> tuple[list[objects.MessageSearchUser], list[objects.MessageSearchGroup]]:
        unique_usc = self.payload.get("uniqueUsc", "")
        if not unique_usc:
            raise ValueError("uniqueUsc is missing. Call refresh() or create() before searching users.")

        response = self.session.post(
            "/?module=Messages&file=searchUsers",
            data={
                "val": search_text,
                "type": "0",
                "parentNodeId": "insertSearchFieldContainer_0_0",
                "xml": "<results></results>",
                "uniqueUsc": unique_usc,
            },
        )
        response.raise_for_status()

        root = ET.fromstring(response.text.strip())
        users: list[objects.MessageSearchUser] = []
        groups: list[objects.MessageSearchGroup] = []

        users_element = root.find("users")
        if users_element is not None:
            for user in users_element.findall("user"):
                users.append(
                    objects.MessageSearchUser(
                        userID=int(user.findtext("userID", default="0")),
                        value=user.findtext("value", default=""),
                        ssID=int(user.findtext("ssID", default="0")),
                        coaccountname=user.findtext("coaccountname") or None,
                        classname=user.findtext("classname") or None,
                        schoolname=user.findtext("schoolname") or None,
                        picture=user.findtext("picture") or None,
                    ),
                )

        groups_element = root.find("groups")
        if groups_element is not None:
            for group in groups_element.findall("group"):
                groups.append(
                    objects.MessageSearchGroup(
                        groupID=int(group.findtext("groupID", default="0")),
                        value=group.findtext("value", default=""),
                        icon=group.findtext("icon") or None,
                        ssID=int(group.findtext("ssID", default="0")),
                        description=group.findtext("description") or None,
                    ),
                )

        return users, groups

    def add_recipient(
        self,
        recipient: objects.MessageSearchUser | objects.MessageSearchGroup,
        recipient_type: RecipientType = RecipientType.TO,
        user_lt: int = 0,
    ) -> MessageComposerForm:
        unique_usc = self.payload.get("uniqueUsc", "")
        if not unique_usc:
            raise ValueError("uniqueUsc is missing. Call refresh() or create() before adding recipients.")

        if isinstance(recipient, objects.MessageSearchUser):
            recipient_id = recipient.user_id
            type_id = "users"
            ssid = recipient.ss_id
        else:
            recipient_id = recipient.group_id
            type_id = "groups"
            ssid = recipient.ss_id

        response = self.session.post(
            "/?module=Messages&file=searchUsers&function=addUserToSelected",
            data={
                "id": str(recipient_id),
                "typeId": type_id,
                "type": recipient_type.request_type,
                "parentNodeId": recipient_type.parent_node_id,
                "ssid": str(ssid),
                "userlt": str(user_lt),
                "uniqueUsc": unique_usc,
            },
        )
        response.raise_for_status()
        return self

    def add_attachment(self, file_path: str | Path) -> bool:
        upload_dir = self.payload.get("randomDir", "")
        if not upload_dir:
            raise ValueError("randomDir is missing. Call refresh() or create() before uploading attachments.")

        path = Path(file_path)
        if not path.exists() or not path.is_file():
            raise FileNotFoundError(f"Attachment file does not exist: {path}")

        mime_type, _ = mimetypes.guess_type(path.name)
        if mime_type is None:
            mime_type = "application/octet-stream"

        file_content = path.read_bytes()
        response = RequestsSession.request(
            self.session,
            "POST",
            self.session.create_url("/Upload/Upload/Index"),
            files={
                "file": (path.name, file_content, mime_type),
                "uploadDir": (None, upload_dir),
            },
        )

        response.raise_for_status()
        result = response.text.strip().lower()
        if result == "true":
            return True
        if result == "false":
            raise RuntimeError(f"Attachment upload failed for '{path.name}': server returned false.")

        raise RuntimeError(f"Attachment upload returned unexpected response for '{path.name}': {response.text!r}")

    def send(self) -> Response:
        files = {key: (None, value) for key, value in self.payload.items()}
        return self.session.post(self._url, files=files)


@dataclass
class GetComposeForm(SessionMixin):
    """
    Fetch and parse compose form hidden fields.

    To reproduce: Open message compose dialog and inspect HTML form fields.

    Example:
    -------
    >>> form_fields = GetComposeForm(session=session).get()
    >>> print(form_fields["randomDir"])
    xJMYmmPoHfRVKvi4KvaTxXHec...

    """

    box_type: BoxType = BoxType.INBOX
    compose_type: int = 0
    msg_id: int = 0

    def get(self) -> dict[str, str]:
        form = MessageComposerForm.create(
            session=self.session,
            box_type=self.box_type,
            compose_type=self.compose_type,
            msg_id=str(self.msg_id),
        )
        return form.hidden_fields
