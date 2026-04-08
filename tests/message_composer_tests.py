from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
import requests

from smartschool import objects
from smartschool.exceptions import SmartSchoolAttachmentUploadError
from smartschool.message_composer import MessageComposerForm, RecipientType

if TYPE_CHECKING:
    from pathlib import Path


class FakeResponse:
    def __init__(self, text: str = "", status_code: int = 200, url: str = "https://example.test"):
        self.text = text
        self.status_code = status_code
        self.url = url

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code} error for url: {self.url}")


class FakeSession:
    def __init__(self):
        self._get_queue: list[FakeResponse] = []
        self._post_queue: list[FakeResponse] = []
        self.calls: list[dict] = []

    def queue_get(self, response: FakeResponse) -> None:
        self._get_queue.append(response)

    def queue_post(self, response: FakeResponse) -> None:
        self._post_queue.append(response)

    def create_url(self, path: str) -> str:
        return f"https://example.test{path}"

    def get(self, url: str, **kwargs):
        self.calls.append({"method": "GET", "url": url, "kwargs": kwargs})
        if not self._get_queue:
            raise AssertionError("No queued GET response")
        return self._get_queue.pop(0)

    def post(self, url: str, **kwargs):
        self.calls.append({"method": "POST", "url": url, "kwargs": kwargs})
        if not self._post_queue:
            raise AssertionError("No queued POST response")
        return self._post_queue.pop(0)


def test_create_fetches_and_parses_hidden_fields():
    session = FakeSession()
    session.queue_get(
        FakeResponse(
            text="""
            <html><body>
              <input type="hidden" name="encryptedSender" value="enc123">
              <input type="hidden" name="randomDir" value="dir123">
              <input type="hidden" name="uniqueUsc" value="usc123">
              <input type="hidden" name="origMsgID" value="0">
            </body></html>
            """
        )
    )

    form = MessageComposerForm.create(session=session)

    assert form.payload["encryptedSender"] == "enc123"
    assert form.payload["randomDir"] == "dir123"
    assert form.payload["uniqueUsc"] == "usc123"
    assert form.hidden_fields["origMsgID"] == "0"


def test_search_users_returns_users_and_groups():
    session = FakeSession()
    form = MessageComposerForm(session=session)
    form.payload["uniqueUsc"] = "usc123"

    session.queue_post(
        FakeResponse(
            text="""
            <results>
              <groups>
                <group>
                  <groupID>298</groupID>
                  <value>1A</value>
                  <icon>smsc/img/briefcase/briefcase_16x16.png</icon>
                  <ssID>4069</ssID>
                  <description>1ste leerjaar A</description>
                </group>
              </groups>
              <users>
                <user>
                  <userID>146</userID>
                  <value>Yvan Vander Sanden</value>
                  <ssID>4069</ssID>
                  <coaccountname></coaccountname>
                  <classname></classname>
                  <schoolname>Instituut Sancta Maria Aarschot</schoolname>
                  <picture>https://example.test/pic.png</picture>
                </user>
              </users>
            </results>
            """
        )
    )

    users, groups = form.search_users("1A")

    assert len(users) == 1
    assert users[0].user_id == 146
    assert users[0].value == "Yvan Vander Sanden"
    assert users[0].ss_id == 4069

    assert len(groups) == 1
    assert groups[0].group_id == 298
    assert groups[0].value == "1A"
    assert groups[0].ss_id == 4069


def test_add_recipient_posts_expected_payload_for_user_bcc():
    session = FakeSession()
    form = MessageComposerForm(session=session)
    form.payload["uniqueUsc"] = "usc123"

    session.queue_post(FakeResponse(text="<users/>"))

    user = objects.MessageSearchUser(
        user_id=146,
        value="Yvan Vander Sanden",
        ss_id=4069,
        coaccountname="",
        classname="",
        schoolname="Instituut Sancta Maria Aarschot",
        picture="https://example.test/pic.png",
    )

    form.add_recipient(user, RecipientType.BCC)

    call = session.calls[-1]
    data = call["kwargs"]["data"]

    assert "function=addUserToSelected" in call["url"]
    assert str(data["id"]) == "146"
    assert data["typeId"] == "users"
    assert str(data["type"]) == "3"
    assert data["parentNodeId"] == "insertSearchFieldContainer_3_0"
    assert str(data["ssid"]) == "4069"
    assert str(data["userlt"]) == "0"
    assert data["uniqueUsc"] == "usc123"


def test_add_attachment_raises_on_false_response(monkeypatch, tmp_path: Path):
    from smartschool import message_composer as mc

    session = FakeSession()
    form = MessageComposerForm(session=session)
    form.payload["randomDir"] = "dir123"

    file_path = tmp_path / "README.md"
    file_path.write_text("hello", encoding="utf-8")

    def fake_request(_session, method, url, **kwargs):
        return FakeResponse(text="false", status_code=200, url=url)

    monkeypatch.setattr(mc.RequestsSession, "request", fake_request)

    with pytest.raises(SmartSchoolAttachmentUploadError, match="server returned false"):
        form.add_attachment(file_path)


def test_add_attachment_sends_file_and_uploaddir(monkeypatch, tmp_path: Path):
    from smartschool import message_composer as mc

    session = FakeSession()
    form = MessageComposerForm(session=session)
    form.payload["randomDir"] = "dir123"

    file_path = tmp_path / "note.txt"
    file_path.write_text("hello", encoding="utf-8")

    captured: dict = {}

    def fake_request(_session, method, url, **kwargs):
        captured["method"] = method
        captured["url"] = url
        captured["kwargs"] = kwargs
        return FakeResponse(text="true", status_code=200, url=url)

    monkeypatch.setattr(mc.RequestsSession, "request", fake_request)

    ok = form.add_attachment(file_path)

    assert ok is None
    assert captured["method"] == "POST"
    assert captured["url"].endswith("/Upload/Upload/Index")

    files = captured["kwargs"]["files"]
    assert files["uploadDir"] == (None, "dir123")
    assert files["file"][0] == "note.txt"
    assert isinstance(files["file"][1], bytes)
