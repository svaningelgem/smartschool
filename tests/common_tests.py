import contextlib
from io import StringIO
from pathlib import Path

import pytest

from smartschool.common import IsSaved, as_float, capture_and_email_all_exceptions, make_filesystem_safe, save, send_email, xml_to_dict


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


def test_save(mocker, tmp_path):
    mocker.patch('smartschool.common.CACHE', new=Path.cwd())

    assert save(type_="todo", course_name="test", id_="123", data="Test") == IsSaved.NEW
    assert save(type_="todo", course_name="test", id_="123", data="Test") == IsSaved.SAME
    assert save(type_="todo", course_name="test", id_="123", data="Test2") == "Test"  # Returns the old data

    assert save(type_="todo", course_name="test", id_="456", data={"Test": 456}) == IsSaved.NEW
    assert save(type_="todo", course_name="test", id_="456", data={"Test": 456}) == IsSaved.SAME
    assert save(type_="todo", course_name="test", id_="456", data={"Test": 789}) == {"Test": 456}


def test_send_email(mocker):
    mocker.patch("platform.system", return_value="Linux")
    server = mocker.patch("smtplib.SMTP")

    send_email(subject="Test", text="Just a test", email_to="me@myself.ai", email_from="me@myself.ai")

    server.assert_any_call('localhost')

    sendmail_call = server().__enter__().sendmail
    assert sendmail_call.call_args.kwargs['from_addr'] == 'me@myself.ai'
    assert sendmail_call.call_args.kwargs['to_addrs'] == ['me@myself.ai']
    assert sendmail_call.call_args.kwargs['msg'].startswith('Content-Type: multipart/alternative; boundary')
    assert "Subject: Test" in sendmail_call.call_args.kwargs['msg']


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


def test_capture_and_email_all_exceptions(mocker):
    send_email = mocker.patch('smartschool.common.send_email')

    @capture_and_email_all_exceptions(email_from="me@myself.ai", email_to="me@myself.ai")
    def test():
        raise KeyError

    target = StringIO()
    with contextlib.redirect_stdout(target):
        with pytest.raises(SystemExit):
            test()

    send_email.assert_called_once()


def test_capture_and_email_all_exceptions_no_exception(mocker):
    send_email = mocker.patch('smartschool.common.send_email')

    @capture_and_email_all_exceptions(email_from="me@myself.ai", email_to="me@myself.ai")
    def test():
        return 42

    target = StringIO()
    with contextlib.redirect_stdout(target):
        assert test() == 42

    send_email.assert_not_called()

    assert '[common_tests.test] Start' in target.getvalue()
    assert '[common_tests.test] Finished' in target.getvalue()
