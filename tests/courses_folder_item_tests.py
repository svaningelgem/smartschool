import pytest
from requests import RequestException

from smartschool import SmartSchoolException, SmartSchoolParsingError
from smartschool._common import bs4_html


def test_get_folder_html_exception_handling(folder, mocker):
    """Test exception is wrapped in SmartSchoolException."""
    mocker.patch.object(folder.session, "get", side_effect=RequestException("Network error"))

    with pytest.raises(SmartSchoolException, match="Failed to fetch folder HTML: Network error"):
        folder._get_folder_html()  # pylint: disable=protected-access  # white-box test


def test_get_folder_html_captures_fixture_only_when_dev_tracing(folder, mocker):
    """Fixture capture is a dev-only side effect, gated behind dev_tracing."""
    save = mocker.patch("smartschool._courses.save_test_response")

    folder._get_folder_html()  # pylint: disable=protected-access  # white-box test
    save.assert_not_called()

    folder.session.dev_tracing = True
    folder._get_folder_html()  # pylint: disable=protected-access  # white-box test
    save.assert_called_once()


def test_get_mime_from_row_image_return_none(folder, mocker):
    """Test return None when no background-image found."""
    mock_row = mocker.Mock()
    mock_div = mocker.Mock()
    mock_div.get.return_value = "color: red; font-size: 12px"
    mock_row.select_one.return_value = mock_div

    result = folder._get_mime_from_row_image(mock_row)  # pylint: disable=protected-access  # white-box test

    assert result is None


def test_get_mime_from_row_image_continue_branch(folder, mocker):
    """Test continue branch when entry is empty."""
    mock_row = mocker.Mock()
    mock_div = mocker.Mock()
    mock_div.get.return_value = "  ; ; background-image: url(/mime_type_pdf/icon.png)"
    mock_row.select_one.return_value = mock_div

    result = folder._get_mime_from_row_image(mock_row)  # pylint: disable=protected-access  # white-box test

    assert result == "pdf"


def test_parse_folder_row_exception(folder, mocker):
    """Test exception when no smsc_cm_link found."""
    mock_row = mocker.Mock()
    mock_link = mocker.Mock()
    mock_link.get.return_value = ["other_class", "different_class"]  # no smsc_cm_link
    mock_row.select.return_value = [mock_link]

    with pytest.raises(SmartSchoolParsingError, match="No browse URL found"):
        folder._parse_folder_row(mock_row)  # pylint: disable=protected-access  # white-box test


def test_get_mime_from_row_image_missing_block(folder):
    """A row without the image block raises instead of AttributeError on None."""
    row = bs4_html("<tr id='docID_12'><td>no block here</td></tr>").select_one("tr")

    with pytest.raises(SmartSchoolParsingError, match=r"div\.smsc_cm_body_row_block"):
        folder._get_mime_from_row_image(row)  # pylint: disable=protected-access  # white-box test


def test_parse_document_row_missing_mime_block(folder):
    """A row without the mime block raises instead of AttributeError on None."""
    row = bs4_html("<tr id='docID_12'><td><a href='x'>file.pdf</a></td></tr>").select_one("tr")

    with pytest.raises(SmartSchoolParsingError, match=r"div\.smsc_cm_body_row_block_mime"):
        folder._parse_document_row(row)  # pylint: disable=protected-access  # white-box test


def test_get_folder_html_asserts_before_requesting_when_browse_url_is_none(folder, mocker):
    """A folder without a browse URL fails its own assert; nothing is requested."""
    folder.browse_url = None
    get = mocker.patch.object(folder.session, "get")

    with pytest.raises(AssertionError):
        folder._get_folder_html()  # pylint: disable=protected-access  # white-box test

    get.assert_not_called()


def test_get_mime_from_row_image_requires_a_style_attribute(folder):
    row = bs4_html('<div class="smsc_cm_body_row"><div class="smsc_cm_body_row_block">x</div></div>').select_one("div.smsc_cm_body_row")

    with pytest.raises(AssertionError, match=r"Expected a 'style' attribute on <div>"):
        folder._get_mime_from_row_image(row)  # pylint: disable=protected-access  # white-box test


def test_get_mime_from_row_image_requires_a_mime_in_the_background_image(folder):
    row = bs4_html('<div class="smsc_cm_body_row"><div class="smsc_cm_body_row_block" style="background-image: url(/nope.png)">x</div></div>').select_one(
        "div.smsc_cm_body_row"
    )

    with pytest.raises(AssertionError, match=r"No mime type in ' url\(/nope.png\)'"):
        folder._get_mime_from_row_image(row)  # pylint: disable=protected-access  # white-box test


def test_parse_document_row_requires_an_id(folder):
    row = bs4_html("<div class='smsc_cm_body_row'><a>file.pdf</a></div>").select_one("div.smsc_cm_body_row")

    with pytest.raises(AssertionError, match=r"Expected a 'id' attribute on <div>"):
        folder._parse_document_row(row)  # pylint: disable=protected-access  # white-box test


def test_parse_document_row_requires_a_mime_type(folder):
    row = bs4_html(
        "<div class='smsc_cm_body_row' id='docID_12'>"
        "<div class='smsc_cm_body_row_block_mime'>pdf - 1 kb - 2024-01-01</div>"
        "<div class='smsc_cm_body_row_block' style='color: red'>icon</div>"
        "<a>file.pdf</a>"
        "</div>"
    ).select_one("div.smsc_cm_body_row")

    with pytest.raises(AssertionError, match="No mime type in the row image"):
        folder._parse_document_row(row)  # pylint: disable=protected-access  # white-box test


def _document_row(inline: str) -> str:
    return (
        "<div class='smsc_cm_body_row' id='docID_12'>"
        "<div class='smsc_cm_body_row_block_mime'>pdf - 1 kb - 2024-01-01</div>"
        "<div class='smsc_cm_body_row_block' style='background-image: url(/mime_x_pdf/icon.png)'>icon</div>"
        "<a>file.pdf</a>"
        f"<div class='smsc_cm_body_row_block_inline'>{inline}</div>"
        "</div>"
    )


@pytest.mark.parametrize(
    ("inline", "expected"),
    [
        ("<iframe></iframe>", r"Expected a 'src' attribute on <iframe>"),
        ("<a>shortcut</a>", r"Expected a 'href' attribute on <a>"),
    ],
)
def test_parse_document_row_requires_a_link_on_an_inline_element(folder, inline: str, expected: str):
    row = bs4_html(_document_row(inline)).select_one("div.smsc_cm_body_row")

    with pytest.raises(AssertionError, match=expected):
        folder._parse_document_row(row)  # pylint: disable=protected-access  # white-box test


def test_parse_folder_row_requires_an_href(folder):
    row = bs4_html("<div class='smsc_cm_body_row'><a class='smsc_cm_link'>subfolder</a></div>").select_one("div.smsc_cm_body_row")

    with pytest.raises(AssertionError, match=r"Expected a 'href' attribute on <a>"):
        folder._parse_folder_row(row)  # pylint: disable=protected-access  # white-box test
