from smartschool.planner import PlannedElements


def test_periods_happy_flow():
    sut = list(PlannedElements())

    assert len(sut) == 2

    assert sut[0].courses[0].name == "Frans"
    assert sut[0].plannedElementType == "planned-assignments"
    assert not sut[0].unconfirmed
