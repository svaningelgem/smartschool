import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest
import time_machine

from smartschool import (
    ApplicableAssignmentTypes,
    PlannedElement,
    PlannedElementDetails,
    PlannedElementLocation,
    PlannedElementPlatformCalendar,
    PlannedElements,
    PlannedElementTextLocation,
    PlannedElementUnknownCalendar,
    PlannedElementUnknownLocation,
    PlannedElementUserCalendar,
    Smartschool,
    SmartSchoolDownloadError,
)


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


def test_planned_elements_asks_for_the_requested_element_types(session: Smartschool, requests_mock):
    requests_mock.get("https://site/planner/api/v1/planned-elements/user/49_10880_2", json=[])

    assert not list(PlannedElements(session, element_types=("planned-lessons", "planned-placeholders")))
    assert requests_mock.last_request.qs["types"] == ["planned-lessons,planned-placeholders"]


@pytest.mark.parametrize(
    ("element_types", "expected"),
    [
        ("planned-lessons", ("planned-lessons",)),
        (["planned-lessons", "planned-meetings"], ("planned-lessons", "planned-meetings")),
        (None, ()),
        ("", ()),
    ],
)
def test_planned_elements_takes_one_type_several_or_none(session: Smartschool, element_types, expected):
    assert PlannedElements(session, element_types=element_types).element_types == expected


@time_machine.travel("2026-11-11")
def test_planned_elements_without_element_types_fetches_everything(session: Smartschool, requests_mock):
    """Without a filter the planner returns every type, such as a lesson-free day, which has no organisers."""
    sut = list(PlannedElements(session, element_types=()))

    assert "types" not in requests_mock.last_request.qs
    assert [element.planned_element_type for element in sut] == ["planned-lesson-free-days"]
    assert sut[0].organisers.users == []


@time_machine.travel("2026-11-11")
def test_planned_elements_reads_a_location_entered_as_free_text(session: Smartschool):
    """A school activity can take place somewhere that is typed in instead of picked from the school's rooms."""
    sut = list(PlannedElements(session, element_types="planned-school-activities"))

    [location] = sut[0].locations
    assert isinstance(location, PlannedElementTextLocation)
    assert location.text == "Sports hall"


@time_machine.travel("2025-05-06")
def test_planned_elements_reads_a_room_as_before(session: Smartschool):
    location = next(location for element in PlannedElements(session, till_date=date(2025, 5, 7)) for location in element.locations)

    assert isinstance(location, PlannedElementLocation)
    assert location.title


def test_planned_elements_keeps_a_kind_of_location_it_does_not_know(session: Smartschool, requests_mock):
    """A new kind of location must not break the listing: it is kept by its type alone."""
    fixture = Path(__file__).parent / "requests/get/planner/api/v1/planned-elements/user/49_10880_2/7966cae8d297.json"
    element = json.loads(fixture.read_text(encoding="utf8"))[0]
    element["locations"] = [{"type": "brand-new-kind", "platformId": 49, "platformName": "Example school", "somethingElse": 1}]
    requests_mock.get("https://site/planner/api/v1/planned-elements/user/49_10880_2", json=[element])

    [location] = next(iter(PlannedElements(session))).locations

    assert isinstance(location, PlannedElementUnknownLocation)
    assert location.type == "brand-new-kind"


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


DETAILS = Path(__file__).parent / "requests/get/planner/api/v1"
LESSON = DETAILS / "planned-lessons/49/00000001-0000-0000-0000-000000000001.json"
ASSIGNMENT = DETAILS / "planned-assignments/49/00000002-0000-0000-0000-000000000001.json"
ASSIGNMENT_WITH_WEBLINK = DETAILS / "planned-assignments/49/00000003-0000-0000-0000-000000000001.json"
MEETING = DETAILS / "planned-meetings/49/00000004-0000-0000-0000-000000000001.json"
SCHOOL_ACTIVITY = DETAILS / "planned-school-activities/49/00000005-0000-0000-0000-000000000001.json"
ATTACHMENT = b"%PDF-1.4 dummy\n"


def _payload(fixture: Path) -> dict:
    return json.loads(fixture.read_text(encoding="utf8"))


def _element(fixture: Path) -> PlannedElement:
    return PlannedElement(**_payload(fixture))


def test_planned_element_details_of_a_lesson(session: Smartschool):
    sut = PlannedElementDetails(session, element=_element(LESSON)).get()

    assert sut.planned_element_type == "planned-lessons"
    assert sut.name == "Chapter 3"
    assert sut.courses[0].name == "Mathematics"
    assert not sut.capabilities.can_user_restore_from_trash

    [attachment] = sut.attachments
    assert attachment.file_name == "chapter 3.docx"
    assert attachment.file_size == 14560
    assert attachment.mime_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

    # What this lesson leaves empty or out
    assert sut.public_info == ""
    assert sut.info == ""
    assert sut.private_info == ""
    assert sut.weblinks == []
    assert sut.goals == []
    assert sut.reservations == []
    assert sut.date_created is None
    assert sut.visibility is None
    assert sut.repeat_options is None
    assert sut.calendars == []
    assert sut.extra_organisers.users == []
    assert sut.invite_statuses == []


def test_planned_element_details_of_an_assignment(session: Smartschool):
    sut = PlannedElementDetails(session, element=_element(ASSIGNMENT)).get()

    assert sut.public_info == "<p>See the title.</p>"
    assert sut.icon == "flags_red_yellow"
    assert sut.date_created == datetime(2026, 10, 26, 14, 28, 19, tzinfo=timezone(timedelta(hours=1)))
    assert sut.visibility is not None
    assert sut.visibility.after_date == datetime(2026, 10, 26, 14, 26, tzinfo=timezone(timedelta(hours=1)))
    assert sut.show_presence_choices
    assert not sut.presence_saved

    assert [goal.type for goal in sut.goals] == ["llinkid", "llinkid"]
    assert sut.goals[0].leerplan_id == "00000002-0000-0000-0000-000000000006"


def test_planned_element_details_reads_a_weblink(session: Smartschool):
    [weblink] = PlannedElementDetails(session, element=_element(ASSIGNMENT_WITH_WEBLINK)).get().weblinks

    assert weblink.name == "Exercises"
    assert weblink.url == "https://example.com/exercises"
    assert weblink.icon == "earth"


def test_planned_element_details_of_a_meeting(session: Smartschool):
    sut = PlannedElementDetails(session, element=_element(MEETING)).get()

    assert sut.info == "<p>Monday: tournament in the sports hall.</p>"
    assert sut.privacy == "standard"
    assert sut.repeat_options is None
    assert sut.extra_organisers.users[0].name.starting_with_first_name == "First Teacher"
    assert sut.extra_participants.users == []
    assert sut.invite_statuses == []

    assert [reservation.reservation_id for reservation in sut.reservations] == [1001, 1002]
    assert sut.reservations[0].item_id == 11

    [calendar] = sut.calendars
    assert isinstance(calendar, PlannedElementPlatformCalendar)
    assert calendar.platform_name == "Example school"
    assert calendar.info.name == "School calendar"
    assert calendar.info.color == "purple-500"


def test_planned_element_details_of_a_school_activity(session: Smartschool):
    sut = PlannedElementDetails(session, element=_element(SCHOOL_ACTIVITY)).get()

    assert sut.info == "<p>Bring a pencil.</p>"
    assert sut.public_info == sut.info
    assert len(sut.organisers.users) == 2
    [location] = sut.locations
    assert isinstance(location, PlannedElementTextLocation)


def test_planned_element_details_of_an_occurrence_go_through_the_original_element(session: Smartschool, requests_mock):
    """
    An occurrence of a recurring meeting is addressed by its original element and date, and so are its attachments.

    No capture of one exists: the recurrence, repeat options, user calendar, extra participant and invite status are
    keys added to the meeting fixture.
    """
    original = "00000004-0000-0000-0000-00000000000a"
    data = _payload(MEETING)
    user = data["organisers"]["users"][0]
    data["recurrence"] = {"originalPlannedElementId": original, "originalRecurrenceDate": "2026-11-12T10:00:00+01:00"}
    data["repeatOptions"] = {"frequency": "daily", "interval": 1, "monthWeek": 0, "until": "2026-11-30", "weekdays": []}
    data["calendars"] = [{"userId": user["id"], "type": "user", "color": "violet-200", "info": user}]
    data["extraParticipants"] = {"users": [user]}
    data["inviteStatuses"] = [{"userId": user["id"], "status": "pending", "isException": False}]
    data["attachments"] = _payload(LESSON)["attachments"]
    url = f"https://site/planner/api/v1/planned-meetings/49/{original}_2026-11-12T10:00:00+01:00"
    requests_mock.get(url, json=data)
    requests_mock.get(f"{url}/attachments/{data['attachments'][0]['id']}/download", content=ATTACHMENT)

    details = PlannedElementDetails(session, element=PlannedElement(**data))
    sut = details.get()

    assert sut.recurrence is not None
    assert sut.recurrence.original_recurrence_date == "2026-11-12T10:00:00+01:00"
    assert sut.repeat_options is not None
    assert sut.repeat_options.frequency == "daily"
    assert sut.repeat_options.interval == 1
    assert sut.repeat_options.until == date(2026, 11, 30)
    assert sut.extra_participants.users[0].id == user["id"]
    assert sut.invite_statuses[0].status == "pending"
    assert not sut.invite_statuses[0].is_exception

    [calendar] = sut.calendars
    assert isinstance(calendar, PlannedElementUserCalendar)
    assert calendar.info.id == user["id"]
    assert calendar.color == "violet-200"

    assert details.files()[0].download() == ATTACHMENT


def test_planned_element_details_keeps_a_kind_of_calendar_it_does_not_know(session: Smartschool, requests_mock):
    """A new kind of calendar must not break the detail view: it is kept by its type alone."""
    data = _payload(MEETING)
    data["calendars"] = [{"type": "brand-new-kind", "somethingElse": 1}]
    requests_mock.get(f"https://site/planner/api/v1/planned-meetings/49/{data['id']}", json=data)

    [calendar] = PlannedElementDetails(session, element=PlannedElement(**data)).get().calendars

    assert isinstance(calendar, PlannedElementUnknownCalendar)
    assert calendar.type == "brand-new-kind"


def test_planned_element_details_fetches_once(session: Smartschool, requests_mock):
    details = PlannedElementDetails(session, element=_element(LESSON))

    details.get()
    details.files()

    assert requests_mock.call_count == 1


def test_planned_element_files_download(session: Smartschool, tmp_path: Path):
    sut = PlannedElementDetails(session, element=_element(LESSON)).files()

    assert [file.filename for file in sut] == ["chapter 3.docx"]
    assert sut[0].download() == ATTACHMENT
    assert sut[0].download_to_dir(tmp_path).read_bytes() == ATTACHMENT


def test_planned_element_file_gets_a_filesystem_safe_name(session: Smartschool, requests_mock):
    data = _payload(LESSON)
    data["attachments"][0]["fileName"] = 'report: "part 1" <draft>.docx'
    requests_mock.get(f"https://site/planner/api/v1/planned-lessons/49/{data['id']}", json=data)

    [file] = PlannedElementDetails(session, element=PlannedElement(**data)).files()

    assert file.filename == "report - 'part 1'_draft.docx"


def test_planned_element_file_download_fails_on_an_http_error(session: Smartschool, requests_mock, tmp_path: Path):
    """An error page must not end up on disk as the file."""
    [file] = PlannedElementDetails(session, element=_element(LESSON)).files()
    requests_mock.get(f"https://site{file.download_url}", status_code=404, text="Not found")

    with pytest.raises(SmartSchoolDownloadError) as error:
        file.download_to_dir(tmp_path / "downloads")

    assert error.value.status_code == 404
    assert not list(tmp_path.rglob(file.filename))
