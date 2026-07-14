from pathlib import Path

from pytest_mock import MockerFixture
from requests_mock import Mocker

from smartschool import (
    AdjustMessageLabel,
    Attachments,
    MarkMessageUnread,
    Message,
    MessageHeaders,
    MessageLabel,
    MessageMoveToArchive,
    MessageMoveToTrash,
    Smartschool,
)

_DISPATCHER_URL = "https://site/?module=Messages&file=dispatcher"


def test_messages_happy_flow(session: Smartschool):
    sut = list(MessageHeaders(session))

    assert len(sut) == 2
    assert sut[0].subject == "Re: LO les"
    assert sut[1].subject == "Frans"


def test_fetch_one_message_happy_flow(session: Smartschool):
    sut = Message(session, 123).get()

    assert sut.subject == "Griezelfestijn"
    assert sut.attachment == 2


def test_fetch_attachments_happy_flow(session: Smartschool):
    sut = list(Attachments(session, 123))

    assert len(sut) == 2
    assert sut[0].name == "Oproep figuranten en helpers.pdf"
    assert sut[1].name == "Poster griezelfestijn.pdf"

    assert sut[0].download().startswith(b"%PDF-1.6\r")


def test_message_unread_happy_flow(session: Smartschool):
    sut = MarkMessageUnread(session, msg_id=123).get()

    assert sut.id == 123
    assert sut.new == 0


def test_adjust_message_label_happy_flow(session: Smartschool):
    sut = AdjustMessageLabel(session, msg_id=123, label=MessageLabel.GREEN_FLAG).get()

    assert sut.id == 123
    assert sut.new == MessageLabel.GREEN_FLAG.value


def test_archive_message_happy_flow(session: Smartschool):
    sut = MessageMoveToArchive(session, msg_id=123).get()

    assert sut.id == 123
    assert sut.new == 1


def test_multi_archive_message_happy_flow(session: Smartschool):
    sut = list(MessageMoveToArchive(session, msg_id=[123, 456]))

    assert len(sut) == 2

    assert sut[0].id == 123
    assert sut[0].new == 1

    assert sut[1].id == 456
    assert sut[1].new == 0


def test_trash_message_happy_flow(session: Smartschool):
    sut = MessageMoveToTrash(session, msg_id=123).get()

    assert sut.msg_id == 123
    assert sut.box_type == "inbox"
    assert sut.is_deleted


def test_empty_inbox_returns_empty_iterator(session: Smartschool, requests_mock: Mocker):
    """Issue #165: an empty inbox returns an empty 200 body; iterate to nothing instead of raising ParseError."""
    requests_mock.post(_DISPATCHER_URL, text="")

    assert list(MessageHeaders(session)) == []


def test_messages_force_authentication_before_posting(session: Smartschool, mocker: MockerFixture):
    """Issue #165: an unauthenticated session gets an empty 200 (no redirect), so the interface forces the lazy login before POSTing."""
    auth = mocker.patch.object(type(session), "authenticated_user", new_callable=mocker.PropertyMock, return_value={"id": "x"})

    sut = list(MessageHeaders(session))

    auth.assert_called()  # login was forced before the POST
    assert len(sut) == 2  # and the messages still parse afterwards


def test_message_with_empty_body_coerced_to_empty_string(session: Smartschool, requests_mock: Mocker):
    """Issue #165: a message with a subject but no body has body=None in the XML; coerce it to ''."""
    fixture = Path(__file__).parent / "requests/post/postboxes/show message.xml"
    empty_body_xml = fixture.read_text(encoding="utf8").replace("<body>&lt;p&gt;Beste&lt;/p&gt;</body>", "<body/>")
    requests_mock.post(_DISPATCHER_URL, text=empty_body_xml)

    sut = Message(session, 123).get()

    assert sut.body == ""
