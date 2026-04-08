from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from smartschool import MessageComposerForm, RecipientType, objects
from smartschool.exceptions import SmartSchoolAttachmentUploadError

if TYPE_CHECKING:
    from pathlib import Path

    from requests_mock import Mocker

    from smartschool import Smartschool


COMPOSE_URL = "https://site/?module=Messages&file=composeMessage&boxType=inbox&composeType=0&msgID=undefined"
SEARCH_USERS_URL = "https://site/?module=Messages&file=searchUsers"
ADD_RECIPIENT_URL = "https://site/?module=Messages&file=searchUsers&function=addUserToSelected"
UPLOAD_URL = "https://site/Upload/Upload/Index"


COMPOSE_FORM_HTML = """
<html><body>
  <form>
    <input type="hidden" name="encryptedSender" value="enc123">
    <input type="hidden" name="randomDir" value="dir123">
    <input type="hidden" name="uniqueUsc" value="usc123">
    <input type="hidden" name="origMsgID" value="0">
    <input type="text" name="visible" value="ignored">
    <input type="hidden" value="nameless">
    <select name="category"><option>ignored</option></select>
    <textarea name="body">ignored</textarea>
  </form>
</body></html>
"""


def _make_form(session: Smartschool, requests_mock: Mocker) -> MessageComposerForm:
    requests_mock.get(COMPOSE_URL, text=COMPOSE_FORM_HTML)
    return MessageComposerForm.create(session=session)


def test_create_parses_hidden_fields_and_seeds_payload(session: Smartschool, requests_mock: Mocker) -> None:
    form = _make_form(session, requests_mock)

    assert form.hidden_fields["encryptedSender"] == "enc123"
    assert form.hidden_fields["randomDir"] == "dir123"
    assert form.hidden_fields["uniqueUsc"] == "usc123"
    assert form.hidden_fields["origMsgID"] == "0"
    # Non-hidden and nameless inputs are skipped
    assert "visible" not in form.hidden_fields
    assert "" not in form.hidden_fields

    # The initial payload mirrors hidden values and baseline constants
    assert form.payload["encryptedSender"] == "enc123"
    assert form.payload["randomDir"] == "dir123"
    assert form.payload["uniqueUsc"] == "usc123"
    assert form.payload["module"] == "Messages"
    assert form.payload["send"] == "send"
    assert form.payload["copyToLVS"] == "dontCopyToLVS"


def test_set_field_helpers_populate_payload(session: Smartschool, requests_mock: Mocker) -> None:
    form = _make_form(session, requests_mock)

    form.set_subject("Hello")
    form.set_message_html("<p>Body</p>")
    form.set_field("sendDate", "2026-04-10")

    assert form.payload["subject"] == "Hello"
    assert form.payload["message"] == "<p>Body</p>"
    assert form.payload["sendDate"] == "2026-04-10"


def test_search_users_returns_users_and_groups(session: Smartschool, requests_mock: Mocker) -> None:
    form = _make_form(session, requests_mock)
    requests_mock.post(
        SEARCH_USERS_URL,
        text="""
        <results>
          <groups>
            <group>
              <groupID>298</groupID>
              <value>1A</value>
              <icon>smsc/img/briefcase.png</icon>
              <ssID>4069</ssID>
              <description>1ste leerjaar A</description>
            </group>
          </groups>
          <users>
            <user>
              <userID>146</userID>
              <value>John Doe</value>
              <ssID>4069</ssID>
              <coaccountname></coaccountname>
              <classname></classname>
              <schoolname>Test School</schoolname>
              <picture>https://site/pic.png</picture>
            </user>
          </users>
        </results>
        """,
    )

    users, groups = form.search_users("John")

    assert len(users) == 1
    assert users[0].user_id == 146
    assert users[0].value == "John Doe"
    assert users[0].ss_id == 4069
    assert users[0].schoolname == "Test School"

    assert len(groups) == 1
    assert groups[0].group_id == 298
    assert groups[0].value == "1A"
    assert groups[0].description == "1ste leerjaar A"


def test_search_users_handles_empty_result(session: Smartschool, requests_mock: Mocker) -> None:
    form = _make_form(session, requests_mock)
    requests_mock.post(SEARCH_USERS_URL, text="<results></results>")

    users, groups = form.search_users("nobody")

    assert users == []
    assert groups == []


def test_search_users_without_unique_usc_raises(session: Smartschool) -> None:
    form = MessageComposerForm(session=session)

    with pytest.raises(ValueError, match="uniqueUsc is missing"):
        form.search_users("anyone")


def _build_user() -> objects.MessageSearchUser:
    return objects.MessageSearchUser(
        user_id=146,
        value="John Doe",
        ss_id=4069,
        schoolname="Test School",
    )


def _build_group() -> objects.MessageSearchGroup:
    return objects.MessageSearchGroup(group_id=298, value="1A", ss_id=4069)


@pytest.mark.parametrize(
    ("recipient_type", "expected_type", "expected_parent"),
    [
        (RecipientType.TO, "0", "insertSearchFieldContainer_0_0"),
        (RecipientType.CC, "2", "insertSearchFieldContainer_2_0"),
        (RecipientType.BCC, "3", "insertSearchFieldContainer_3_0"),
    ],
)
def test_add_recipient_user_posts_expected_payload(
    session: Smartschool,
    requests_mock: Mocker,
    recipient_type: RecipientType,
    expected_type: str,
    expected_parent: str,
) -> None:
    form = _make_form(session, requests_mock)
    requests_mock.post(ADD_RECIPIENT_URL, text="<users/>")

    form.add_recipient(_build_user(), recipient_type)

    last = requests_mock.request_history[-1]
    assert "function=addUserToSelected" in last.url
    body = last.text or ""
    assert "id=146" in body
    assert "typeId=users" in body
    assert f"type={expected_type}" in body
    assert f"parentNodeId={expected_parent}" in body
    assert "ssid=4069" in body
    assert "uniqueUsc=usc123" in body


def test_add_recipient_group_uses_groups_type(session: Smartschool, requests_mock: Mocker) -> None:
    form = _make_form(session, requests_mock)
    requests_mock.post(ADD_RECIPIENT_URL, text="<groups/>")

    form.add_recipient(_build_group(), RecipientType.CC)

    body = requests_mock.request_history[-1].text or ""
    assert "id=298" in body
    assert "typeId=groups" in body
    assert "type=2" in body


def test_add_recipient_without_unique_usc_raises(session: Smartschool) -> None:
    form = MessageComposerForm(session=session)

    with pytest.raises(ValueError, match="uniqueUsc is missing"):
        form.add_recipient(_build_user())


def test_add_attachment_happy_path(session: Smartschool, requests_mock: Mocker, tmp_path: Path) -> None:
    form = _make_form(session, requests_mock)
    requests_mock.post(UPLOAD_URL, text="true")

    file_path = tmp_path / "note.txt"
    file_path.write_text("hello", encoding="utf-8")

    form.add_attachment(file_path)

    last = requests_mock.request_history[-1]
    assert last.url == UPLOAD_URL
    assert last.method == "POST"
    body = last.text or ""
    assert "note.txt" in body
    assert "dir123" in body


def test_add_attachment_raises_on_false_response(session: Smartschool, requests_mock: Mocker, tmp_path: Path) -> None:
    form = _make_form(session, requests_mock)
    requests_mock.post(UPLOAD_URL, text="false")

    file_path = tmp_path / "note.txt"
    file_path.write_text("hello", encoding="utf-8")

    with pytest.raises(SmartSchoolAttachmentUploadError, match="server returned false"):
        form.add_attachment(file_path)


def test_add_attachment_raises_on_unexpected_response(session: Smartschool, requests_mock: Mocker, tmp_path: Path) -> None:
    form = _make_form(session, requests_mock)
    requests_mock.post(UPLOAD_URL, text="maybe?")

    file_path = tmp_path / "note.txt"
    file_path.write_text("hello", encoding="utf-8")

    with pytest.raises(SmartSchoolAttachmentUploadError, match="unexpected response"):
        form.add_attachment(file_path)


def test_add_attachment_without_random_dir_raises(session: Smartschool, tmp_path: Path) -> None:
    form = MessageComposerForm(session=session)
    file_path = tmp_path / "note.txt"
    file_path.write_text("hello", encoding="utf-8")

    with pytest.raises(ValueError, match="randomDir is missing"):
        form.add_attachment(file_path)


def test_add_attachment_missing_file_raises(session: Smartschool, requests_mock: Mocker, tmp_path: Path) -> None:
    form = _make_form(session, requests_mock)

    with pytest.raises(FileNotFoundError):
        form.add_attachment(tmp_path / "does_not_exist.txt")


def test_send_posts_payload_as_multipart(session: Smartschool, requests_mock: Mocker) -> None:
    form = _make_form(session, requests_mock)
    form.set_subject("Hello")
    form.set_message_html("<p>Body</p>")

    requests_mock.post(COMPOSE_URL, text="")

    response = form.send()

    assert response.status_code == 200
    last = requests_mock.request_history[-1]
    assert last.method == "POST"
    body = last.text or ""
    assert "Hello" in body
    assert "<p>Body</p>" in body
