from smartschool import Smartschool
from smartschool.planner import PlannedElements


def test_periods_happy_flow(session:Smartschool):
    sut = list(PlannedElements(session))

    assert len(sut) == 2

    assert sut[0].courses[0].name == "Duits"
    assert sut[0].plannedElementType == "planned-assignments"
    assert not sut[0].unconfirmed
