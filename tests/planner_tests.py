from smartschool import Smartschool
from smartschool.planner import PlannedElements
import time_machine


@time_machine.travel("2025-05-06")
def test_periods_happy_flow(session:Smartschool):
    sut = list(PlannedElements(session))

    assert len(sut) == 25

    assert sut[0].courses[0].name == "Godsdienst"
    assert sut[0].plannedElementType == "planned-placeholders"
    assert not sut[0].unconfirmed
