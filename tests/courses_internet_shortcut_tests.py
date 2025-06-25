from datetime import datetime, timezone

import pytest

from smartschool import Smartschool, SmartSchoolException
from smartschool.courses import InternetShortcut


@pytest.fixture
def shortcut(session: Smartschool) -> InternetShortcut:
    return InternetShortcut(session, None, 0, "test", "html", "123 kb", datetime.now(tz=timezone.utc), "dllink", "viewlink", link="https://example.com")


def test_post_init_raises_exception_when_no_link(session: Smartschool):
    with pytest.raises(SmartSchoolException, match="No link found in internet shortcut"):
        InternetShortcut(session, None, 0, "test", "html", "123 kb", datetime.now(tz=timezone.utc), "dllink", "viewlink", link="")


def test_post_init_raises_exception_when_link_is_none(session: Smartschool):
    with pytest.raises(SmartSchoolException, match="No link found in internet shortcut"):
        InternetShortcut(session, None, 0, "test", "html", "123 kb", datetime.now(tz=timezone.utc), "dllink", "viewlink", link=None)


def test_post_init_succeeds_with_valid_link(shortcut: InternetShortcut):
    assert shortcut.link == "https://example.com"


def test_real_download_returns_bytes_when_no_target(shortcut: InternetShortcut):
    result = shortcut._real_download(None)

    expected = b"[InternetShortcut]\r\nURL=https://example.com"
    assert result == expected


def test_real_download_writes_to_target_and_returns_path(shortcut: InternetShortcut, tmp_path):
    target = tmp_path / "test.url"
    result = shortcut._real_download(target)

    assert result == target
    content = target.read_bytes()
    expected = b"[InternetShortcut]\r\nURL=https://example.com"
    assert content == expected


def test_filename_without_extension(shortcut: InternetShortcut, mocker):
    mock_create_safe = mocker.patch("smartschool.courses.create_filesystem_safe_filename", return_value="safe_name.url")

    shortcut.name = "document"
    result = shortcut.filename

    mock_create_safe.assert_called_once_with("document.url")
    assert result == "safe_name.url"


def test_filename_with_extension_strips_last_extension(shortcut: InternetShortcut, mocker):
    mock_create_safe = mocker.patch("smartschool.courses.create_filesystem_safe_filename", return_value="safe_name.url")

    shortcut.name = "document.pdf.url"
    result = shortcut.filename

    mock_create_safe.assert_called_once_with("document.pdf.url")
    assert result == "safe_name.url"


def test_filename_with_single_extension_strips_it(shortcut: InternetShortcut, mocker):
    mock_create_safe = mocker.patch("smartschool.courses.create_filesystem_safe_filename", return_value="safe_name.url")

    shortcut.name = "document.url"
    result = shortcut.filename

    mock_create_safe.assert_called_once_with("document.url")
    assert result == "safe_name.url"
