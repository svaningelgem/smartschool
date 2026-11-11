from datetime import date
from pathlib import Path

import pytest
import time_machine

from smartschool import ApplicableAssignmentTypes, PlannedElements, Smartschool


@time_machine.travel("2025-05-06")
def test_periods_happy_flow(session: Smartschool):
    sut = list(PlannedElements(session))

    assert len(sut) == 25

    assert sut[0].courses[0].name == "Godsdienst"
    assert sut[0].planned_element_type == "planned-placeholders"
    assert not sut[0].unconfirmed


@time_machine.travel("2025-05-06")
def test_planned_elements_till_date(session: Smartschool):
    sut = list(PlannedElements(session, till_date=date(2025, 5, 7)))

    assert len(sut) == 1

    assert sut[0].courses[0].name == "Dummy"
    assert sut[0].planned_element_type == "planned-placeholders"
    assert sut[0].unconfirmed


@time_machine.travel("2025-05-06")
def test_planned_elements_asks_for_the_requested_element_types(session: Smartschool, requests_mock):
    placeholders = Path(__file__).parent / "requests/get/planner/api/v1/planned-elements/user/49_10880_2/7966cae8d297.json"
    requests_mock.get("https://site/planner/api/v1/planned-elements/user/49_10880_2", text=placeholders.read_text(encoding="utf8"))

    sut = list(PlannedElements(session, element_types=("planned-lessons", "planned-placeholders")))

    assert requests_mock.last_request.qs["types"] == ["planned-lessons,planned-placeholders"]
    assert [element.planned_element_type for element in sut] == ["planned-placeholders"]


def test_applicable_assignment_types(session: Smartschool):
    sut = list(ApplicableAssignmentTypes(session))

    assert len(sut) == 7

    obj = sut[0]
    assert obj.abbreviation == "-"
    assert obj.id == "12657aa0-3b29-4977-925b-e2a0f133f2ba"
    assert obj.is_visible is True
    assert obj.name == "-"
    assert obj.platform_id == 49
    assert obj.weight == pytest.approx(1.0)
