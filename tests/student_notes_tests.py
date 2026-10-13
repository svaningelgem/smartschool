from datetime import date, datetime
from urllib.parse import parse_qs

import pytest
import time_machine

from smartschool import (
    Smartschool,
    SmartSchoolParsingError,
    StudentAbsences,
    StudentNoteDetail,
    StudentNoteDetails,
    StudentNoteParam,
    StudentNotes,
)
from smartschool._common import convert_epoch_to_datetime


def _posted_command(requests_mock) -> str:
    return parse_qs(requests_mock.last_request.text)["command"][0]


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


def test_notes_ask_for_the_logged_in_user_by_default(session: Smartschool, requests_mock):
    list(StudentNotes(session))

    command = _posted_command(requests_mock)
    assert "<subsystem>lvs_pupils</subsystem>" in command
    assert "<action>getUserData</action>" in command
    assert '<param name="userID"><![CDATA[49_10880_2]]></param>' in command  # the id of the `session` fixture, untouched
    assert '<param name="groupID"><![CDATA[0]]></param>' in command
    assert requests_mock.last_request.url.endswith("/?module=LVS&file=dispatcher")


def test_notes_for_a_given_pupil_and_period(session: Smartschool, requests_mock):
    list(StudentNotes(session, pupil_id="49_99999_2", group_id=2468, since=date(2025, 9, 1)))

    command = _posted_command(requests_mock)
    assert '<param name="userID"><![CDATA[49_99999_2]]></param>' in command
    assert '<param name="groupID"><![CDATA[2468]]></param>' in command
    assert '"from": "2025-09-01"' in command


@time_machine.travel("2025-05-06")
def test_notes_without_a_start_date_reach_back_far(session: Smartschool, requests_mock):
    list(StudentNotes(session))

    command = _posted_command(requests_mock)
    assert '{"from": "2000-01-01", "until": "2026-05-07"}' in command  # a year and a day ahead
    for name, value in (("toolbarType", "main"), ("viewAllFilter", "[]"), ("filterData", "0")):
        assert f'<param name="{name}"><![CDATA[{value}]]></param>' in command


@time_machine.travel("2025-05-06")
def test_notes_since_a_date_ask_from_that_date(session: Smartschool, requests_mock):
    list(StudentAbsences(session, since=date(2025, 9, 1)))

    assert '{"from": "2025-09-01", "until": "2026-05-07"}' in _posted_command(requests_mock)


@pytest.mark.parametrize("pupil_id", ["", None])
def test_an_empty_pupil_id_means_the_logged_in_user(session: Smartschool, requests_mock, pupil_id):
    list(StudentNotes(session, pupil_id=pupil_id))

    assert '<param name="userID"><![CDATA[49_10880_2]]></param>' in _posted_command(requests_mock)


def test_a_single_note_is_still_a_list(session: Smartschool):
    notes = list(StudentNotes(session))

    assert [n.item_id for n in notes] == [5001]


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
    assert first.part_of_day == "VM"
    assert first.school_year == "2025-2026"

    assert second.part_of_day == "NM"
    assert second.info == "Synthetic info"


def test_details_of_an_announcement(session: Smartschool, requests_mock):
    detail = StudentNoteDetails(session, item_id=5001).get()

    command = _posted_command(requests_mock)
    assert "<action>getItemParams</action>" in command
    assert '<param name="itemID"><![CDATA[5001]]></param>' in command
    assert '<param name="userID"><![CDATA[0]]></param>' in command

    assert detail.item_id == 5001
    assert detail.text_html == ("<p>Synthetic: morgen gaan we naar het museum.</p><p>Neem een <strong>lunchpakket</strong> mee &amp; drinken.<br>Tot dan!</p>")
    assert detail.text == "Synthetic: morgen gaan we naar het museum.\nNeem een lunchpakket mee & drinken.\nTot dan!"
    assert detail.fields == {"Leerkracht": "Voorbeeld Vera"}  # the fixed instruction (type 8) is ignored
    assert detail.date is None  # an announcement has no date parameter
    assert detail.measure is None
    assert detail.attachments == []


def test_a_measure_and_a_date(session: Smartschool):
    detail = StudentNoteDetails(session, item_id=5002).get()

    assert detail.measure == "2de keer: schriftelijke mededeling"
    assert detail.date == datetime.fromisoformat("2025-01-15T10:00:00+01:00")
    assert detail.fields == {"Leerkracht": "Proef Peter"}
    assert detail.text_html is None
    assert detail.text is None


def test_a_single_param_is_still_a_list(session: Smartschool):
    detail = StudentNoteDetails(session, item_id=5002).get()

    assert [p.title for p in detail.params] == ["Leerkracht"]
    assert detail.params[0].param_type == 1
    assert detail.params[0].option_value is None
    assert detail.attachments == []  # no attachments parameter at all


def test_attachments_are_decoded(session: Smartschool):
    detail = StudentNoteDetails(session, item_id=5001).get()

    assert detail.attachments == [{"name": "synthetic.pdf", "fileID": 42}]


def test_broken_attachments_are_ignored(session: Smartschool):
    assert StudentNoteDetails(session, item_id=5001).get().attachments == []


def test_attachments_that_are_not_a_list_are_ignored(session: Smartschool):
    assert StudentNoteDetails(session, item_id=5001).get().attachments == []


def test_unknown_param_types_end_up_in_fields(session: Smartschool):
    detail = StudentNoteDetails(session, item_id=5001).get()

    assert detail.fields == {"Synthetic veld": "waarde", "Leeg veld": ""}


def test_no_params_gives_no_detail(session: Smartschool):
    assert not list(StudentNoteDetails(session, item_id=5001))


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("1759389300", "2025-10-02T09:15:00+02:00"),
        (1759389300, "2025-10-02T09:15:00+02:00"),
        ("1736931600", "2025-01-15T10:00:00+01:00"),
    ],
)
def test_epoch_seconds_are_brussels_time(value, expected):
    assert convert_epoch_to_datetime(value) == datetime.fromisoformat(expected)
    assert convert_epoch_to_datetime(value).utcoffset() == datetime.fromisoformat(expected).utcoffset()


@pytest.mark.parametrize("value", [None, "", "yesterday", 10**30])
def test_epoch_seconds_that_are_not_a_date_are_rejected(value):
    with pytest.raises(SmartSchoolParsingError):
        convert_epoch_to_datetime(value)


@pytest.mark.parametrize(
    ("html", "expected"),
    [
        ("<p>a <b>bold</b> and <i>italic</i>, <a href='x'>linked</a>.</p>", "a bold and italic, linked."),
        ("<p>one</p><p>two</p><div>three</div>", "one\ntwo\nthree"),
        ("<table><tr><th>h</th><th>i</th></tr><tr><td>a</td><td>b</td></tr></table>", "h\ni\na\nb"),
        ("<ul><li>x</li><li>y</li></ul><h2>head</h2>tail", "x\ny\nhead\ntail"),
        ("line<br>break<br/>again", "line\nbreak\nagain"),
        ("<p>keep</p><script>alert(1)</script><style>p {color: red}</style>", "keep"),
        ("caf&eacute; &amp; &lt;b&gt;&nbsp;x", "café & <b> x"),
        ("  spaced \n  out\t text  ", "spaced out text"),
        ("", ""),
    ],
)
def test_text_of_an_announcement(html, expected):
    param = StudentNoteParam(param_id=1, param_type=2, title="Mededeling", value=html)

    assert StudentNoteDetail(item_id=1, params=[param]).text == (expected or None)


def test_pupil_selection_is_keyword_only(session: Smartschool):
    for query in (StudentNotes, StudentAbsences):
        with pytest.raises(TypeError):
            query(session, {}, "49_99999_2")  # pylint: disable=too-many-function-args  # ty: ignore[too-many-positional-arguments]  # session and cache are the positional ones


def test_repr_hides_the_content_of_a_note(session: Smartschool):
    note = next(iter(StudentNotes(session)))

    shown = repr(note)
    assert "5001" in shown
    assert "Mededeling" in shown
    assert note.title not in shown
    assert note.author not in shown


def test_repr_hides_the_content_of_a_detail(session: Smartschool):
    detail = StudentNoteDetails(session, item_id=5001).get()

    shown = repr(detail)
    assert "5001" in shown
    for secret in ("museum", "Voorbeeld Vera"):
        assert secret not in shown
        assert secret not in repr(detail.params)


def test_attachments_without_a_value_are_empty():
    param = StudentNoteParam(param_id=1, param_type=6, title="Bijlagen", value="files")

    assert StudentNoteDetail(item_id=1, params=[param]).attachments == []


@pytest.mark.parametrize("tag", ["div", "p", "ul", "ol", "li", "tr", "td", "th", "blockquote", "h1", "h2", "h3", "h4", "h5", "h6"])
def test_every_block_tag_starts_a_new_line(tag):
    param = StudentNoteParam(param_id=1, param_type=2, title="Mededeling", value=f"x<{tag}>y</{tag}>z")

    assert StudentNoteDetail(item_id=1, params=[param]).text == "x\ny\nz"


@pytest.mark.parametrize(("html", "expected"), [("tail<div>x</div>", "tail\nx"), ("<p>a|b</p>", "a|b")])
def test_text_edges(html, expected):
    param = StudentNoteParam(param_id=1, param_type=2, title="Mededeling", value=html)

    assert StudentNoteDetail(item_id=1, params=[param]).text == expected
