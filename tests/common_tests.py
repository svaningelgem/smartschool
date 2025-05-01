import contextlib
import warnings
from copy import deepcopy
from io import StringIO
from pathlib import Path

import pytest_mock
from bs4 import BeautifulSoup, FeatureNotFound, GuessedAtParserWarning

from smartschool.common import IsSaved, as_float, bs4_html, fill_form, make_filesystem_safe, save, send_email, xml_to_dict
from smartschool.objects import Student


def test_xml_to_dict():
    xml = """
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<server>
  <response>
    <status>ok</status>
    <actions>
        <sub attr="a">123</sub>
        <sub attr="a">456</sub>
        <sub attr="a"><extra/></sub>
    </actions>
  </response>
</server>
"""
    assert xml_to_dict(xml) == {
        "response": {
            "actions": {
                "sub": [
                    "123",
                    "456",
                    {"extra": None},
                ],
            },
            "status": "ok",
        },
    }


def test_save(tmp_path: Path) -> None:
    assert save(type_="todo", course_name="test", id_="123", data="Test") == IsSaved.NEW
    assert save(type_="todo", course_name="test", id_="123", data="Test") == IsSaved.SAME
    assert save(type_="todo", course_name="test", id_="123", data="Test2") == "Test"  # Returns the old data

    assert save(type_="todo", course_name="test", id_="456", data={"Test": 456}) == IsSaved.NEW
    assert save(type_="todo", course_name="test", id_="456", data={"Test": 456}) == IsSaved.SAME
    assert save(type_="todo", course_name="test", id_="456", data={"Test": 789}) == {"Test": 456}


def test_save_as_pydantic_dataclass(tmp_path: Path) -> None:
    sut = Student(
        id="a",
        pictureHash="b",
        pictureUrl="c",
        description={"startingWithFirstName": "d", "startingWithLastName": "e"},
        name={"startingWithFirstName": "f", "startingWithLastName": "g"},
        sort="h",
    )
    original = deepcopy(sut)

    assert save(type_="todo", course_name="test", id_="123", data=sut) == IsSaved.NEW
    assert save(type_="todo", course_name="test", id_="123", data=sut) == IsSaved.SAME

    sut.id = "i"
    assert save(type_="todo", course_name="test", id_="123", data=sut) == original


def test_send_email(mocker):
    mocker.patch("platform.system", return_value="Linux")
    server = mocker.patch("smtplib.SMTP")

    send_email(subject="Test", text="Just a test", email_to="me@myself.ai", email_from="me@myself.ai")

    server.assert_any_call("localhost")

    sendmail_call = server().__enter__().sendmail
    assert sendmail_call.call_args.kwargs["from_addr"] == "me@myself.ai"
    assert sendmail_call.call_args.kwargs["to_addrs"] == ["me@myself.ai"]
    assert sendmail_call.call_args.kwargs["msg"].startswith("Content-Type: multipart/alternative; boundary")
    assert "Subject: Test" in sendmail_call.call_args.kwargs["msg"]


def test_multi_email_on_windows(mocker):
    mocker.patch("platform.system", return_value="Windows")
    server = mocker.patch("smtplib.SMTP")

    target = StringIO()
    with contextlib.redirect_stdout(target):
        send_email(subject="Test", text="Just a test", email_to=["me@myself.ai", "me2@myself.ai"], email_from="me@myself.ai")

    server.assert_not_called()

    assert "Subject: Test" in target.getvalue()
    assert "Just a test" in target.getvalue()


def test_as_float():
    assert as_float("123,34") == 123.34
    assert as_float("123.34") == 123.34


def test_make_filesystem_safe():
    assert make_filesystem_safe("1 23?34_ab-'\".xml") == "1_23_34_ab-_.xml"


def test_bs4_html():
    sut = bs4_html("<html />")

    assert isinstance(sut, BeautifulSoup)


def test_bs4_html_no_good_options(mocker):
    mocker.patch("smartschool.common._used_bs4_option", new=None)

    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=GuessedAtParserWarning)
        mocker.patch("smartschool.common.BeautifulSoup", side_effect=[FeatureNotFound, FeatureNotFound, FeatureNotFound, BeautifulSoup("<html />")])

    sut = bs4_html("<html />")
    assert isinstance(sut, BeautifulSoup)


def test_fill_form(mocker: pytest_mock.MockerFixture):
    # Create sample HTML content with a form
    html_content = """
    <form>
        <input name="username" value="default_user">
        <input name="password" value="default_pass">
        <input name="email" value="default_email">
    </form>
    """
    html = BeautifulSoup(html_content, "html.parser")

    # Mock bs4_html to return our test HTML
    mocker.patch("smartschool.common.bs4_html", return_value=html)

    # Create mock Response object
    response = mocker.Mock()
    response.text = str(html)

    # Define values to fill
    values = {"username": "test_user", "email": "test@example.com"}

    # Call the function
    result = fill_form(response, "form", values)

    # Assert the result matches expectations
    assert result == {"username": "test_user", "password": "default_pass", "email": "test@example.com"}
