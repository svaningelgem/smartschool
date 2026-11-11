import json
from datetime import date
from pathlib import Path

import pytest
import time_machine

from smartschool import ApplicableAssignmentTypes, PlannedElement, PlannedElementDetails, PlannedElements, Smartschool


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


PDF = b"%PDF-1.4 dummy\n"
LESSON = Path(__file__).parent / "requests/get/planner/api/v1/planned-lessons/49/5f0c2a1e-7b3d-4c8e-9a61-2d4e8f1b3c70.json"


def _lesson() -> PlannedElement:
    return PlannedElement(**json.loads(LESSON.read_text(encoding="utf8")))


def test_planned_element_details(session: Smartschool):
    sut = PlannedElementDetails(session, element=_lesson()).get()

    assert sut.planned_element_type == "planned-lessons"
    assert sut.courses[0].name == "Dummy"
    assert sut.public_info == "<p>Lees hoofdstuk 3 voor de volgende les.</p>"
    assert not sut.capabilities.can_user_restore_from_trash

    assert len(sut.attachments) == 1
    assert sut.attachments[0].file_name == "hoofdstuk3.pdf"
    assert sut.attachments[0].file_size == 123456
    assert sut.attachments[0].mime_type == "application/pdf"

    assert len(sut.weblinks) == 1
    assert sut.weblinks[0].name == "Oefeningen"
    assert sut.weblinks[0].url == "https://example.com/oefeningen"

    assert len(sut.goals) == 1
    assert sut.goals[0].leerplan_id == "6a2c4e8f-0b1d-4f3a-9c5e-7d9b1f3a5c7e"


def test_planned_element_details_fetches_once(session: Smartschool, requests_mock):
    details = PlannedElementDetails(session, element=_lesson())

    details.get()
    details.files()

    assert requests_mock.call_count == 1


def test_planned_element_files_download(session: Smartschool, tmp_path: Path):
    sut = PlannedElementDetails(session, element=_lesson()).files()

    assert [file.filename for file in sut] == ["hoofdstuk3.pdf"]
    assert sut[0].download() == PDF
    assert sut[0].download_to_dir(tmp_path).read_bytes() == PDF


def test_planned_element_details_of_a_recurring_meeting(session: Smartschool, requests_mock):
    """An occurrence of a recurring meeting is fetched through its original element and date."""
    data = json.loads(LESSON.read_text(encoding="utf8"))
    data["plannedElementType"] = "planned-meetings"
    data["recurrence"] = {
        "originalPlannedElementId": "9d4f2b6a-8c1e-4a3f-b5d7-2e6c8a0f4b19",
        "originalRecurrenceDate": "2026-11-12T10:00:00+01:00",
    }
    url = "https://site/planner/api/v1/planned-meetings/49/9d4f2b6a-8c1e-4a3f-b5d7-2e6c8a0f4b19_2026-11-12T10:00:00+01:00"
    requests_mock.get(url, json=data)

    sut = PlannedElementDetails(session, element=PlannedElement(**data)).get()

    assert sut.planned_element_type == "planned-meetings"
    assert sut.recurrence is not None
    assert sut.recurrence.original_recurrence_date == "2026-11-12T10:00:00+01:00"
