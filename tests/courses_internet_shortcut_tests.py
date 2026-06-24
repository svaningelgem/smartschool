from datetime import datetime, timezone

import pytest

from smartschool import InternetShortcut, Smartschool, SmartSchoolException


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


def test_filename_without_extension(shortcut: InternetShortcut):
    shortcut.name = "document"
    assert shortcut.filename == "document.url"


def test_filename_with_extension_strips_last_extension(shortcut: InternetShortcut):
    shortcut.name = "document.pdf.url"
    assert shortcut.filename == "document.pdf.url"


def test_filename_with_single_extension_strips_it(shortcut: InternetShortcut):
    shortcut.name = "document.url"
    assert shortcut.filename == "document.url"
