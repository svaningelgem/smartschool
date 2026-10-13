import dataclasses
import json
import logging
import xml.etree.ElementTree as ET
from datetime import date, datetime
from urllib.parse import parse_qs

import pytest
import time_machine

from smartschool import (
    PartOfDay,
    Smartschool,
    SmartSchoolParsingError,
    StudentAbsence,
    StudentAbsences,
    StudentNoteAttachment,
    StudentNoteDetail,
    StudentNoteDetails,
    StudentNoteParam,
    StudentNoteParamType,
    StudentNotes,
)
from smartschool._common import convert_to_datetime

_QUERIES = (StudentNotes, StudentAbsences)


def _posted_command(requests_mock) -> ET.Element:
    return ET.fromstring(parse_qs(requests_mock.last_request.text)["command"][0])


def _posted_params(requests_mock) -> dict[str, str]:
    return {p.get("name", ""): p.text or "" for p in _posted_command(requests_mock).iter("param")}


def _detail(*params: StudentNoteParam) -> StudentNoteDetail:
    return StudentNoteDetail(item_id=1, params=list(params))


def _param(param_type: int, value: str = "", option_value: str = "", param_id: int = 1, title: str = "t") -> StudentNoteParam:
    return StudentNoteParam(
        param_id=param_id,
        param_type=param_type,
        title=title,
        value=value,
        option_value=option_value,  # ty: ignore[unknown-argument]  # ty only knows the alias
    )


def _announcement(html: str) -> StudentNoteDetail:
    return _detail(_param(StudentNoteParamType.TEXT, html))


def test_notes_happy_flow(session: Smartschool):
    notes = list(StudentNotes(session))

    assert [n.item_id for n in notes] == [5001, 5002, 5003]
    mededeling, ordemaatregel, welzijn = notes

    assert mededeling.cat_name == "Mededeling"
    assert mededeling.title == "Synthetic: uitstap naar het museum"
    assert mededeling.date == datetime.fromisoformat("2025-10-02T09:15:00+02:00")
    assert mededeling.author == "Voorbeeld Vera"
    assert mededeling.author_reverse == "Vera Voorbeeld"
    assert (mededeling.group_id, mededeling.pupil_id, mededeling.cat_id) == (1001, 9001, 11)
    assert mededeling.viewed is True
    assert mededeling.private is False
    assert mededeling.school_year == "2025-2026"
    assert mededeling.study_direction == "Synthetic Richting"

    assert ordemaatregel.viewed is False
    assert ordemaatregel.date == datetime.fromisoformat("2025-01-15T10:00:00+01:00")  # winter time

    assert welzijn.cat_name == "Gedrag & Welzijn (café)"  # spaces, an ampersand and an accent
    assert welzijn.title == ""  # an empty title
    assert welzijn.private is True


def test_notes_may_leave_out_the_personal_elements(session: Smartschool):
    (note,) = StudentNotes(session)

    assert (note.item_id, note.title, note.author, note.author_reverse) == (5001, "", "", "")


@pytest.mark.parametrize("query", _QUERIES)
def test_queries_ask_for_the_logged_in_user_by_default(session: Smartschool, requests_mock, query):
    list(query(session))

    command = _posted_command(requests_mock)
    params = _posted_params(requests_mock)
    assert command.findtext(".//subsystem") == "lvs_pupils"
    assert command.findtext(".//action") == "getUserData"
    assert params["userID"] == "49_10880_2"  # the id of the `session` fixture, untouched
    assert params["groupID"] == "0"
    assert (params["toolbarType"], params["viewAllFilter"], params["filterData"]) == ("main", "[]", "0")
    assert requests_mock.last_request.url.endswith("/?module=LVS&file=dispatcher")


@pytest.mark.parametrize("query", _QUERIES)
def test_queries_for_a_given_user_and_group(session: Smartschool, requests_mock, query):
    list(query(session, user_id="49_99999_2", group_id=2468))

    params = _posted_params(requests_mock)
    assert params["userID"] == "49_99999_2"
    assert params["groupID"] == "2468"


@pytest.mark.parametrize("query", _QUERIES)
def test_an_empty_user_id_means_the_logged_in_user(session: Smartschool, requests_mock, query):
    list(query(session, user_id=""))

    assert _posted_params(requests_mock)["userID"] == "49_10880_2"


@time_machine.travel("2025-05-06")
@pytest.mark.parametrize("query", _QUERIES)
def test_queries_without_a_period_reach_back_far_and_a_year_ahead(session: Smartschool, requests_mock, query):
    list(query(session))

    sy_range = json.loads(_posted_params(requests_mock)["syRange"])
    assert sy_range["from"] == "2000-01-01"
    assert date.fromisoformat(sy_range["until"]) > date(2026, 4, 1)


@pytest.mark.parametrize("query", _QUERIES)
@pytest.mark.parametrize("day", [date(2024, 9, 1), datetime(2024, 9, 1, 8, 30)])  # a datetime must give the same range
def test_queries_for_a_given_period(session: Smartschool, requests_mock, query, day):
    list(query(session, since=day, until=date(2025, 8, 31)))

    assert json.loads(_posted_params(requests_mock)["syRange"]) == {"from": "2024-09-01", "until": "2025-08-31"}


@pytest.mark.parametrize("query", _QUERIES)
def test_the_user_selection_is_keyword_only(session: Smartschool, query):
    with pytest.raises(TypeError):
        query(session, {}, "49_99999_2")  # pylint: disable=too-many-function-args  # session and cache are positional


def test_a_single_note_is_still_a_list(session: Smartschool):
    assert [n.item_id for n in StudentNotes(session)] == [5001]


def test_no_notes_and_no_absences(session: Smartschool):
    assert not list(StudentNotes(session))
    assert not list(StudentAbsences(session))


def test_an_empty_body_is_an_empty_result(session: Smartschool):
    assert not list(StudentNotes(session))


def test_only_absences(session: Smartschool):
    assert not list(StudentNotes(session))
    assert len(list(StudentAbsences(session))) == 2


def test_absences_happy_flow(session: Smartschool):
    first, second = StudentAbsences(session)

    assert first.absent_id == 7001
    assert first.code == "Z"
    assert first.description == "Ziek"
    assert first.date == date(2025, 10, 6)  # midnight Brussels time, not the day before in UTC
    assert first.info == ""
    assert first.color == "#aabbcc"
    assert first.part_of_day is PartOfDay.MORNING
    assert first.school_year == "2025-2026"

    assert second.part_of_day is PartOfDay.AFTERNOON
    assert second.info == "Synthetic info"
    assert "Synthetic info" not in repr(second)  # free text: personal content


def test_unknown_parts_of_the_day_are_kept(session: Smartschool, caplog):
    unknown, empty = StudentAbsences(session)
    warnings = [r.getMessage() for r in caplog.records if r.levelno == logging.WARNING]

    assert unknown.part_of_day == "XX"
    assert empty.part_of_day is None
    assert warnings == ["Unknown part of the day 'XX', please report it"]  # the empty code stays quiet


def test_an_unknown_part_of_the_day_is_one_member_that_warns_once(caplog):
    first, second = PartOfDay("YY"), PartOfDay("YY")

    assert first is second
    assert first not in set(PartOfDay)  # not promoted to a real member
    assert [r.getMessage() for r in caplog.records if r.levelno == logging.WARNING] == ["Unknown part of the day 'YY', please report it"]


def test_an_empty_part_of_the_day_is_none_without_a_warning(caplog):
    assert _absence(date(2025, 10, 6), part_of_day="").part_of_day is None  # a raw API value
    assert not caplog.records


def test_a_part_of_the_day_must_be_a_string():
    with pytest.raises(ValueError, match="is not a valid PartOfDay"):
        PartOfDay(5)


def test_the_part_of_the_day_is_a_plain_string_for_json(session: Smartschool):
    first, _ = StudentAbsences(session)

    assert json.dumps({"pod": first.part_of_day}) == '{"pod": "VM"}'
    assert str(first.part_of_day) == "VM"


def _absence(day, part_of_day=PartOfDay.MORNING) -> StudentAbsence:
    # The validators take the raw API values, which the type hints don't list.
    return StudentAbsence(
        absent_id=1,
        code="Z",
        description="",
        date=day,
        info="",
        color="",
        part_of_day=part_of_day,
        school_year="",
    )


def test_an_absence_date_is_the_day_of_the_epoch():
    absence = _absence("1759389300")

    assert absence.date == date(2025, 10, 2)  # 09:15 Brussels time, not a midnight stamp


def test_records_survive_replace(session: Smartschool):
    note = next(iter(StudentNotes(session)))
    absence = next(iter(StudentAbsences(session)))

    assert dataclasses.replace(note, viewed=False).viewed is False
    assert dataclasses.replace(note, viewed=False).date == note.date
    assert dataclasses.replace(absence, code="B").date == absence.date
    assert _absence(date(2025, 10, 6)).date == date(2025, 10, 6)


def test_repr_hides_the_personal_content_of_a_note(session: Smartschool):
    note = next(iter(StudentNotes(session)))

    shown = repr(note)
    assert "5001" in shown
    assert "Mededeling" in shown
    assert "Voorbeeld" not in shown  # author, in either order
    assert "museum" not in shown  # title


def test_details_of_an_announcement(session: Smartschool, requests_mock):
    detail = StudentNoteDetails(session, item_id=5001).get()

    command = _posted_command(requests_mock)
    params = _posted_params(requests_mock)
    assert command.findtext(".//action") == "getItemParams"
    assert params == {"userID": "0", "itemID": "5001"}

    assert detail.item_id == 5001
    assert detail.text_html == "<p>Synthetic: morgen gaan we naar het museum.</p><p>Neem een <strong>lunchpakket</strong> mee &amp; drinken.<br>Tot dan!</p>"
    assert detail.text == "Synthetic: morgen gaan we naar het museum.\nNeem een lunchpakket mee & drinken.\nTot dan!"
    assert detail.fields == {"Leerkracht": "Voorbeeld Vera"}  # the fixed instruction (type 8) is ignored
    assert detail.date is None  # an announcement has no date parameter
    assert detail.choice == ""
    assert detail.attachments == []


def test_a_measure_and_a_date(session: Smartschool):
    detail = StudentNoteDetails(session, item_id=5002).get()

    assert detail.choice == "2de keer: schriftelijke mededeling"
    assert detail.date == datetime.fromisoformat("2025-01-15T10:00:00+01:00")
    assert detail.fields == {"Leerkracht": "Proef Peter"}
    assert detail.text_html == ""
    assert detail.text == ""
    assert "schriftelijke" not in repr(detail)  # the measure is personal content
    assert "schriftelijke" not in repr(detail.params)


def test_an_empty_date_param_is_no_date(session: Smartschool):
    detail = StudentNoteDetails(session, item_id=5002).get()

    assert detail.date is None
    assert detail.fields == {}


def test_a_single_param_is_still_a_list(session: Smartschool):
    detail = StudentNoteDetails(session, item_id=5002).get()

    assert [p.title for p in detail.params] == ["Leerkracht"]
    assert detail.params[0].param_type == 1  # a type that isn't in `StudentNoteParamType`
    assert detail.choice == ""
    assert detail.attachments == []  # no attachments parameter at all


def test_no_params_gives_a_detail_without_params(session: Smartschool):
    detail = StudentNoteDetails(session, item_id=5002).get()

    assert detail.item_id == 5002
    assert detail.params == []
    assert (detail.text, detail.date, detail.choice, detail.attachments, detail.fields) == ("", None, "", [], {})


def test_an_empty_answer_has_no_detail(session: Smartschool):
    assert not list(StudentNoteDetails(session, item_id=5002))


def test_attachments_are_decoded(session: Smartschool):
    (attachment,) = StudentNoteDetails(session, item_id=5001).get().attachments

    assert attachment == StudentNoteAttachment(file_id=42, file_name="synthetic.pdf", file_mime="application/pdf", file_wopi=False, file_hash="0123abcd")
    assert "synthetic.pdf" not in repr(attachment)  # personal content


def test_broken_attachments_are_ignored(session: Smartschool):
    assert StudentNoteDetails(session, item_id=5001).get().attachments == []


def test_attachments_that_are_not_files_are_ignored(session: Smartschool):
    assert StudentNoteDetails(session, item_id=5001).get().attachments == []


def test_attachments_without_a_value_are_empty():
    assert _detail(_param(StudentNoteParamType.ATTACHMENTS, "files")).attachments == []


def test_unknown_param_types_end_up_in_fields(session: Smartschool):
    assert StudentNoteDetails(session, item_id=5001).get().fields == {"Synthetic veld": "waarde", "Leeg veld": ""}


def test_the_first_parameter_of_a_type_wins_and_the_others_stay_visible(session: Smartschool):
    detail = StudentNoteDetails(session, item_id=5002).get()

    assert detail.date == datetime.fromisoformat("2025-01-15T10:00:00+01:00")  # "Van", not "Tot"
    assert detail.text_html == "<p>eerste</p>"
    assert detail.choice == "Eerste keuze"  # the label, not the option id
    assert detail.fields == {"Tot": "1737000000", "Tweede tekst": "<p>tweede</p>", "Tweede keuze": "Andere keuze"}
    assert [p.title for p in detail.params] == ["Van", "Tot", "Eerste tekst", "Tweede tekst", "Keuze", "Tweede keuze"]
    assert [p.value for p in detail.params if p.param_type == StudentNoteParamType.SELECT] == ["3", "5"]  # the option ids stay in params


def test_repr_hides_the_personal_content_of_a_detail(session: Smartschool):
    detail = StudentNoteDetails(session, item_id=5001).get()

    assert "5001" in repr(detail)
    for secret in ("museum", "Voorbeeld", "synthetic.pdf"):
        assert secret not in repr(detail)
        assert secret not in repr(detail.params)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("1759389300", "2025-10-02T09:15:00+02:00"),
        (1759389300, "2025-10-02T09:15:00+02:00"),
        ("1759389300.0", "2025-10-02T09:15:00+02:00"),
        (1759389300.0, "2025-10-02T09:15:00+02:00"),
        ("1736931600", "2025-01-15T10:00:00+01:00"),
        (datetime.fromisoformat("2025-10-02T09:15:00+02:00"), "2025-10-02T09:15:00+02:00"),  # already parsed
    ],
)
def test_epoch_seconds_are_brussels_time(value, expected):
    assert convert_to_datetime(value) == datetime.fromisoformat(expected)
    assert convert_to_datetime(value).utcoffset() == datetime.fromisoformat(expected).utcoffset()


@pytest.mark.parametrize("value", ["", "yesterday", 10**30])
def test_epoch_seconds_that_are_not_a_date_are_rejected(value):
    with pytest.raises(SmartSchoolParsingError):
        convert_to_datetime(value)


@pytest.mark.parametrize(
    ("html", "expected"),
    [
        ("<p>a <b>bold</b> and <i>italic</i>, <a href='x'>linked</a>.</p>", "a bold and italic, linked."),
        ("<p>one</p><p>two</p><div>three</div>", "one\ntwo\nthree"),
        ("<table><tr><th>h</th><th>i</th></tr><tr><td>a</td><td>b</td></tr></table>", "h\ni\na\nb"),
        ("<ul><li>x</li><li>y</li></ul><h2>head</h2>tail", "x\ny\nhead\ntail"),
        ("line<br>break<br/>again", "line\nbreak\nagain"),
        ("a<hr>b", "a\nb"),
        ("<section>a</section><section>b</section>", "a\nb"),
        ("<dl><dt>t</dt><dd>d</dd></dl>", "t\nd"),
        ("<p>keep</p><script>alert(1)</script><style>p {color: red}</style>", "keep"),
        ("caf&eacute; &amp; &lt;b&gt;&nbsp;x", "café & <b> x"),
        ("  spaced \n  out\t text  ", "spaced out text"),
        ("tail<div>x</div>", "tail\nx"),
        ("<p>a|b</p>", "a|b"),
        ("a\x00b", "ab"),  # the internal separator can't be injected
        ("<tr><td>a</td><td>b</td></tr>", "a\nb"),  # every cell is its own line
        ("Hallo <font color='red'>rode</font> <strike>x</strike> <big>b</big> <tt>t</tt> <label>l</label> wereld", "Hallo rode x b t l wereld"),
        ("<p></p>", ""),
        ("", ""),
    ],
)
def test_text_of_an_announcement(html, expected):
    assert _announcement(html).text == expected


@pytest.mark.parametrize("tag", ["blockquote", "figure", "h6", "article", "ol", "pre", "tr"])
def test_a_block_tag_that_is_not_inline_starts_a_new_line(tag):
    assert _announcement(f"x<{tag}>y</{tag}>z").text == "x\ny\nz"


@pytest.mark.parametrize("tag", ["a", "abbr", "b", "code", "em", "i", "span", "strong", "sub", "sup", "u"])
def test_an_inline_tag_keeps_the_text_together(tag):
    assert _announcement(f"x<{tag}>y</{tag}>z").text == "xyz"
