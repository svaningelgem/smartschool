from smartschool import AdjustMessageLabel, Attachments, MarkMessageUnread, Message, MessageHeaders, MessageLabel, MessageMoveToArchive, MessageMoveToTrash


def test_messages_happy_flow():
    sut = list(MessageHeaders())

    assert len(sut) == 2
    assert sut[0].subject == "Re: LO les"
    assert sut[1].subject == "Frans"


def test_fetch_one_message_happy_flow():
    sut = Message(123).get()

    assert sut.subject == "Griezelfestijn"
    assert sut.attachment == 2


def test_fetch_attachments_happy_flow():
    sut = list(Attachments(123))

    assert len(sut) == 2
    assert sut[0].name == "Oproep figuranten en helpers.pdf"
    assert sut[1].name == "Poster griezelfestijn.pdf"

    assert sut[0].download().startswith(b"%PDF-1.6\r")


def test_message_unread_happy_flow():
    sut = MarkMessageUnread(msg_id=123).get()

    assert sut.id == 123
    assert sut.new == 0


def test_adjust_message_label_happy_flow():
    sut = AdjustMessageLabel(msg_id=123, label=MessageLabel.GREEN_FLAG).get()

    assert sut.id == 123
    assert sut.new == MessageLabel.GREEN_FLAG.value


def test_archive_message_happy_flow():
    sut = MessageMoveToArchive(msg_id=123).get()

    assert sut.id == 123
    assert sut.new == 1


def test_multi_archive_message_happy_flow():
    sut = list(MessageMoveToArchive(msg_id=[123, 456]))

    assert len(sut) == 2

    assert sut[0].id == 123
    assert sut[0].new == 1

    assert sut[1].id == 456
    assert sut[1].new == 0


def test_trash_message_happy_flow():
    sut = MessageMoveToTrash(msg_id=123).get()

    assert sut.msgID == 123
    assert sut.boxType == "inbox"
    assert sut.is_deleted
