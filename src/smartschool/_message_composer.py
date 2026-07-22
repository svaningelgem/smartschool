from __future__ import annotations

import mimetypes
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING
from xml.etree import ElementTree as ET

from ._common import bs4_html
from ._exceptions import SmartSchoolAttachmentUploadError
from ._messages import BoxType
from ._objects import MessageSearchGroup, MessageSearchUser
from ._session import SessionMixin

if TYPE_CHECKING:
    from requests import Response

    from ._session import Smartschool

__all__ = [
    "MessageComposerForm",
    "RecipientType",
]


class RecipientType(Enum):
    """
    Recipient field of the compose form (To / Cc / Bcc).

    The value is the search-field container index Smartschool assigns to the field. Co-accounts
    (parents) live in a mirrored block of containers; the composer routes a recipient there
    automatically when it is a co-account (``user_lt`` > 0), so callers only pick To/Cc/Bcc.
    """

    TO = "0"
    CC = "2"
    BCC = "3"

    @property
    def parent_node_id(self) -> str:
        return f"insertSearchFieldContainer_{self.value}_0"


# The compose form mirrors each To/Cc/Bcc field into a second block for co-accounts (parents),
# with these container indices.
_COACCOUNT_FIELD = {RecipientType.TO: "1", RecipientType.CC: "4", RecipientType.BCC: "5"}


def _field_ids(recipient_type: RecipientType, *, coaccount: bool) -> tuple[str, str]:
    """Return the ``(type, parentNodeId)`` request fields for a recipient field."""
    if coaccount:
        container = _COACCOUNT_FIELD[recipient_type]
        return container, f"insertSearchFieldContainer_{container}_0"
    return recipient_type.value, recipient_type.parent_node_id


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
    >>> form.add_all_coaccounts(users[0])  # also message that student's co-accounts (parents)
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

    def refresh(self) -> None:
        resp = self.session.get(self._url)
        resp.raise_for_status()

        soup = bs4_html(resp)
        self.hidden_fields = {inp["name"]: inp.get("value", "") for inp in soup.select("input[type=hidden][name]")}

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

    def set_field(self, key: str, value: str | int) -> None:
        self.payload[key] = str(value)

    def set_subject(self, subject: str) -> None:
        self.set_field("subject", subject)

    def set_message_html(self, message_html: str) -> None:
        self.set_field("message", message_html)

    def search_users(
        self,
        search_text: str,
        *,
        coaccount: bool = False,
    ) -> tuple[list[MessageSearchUser], list[MessageSearchGroup]]:
        """
        Search recipients.

        With ``coaccount=True`` the search returns co-accounts (parents) instead of accounts:
        each comes back as a user sharing the account's ``user_id``/``ss_id`` with ``user_lt``
        >= 1. Add them with :meth:`add_recipient` as usual - they are routed to the co-account
        field automatically.
        """
        unique_usc = self.payload.get("uniqueUsc", "")
        if not unique_usc:
            raise ValueError("uniqueUsc is missing. Call refresh() or create() before searching users.")

        # The search field only selects accounts (container 0) vs co-accounts (container 1) --
        # the To/Cc/Bcc choice doesn't change which people match (anyone can be To/Cc/Bcc), and
        # a picked result is placed by add_recipient() using its own ids, not this field. So we
        # always search the To slot; only the coaccount flag matters here.
        search_type, parent_node_id = _field_ids(RecipientType.TO, coaccount=coaccount)
        response = self.session.post(
            "/?module=Messages&file=searchUsers",
            data={
                "val": search_text,
                "type": search_type,
                "parentNodeId": parent_node_id,
                "xml": "<results></results>",
                "uniqueUsc": unique_usc,
            },
        )
        response.raise_for_status()

        root = ET.fromstring(response.text.strip())
        users: list[MessageSearchUser] = []
        groups: list[MessageSearchGroup] = []

        users_element = root.find("users")
        if users_element is not None:
            for user in users_element.findall("user"):
                users.append(
                    MessageSearchUser(
                        userID=int(user.findtext("userID", default="0")),
                        value=user.findtext("value", default=""),
                        ssID=int(user.findtext("ssID", default="0")),
                        userLT=int(user.findtext("userLT", default="0")),
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
                    MessageSearchGroup(
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
        recipient: MessageSearchUser | MessageSearchGroup,
        recipient_type: RecipientType = RecipientType.TO,
        user_lt: int | None = None,
    ) -> None:
        """
        Add a recipient to the given field (To/Cc/Bcc).

        ``user_lt`` defaults to the recipient's own ``user_lt`` (0 for a main account or a
        group, 1+ for a co-account), so a co-account returned by :meth:`search_users` is added
        correctly without passing it explicitly. Pass it to override. A co-account (resolved
        ``user_lt`` > 0) is routed to the co-account block of the chosen field automatically.
        """
        unique_usc = self.payload.get("uniqueUsc", "")
        if not unique_usc:
            raise ValueError("uniqueUsc is missing. Call refresh() or create() before adding recipients.")

        ssid = recipient.ss_id
        if isinstance(recipient, MessageSearchUser):
            recipient_id = recipient.user_id
            type_id = "users"
        else:
            recipient_id = recipient.group_id
            type_id = "groups"

        if user_lt is None:
            user_lt = getattr(recipient, "user_lt", 0)

        add_type, parent_node_id = _field_ids(recipient_type, coaccount=user_lt > 0)
        response = self.session.post(
            "/?module=Messages&file=searchUsers&function=addUserToSelected",
            data={
                "id": str(recipient_id),
                "typeId": type_id,
                "type": add_type,
                "parentNodeId": parent_node_id,
                "ssid": str(ssid),
                "userlt": str(user_lt),
                "uniqueUsc": unique_usc,
            },
        )
        response.raise_for_status()

    def add_all_coaccounts(
        self,
        user: MessageSearchUser,
        recipient_type: RecipientType = RecipientType.TO,
    ) -> list[MessageSearchUser]:
        """
        Add every co-account (typically the parents) of ``user`` as recipients.

        Searches the co-accounts for ``user`` and adds each one belonging to them, returning the
        co-accounts added (empty if the account has none). ``recipient_type`` picks the field
        (To/Cc/Bcc); the co-account routing is handled automatically.
        """
        found, _ = self.search_users(user.value, coaccount=True)
        coaccounts = [c for c in found if c.user_id == user.user_id and c.ss_id == user.ss_id and c.user_lt > 0]
        for coaccount in coaccounts:
            self.add_recipient(coaccount, recipient_type)
        return coaccounts

    def add_attachment(self, file_path: str | Path) -> None:
        upload_dir = self.payload.get("randomDir", "")
        if not upload_dir:
            raise ValueError("randomDir is missing. Call refresh() or create() before uploading attachments.")

        path = Path(file_path)
        if not path.is_file():
            raise FileNotFoundError(f"Attachment file does not exist: {path}")

        mime_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"

        file_content = path.read_bytes()
        response = self.session.post(
            "/Upload/Upload/Index",
            files={
                "file": (path.name, file_content, mime_type),
                "uploadDir": (None, upload_dir),
            },
        )

        response.raise_for_status()
        result = response.text.strip().lower()
        if result == "true":
            return
        if result == "false":
            raise SmartSchoolAttachmentUploadError(f"Attachment upload failed for '{path.name}': server returned false.")

        raise SmartSchoolAttachmentUploadError(f"Attachment upload returned unexpected response for '{path.name}': {response.text!r}")

    def send(self) -> Response:
        files = {key: (None, value) for key, value in self.payload.items()}
        return self.session.post(self._url, files=files)
