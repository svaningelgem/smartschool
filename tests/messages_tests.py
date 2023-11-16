from smartschool import Attachments, Message, MessageHeaders


def test_messages_happy_flow():
    sut = list(MessageHeaders())

    assert len(sut) == 2
    assert sut[0].subject == "Re: LO les"
    assert sut[1].subject == "Frans"


def test_fetch_one_message_happy_flow():
    sut = list(Message(123))

    assert len(sut) == 1
    assert sut[0].subject == "Griezelfestijn"
    assert sut[0].attachment == 2


def test_fetch_attachments_happy_flow():
    sut = list(Attachments(123))

    assert len(sut) == 2
    assert sut[0].name == "Oproep figuranten en helpers.pdf"
    assert sut[1].name == "Poster griezelfestijn.pdf"

    assert sut[0].download().startswith(b"%PDF-1.6\r")
