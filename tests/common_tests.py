import warnings
from copy import deepcopy
from pathlib import Path

import pytest_mock
from bs4 import BeautifulSoup, FeatureNotFound, GuessedAtParserWarning
from logprise import logger
from requests import Response
from smartschool import Smartschool

from smartschool.common import IsSaved, as_float, bs4_html, fill_form, get_all_values_from_form, make_filesystem_safe, save, send_email, xml_to_dict
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


def test_save(session: Smartschool, tmp_path: Path) -> None:
    assert save(session, type_="todo", course_name="test", id_="123", data="Test") == IsSaved.NEW
    assert save(session, type_="todo", course_name="test", id_="123", data="Test") == IsSaved.SAME
    assert save(session, type_="todo", course_name="test", id_="123", data="Test2") == "Test"  # Returns the old data

    assert save(session, type_="todo", course_name="test", id_="456", data={"Test": 456}) == IsSaved.NEW
    assert save(session, type_="todo", course_name="test", id_="456", data={"Test": 456}) == IsSaved.SAME
    assert save(session, type_="todo", course_name="test", id_="456", data={"Test": 789}) == {"Test": 456}


def test_save_as_pydantic_dataclass(session: Smartschool,tmp_path: Path) -> None:
    sut = Student(
        id="a",
        pictureHash="b",
        pictureUrl="c",
        description={"startingWithFirstName": "d", "startingWithLastName": "e"},
        name={"startingWithFirstName": "f", "startingWithLastName": "g"},
        sort="h",
    )
    original = deepcopy(sut)

    assert save(session,type_="todo", course_name="test", id_="123", data=sut) == IsSaved.NEW
    assert save(session,type_="todo", course_name="test", id_="123", data=sut) == IsSaved.SAME

    sut.id = "i"
    assert save(session,type_="todo", course_name="test", id_="123", data=sut) == original


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

    data_outputted = []
    mocker.patch.object(logger, "info", lambda x: data_outputted.append(x))

    send_email(subject="Test", text="Just a test", email_to=["me@myself.ai", "me2@myself.ai"], email_from="me@myself.ai")
    server.assert_not_called()

    assert "Subject: Test" in data_outputted
    assert "Just a test" in data_outputted


def test_as_float():
    assert as_float("123,34") == 123.34
    assert as_float("123.34") == 123.34


def test_make_filesystem_safe():
    assert make_filesystem_safe("1 23?34_ab-'\".xml") == "1_23_34_ab-_.xml"


def test_bs4_html():
    sut = bs4_html("<html />")

    assert isinstance(sut, BeautifulSoup)


def test_bs4_html_with_response(mocker):
    response = mocker.Mock(spec=Response)
    response.text = "<html />"
    sut = bs4_html(response)

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


def test_missing_name():
    """Test missing name attribute."""
    html = BeautifulSoup("""
    <form>
        <input value="test" />
        <input value="test2" name="test2"/>
    """)
    result = get_all_values_from_form(html, "form")
    assert result == [{"name": "test2", "value": "test2"}]


def test_select_with_explicit_values():
    """Test select with explicit value attributes."""
    html = BeautifulSoup(
        """
    <form>
        <select name="country">
            <option value="us">United States</option>
            <option value="ca" selected>Canada</option>
            <option value="uk">United Kingdom</option>
        </select>
    </form>
    """,
        "html.parser",
    )

    result = get_all_values_from_form(html, "form")
    select_element = result[0]

    assert select_element["name"] == "country"
    assert select_element["value"] == "ca"
    assert select_element["values"] == ["us", "ca", "uk"]


def test_select_without_value_attributes():
    """Test select where options use text content as values."""
    html = BeautifulSoup(
        """
    <form>
        <select name="fruit">
            <option>Apple</option>
            <option selected>Orange</option>
            <option>Banana</option>
        </select>
    </form>
    """,
        "html.parser",
    )

    result = get_all_values_from_form(html, "form")
    select_element = result[0]

    assert select_element["name"] == "fruit"
    assert select_element["value"] == "Orange"
    assert select_element["values"] == ["Apple", "Orange", "Banana"]


def test_select_mixed_value_types():
    """Test select with mix of value attributes and text content."""
    html = BeautifulSoup(
        """
    <form>
        <select name="size">
            <option value="s">Small</option>
            <option>Medium</option>
            <option value="l" selected>Large</option>
        </select>
    </form>
    """,
        "html.parser",
    )

    result = get_all_values_from_form(html, "form")
    select_element = result[0]

    assert select_element["name"] == "size"
    assert select_element["value"] == "l"
    assert select_element["values"] == ["s", "Medium", "l"]


def test_select_no_selection_defaults_to_first():
    """Test select without selected option defaults to first."""
    html = BeautifulSoup(
        """
    <form>
        <select name="color">
            <option value="red">Red</option>
            <option value="blue">Blue</option>
        </select>
    </form>
    """,
        "html.parser",
    )

    result = get_all_values_from_form(html, "form")
    select_element = result[0]

    assert select_element["value"] == "red"


def test_select_empty():
    """Test empty select element."""
    html = BeautifulSoup(
        """
    <form>
        <select name="empty"></select>
    </form>
    """,
        "html.parser",
    )

    result = get_all_values_from_form(html, "form")
    select_element = result[0]

    assert select_element["value"] is None
    assert select_element["values"] == []


def test_select_with_empty_options():
    """Test select with empty option values."""
    html = BeautifulSoup(
        """
    <form>
        <select name="test">
            <option value="">Choose...</option>
            <option value="val1">Option 1</option>
        </select>
    </form>
    """,
        "html.parser",
    )

    result = get_all_values_from_form(html, "form")
    select_element = result[0]

    # Empty values should be filtered out
    assert select_element["values"] == ["val1"]
    assert select_element["value"] == "val1"


def test_select_multiple_selections():
    """Test select with multiple attribute and multiple selected options."""
    html = BeautifulSoup(
        """
    <form>
        <select name="colors" multiple>
            <option value="red" selected>Red</option>
            <option value="blue">Blue</option>
            <option value="green" selected>Green</option>
            <option value="yellow">Yellow</option>
        </select>
    </form>
    """,
        "html.parser",
    )

    result = get_all_values_from_form(html, "form")
    select_element = result[0]

    assert select_element["name"] == "colors"
    assert select_element["value"] == ["red", "green"]
    assert select_element["values"] == ["red", "blue", "green", "yellow"]


def test_select_multiple_no_selections():
    """Test multiple select with no selected options."""
    html = BeautifulSoup(
        """
    <form>
        <select name="items" multiple>
            <option value="a">A</option>
            <option value="b">B</option>
        </select>
    </form>
    """,
        "html.parser",
    )

    result = get_all_values_from_form(html, "form")
    select_element = result[0]

    assert select_element["value"] == []


def test_select_case_insensitive_attributes():
    """Test case-insensitive handling of selected and multiple attributes."""
    html = BeautifulSoup(
        """
    <form>
        <select name="test1" MULTIPLE>
            <option value="a" SELECTED>A</option>
            <option value="b" Selected>B</option>
        </select>
        <select name="test2">
            <option value="x">X</option>
            <option value="y" SeLeCteD>Y</option>
        </select>
    </form>
    """,
        "html.parser",
    )

    result = get_all_values_from_form(html, "form")

    # Multiple select with case-insensitive attributes
    multi_select = next(el for el in result if el["name"] == "test1")
    assert multi_select["value"] == ["a", "b"]

    # Single select with case-insensitive selected
    single_select = next(el for el in result if el["name"] == "test2")
    assert single_select["value"] == "y"


def test_select_single_multiple_selected_last_wins():
    """Test single select with multiple selected options - last one wins."""
    html = BeautifulSoup(
        """
    <form>
        <select name="priority">
            <option value="low" selected>Low</option>
            <option value="med">Medium</option>
            <option value="high" selected>High</option>
        </select>
    </form>
    """,
        "html.parser",
    )

    result = get_all_values_from_form(html, "form")
    select_element = result[0]

    assert select_element["value"] == "high"  # Last selected wins
