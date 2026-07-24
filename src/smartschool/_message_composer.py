from __future__ import annotations

import mimetypes
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING
from xml.etree import ElementTree as ET

from logprise import logger

from ._common import bs4_html, parse_smsc_vars
from ._exceptions import SmartSchoolAttachmentUploadError, SmartSchoolCoAccountsUnavailableError
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
    def coaccount_container(self) -> str:
        """The container index of this field's mirrored co-account block."""
        return {RecipientType.TO: "1", RecipientType.CC: "4", RecipientType.BCC: "5"}[self]

    @property
    def parent_node_id(self) -> str:
        return _node_id(self.value)


def _node_id(container: str) -> str:
    """The DOM id of a search-field container."""
    return f"insertSearchFieldContainer_{container}_0"


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
    # Whether this account may message co-accounts (parents); set from the compose page by
    # refresh(). Co-account calls only work when this is True. See :meth:`add_all_coaccounts`.
    can_send_to_coaccounts: bool = False

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
        # The compose page always renders the co-account recipient block, so its presence is not
        # a capability signal. The real (staff/school-gated) flag lives in the embedded SMSC vars
        # config object.
        smsc_vars = parse_smsc_vars(resp.text)
        if not smsc_vars:
            logger.warning("No SMSC vars config found in the compose page; assuming co-accounts are unavailable.")
        self.can_send_to_coaccounts = bool(smsc_vars.get("canSendToCoAccounts"))

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

    def search_users(self, search_text: str) -> tuple[list[MessageSearchUser], list[MessageSearchGroup]]:
        """Search accounts (users and groups) by name. For a user's co-accounts use :meth:`get_coaccounts`."""
        return self._search_recipients(search_text, coaccount=False)

    def _search_recipients(
        self,
        search_text: str,
        *,
        coaccount: bool,
    ) -> tuple[list[MessageSearchUser], list[MessageSearchGroup]]:
        """
        POST a recipient search and parse the result.

        ``coaccount`` picks accounts (``False``) or co-accounts (``True``); a co-account search
        returns only co-accounts (``user_lt`` >= 1).
        """
        unique_usc = self.payload.get("uniqueUsc", "")
        if not unique_usc:
            raise ValueError("uniqueUsc is missing. Call refresh() or create() before searching users.")

        # Search only distinguishes accounts (container 0) from co-accounts (container 1). The
        # To/Cc/Bcc field is irrelevant to which people match (anyone can be To/Cc/Bcc), and a
        # picked result is placed later by add_recipient() using its own ids -- so there's no
        # field to thread through here, only the coaccount flag.
        search_type = "1" if coaccount else "0"
        parent_node_id = _node_id(search_type)
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

        if coaccount:  # a co-account search must yield co-accounts, never the main accounts
            users = [u for u in users if u.user_lt > 0]

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
            default_lt = recipient.user_lt
        else:
            recipient_id = recipient.group_id
            type_id = "groups"
            default_lt = 0  # groups have no co-accounts

        if user_lt is None:
            user_lt = default_lt

        if user_lt > 0:  # a co-account -> mirrored co-account container of the chosen field
            self._ensure_coaccounts_available()
            container = recipient_type.coaccount_container
        else:
            container = recipient_type.value
        parent_node_id = _node_id(container)

        response = self.session.post(
            "/?module=Messages&file=searchUsers&function=addUserToSelected",
            data={
                "id": str(recipient_id),
                "typeId": type_id,
                "type": container,
                "parentNodeId": parent_node_id,
                "ssid": str(ssid),
                "userlt": str(user_lt),
                "uniqueUsc": unique_usc,
            },
        )
        response.raise_for_status()

    def get_coaccounts(self, user: MessageSearchUser) -> list[MessageSearchUser]:
        """
        Return the co-accounts (typically the parents) of ``user``.

        Co-accounts are discovered through a name search, which can span namesakes, so this
        narrows the co-account search to the ones that actually belong to ``user`` (same
        ``user_id``/``ss_id``). Add them with :meth:`add_recipient` - they are routed to the
        co-account field automatically.

        Raises :class:`SmartSchoolCoAccountsUnavailableError` if this account cannot message
        co-accounts (check :attr:`can_send_to_coaccounts` to avoid it). Failing up front matters:
        a non-capable account's search comes back empty, so a later guard would never fire and
        the message would silently go out without the parents.
        """
        self._ensure_coaccounts_available()
        found, _ = self._search_recipients(user.value, coaccount=True)
        return [c for c in found if c.user_id == user.user_id and c.ss_id == user.ss_id]

    def _ensure_coaccounts_available(self) -> None:
        """Guard every co-account path: raise if this account cannot message co-accounts."""
        if not self.can_send_to_coaccounts:
            raise SmartSchoolCoAccountsUnavailableError

    def add_all_coaccounts(
        self,
        *users: MessageSearchUser,
        recipient_type: RecipientType = RecipientType.TO,
    ) -> list[MessageSearchUser]:
        """
        Add every co-account (typically the parents) of each user in ``users`` as recipients.

        Accepts one or more users (e.g. ``add_all_coaccounts(*students)``) and returns the
        co-accounts added across all of them (empty if none have any). ``recipient_type`` picks
        the field (To/Cc/Bcc); the co-account routing is handled automatically.
        """
        added: list[MessageSearchUser] = []
        for user in users:
            coaccounts = self.get_coaccounts(user)
            for coaccount in coaccounts:
                self.add_recipient(coaccount, recipient_type)
            added.extend(coaccounts)
        return added

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
