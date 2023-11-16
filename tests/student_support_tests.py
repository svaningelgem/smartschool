from smartschool import StudentSupportLinks


def test_support_links_happy_flow():
    sut = list(StudentSupportLinks())

    assert len(sut) == 2

    assert sut[0].name == "1712"
    assert sut[1].name == "Autisme chat"
