import pytest

from requests import RequestException

from smartschool import FolderItem, SmartSchoolException, CourseCondensed


def test_get_folder_html_exception_handling(session, mocker):
    """Test exception is wrapped in SmartSchoolException."""
    instance = FolderItem(session=session, parent=None, course=CourseCondensed(session=session,name="Course", teacher="Teacher", url="url",), name="Name",)
    mocker.patch.object(session, "get", side_effect=RequestException("Network error"))

    with pytest.raises(SmartSchoolException, match="Failed to fetch folder HTML: Network error"):
        instance._get_folder_html()
