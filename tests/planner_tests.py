from datetime import date

import pytest
import time_machine

from smartschool import ApplicableAssignmentTypes, PlannedElements, Smartschool


@time_machine.travel("2025-05-06")
def test_periods_happy_flow(session: Smartschool):
    sut = list(PlannedElements(session))

    assert len(sut) == 25

    assert sut[0].courses[0].name == "Godsdienst"
    assert sut[0].plannedElementType == "planned-placeholders"
    assert not sut[0].unconfirmed


@time_machine.travel("2025-05-06")
def test_planned_elements_till_date(session: Smartschool):
    sut = list(PlannedElements(session, till_date=date(2025,5,7)))

    assert len(sut) == 1

    assert sut[0].courses[0].name == "Dummy"
    assert sut[0].plannedElementType == "planned-placeholders"
    assert sut[0].unconfirmed


def test_applicable_assignment_types(session: Smartschool):
    sut = list(ApplicableAssignmentTypes(session))

    assert len(sut) == 7

    obj = sut[0]
    assert obj.abbreviation == "-"
    assert obj.id == "12657aa0-3b29-4977-925b-e2a0f133f2ba"
    assert obj.isVisible is True
    assert obj.name == "-"
    assert obj.platformId == 49
    assert obj.weight == pytest.approx(1.0)
