import pytest
from requests import RequestException

from smartschool import CourseCondensed, FolderItem, SmartSchoolException, Smartschool


@pytest.fixture
def folder(session: Smartschool) -> FolderItem:
    return FolderItem(
        session=session,
        parent=None,
        course=CourseCondensed(
            session=session,
            name="Course",
            teacher="Teacher",
            url="url",
        ),
        name="Name",
    )


def test_get_folder_html_exception_handling(folder, mocker):
    """Test exception is wrapped in SmartSchoolException."""
    mocker.patch.object(folder.session, "get", side_effect=RequestException("Network error"))

    with pytest.raises(SmartSchoolException, match="Failed to fetch folder HTML: Network error"):
        folder._get_folder_html()


def test_get_mime_from_row_image_return_none(folder, mocker):
    """Test return None when no background-image found."""
    mock_row = mocker.Mock()
    mock_div = mocker.Mock()
    mock_div.get.return_value = "color: red; font-size: 12px"
    mock_row.select_one.return_value = mock_div

    result = folder._get_mime_from_row_image(mock_row)

    assert result is None


def test_get_mime_from_row_image_continue_branch(folder, mocker):
    """Test continue branch when entry is empty."""
    mock_row = mocker.Mock()
    mock_div = mocker.Mock()
    mock_div.get.return_value = "  ; ; background-image: url(/mime_type_pdf/icon.png)"
    mock_row.select_one.return_value = mock_div

    result = folder._get_mime_from_row_image(mock_row)

    assert result == "pdf"
