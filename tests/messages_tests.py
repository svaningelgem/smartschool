from smartschool import Messages


def test_messages_happy_flow():
    sut = list(Messages())

    assert len(sut) == 2
    assert sut[0].subject == "Re: LO les"
    assert sut[1].subject == "Frans"
