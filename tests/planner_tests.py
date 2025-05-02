from smartschool.planner import PlannedElements


def test_periods_happy_flow():
    sut = list(PlannedElements())

    assert len(sut) == 25

    assert sut[0].courses[0].name == "Godsdienst"
    assert sut[0].plannedElementType == "planned-placeholders"
    assert not sut[0].unconfirmed
