from datetime import datetime, timezone

import pytest
from requests import Response

from smartschool import Smartschool
from smartschool.courses import FileItem


@pytest.fixture
def file_item(session: Smartschool) -> FileItem:
    return FileItem(session, None, 0, "test.pdf", "pdf", "123 kb", datetime.now(tz=timezone.utc), "dllink", "viewlink")


@pytest.mark.parametrize(
    ("mime_type", "expected_suffix"),
    [
        ("docx", ".docx"),
        ("word", ".docx"),
        ("doc", ".doc"),
        ("xlsx", ".xlsx"),
        ("excel", ".xlsx"),
        ("xls", ".xlsx"),
        ("odt", ".odt"),
        ("pdf", ".pdf"),
        ("powerpointpresentatie", ".pptx"),
        ("pptx", ".pptx"),
        ("ppt", ".ppt"),
        ("video", ".mp4"),
        ("m4v", ".mp4"),
        ("mp4", ".mp4"),
        ("wmv", ".wmv"),
        ("audio", ".mp3"),
        ("mp3", ".mp3"),
        ("zip", ".zip"),
        ("rar", ".rar"),
        ("7z", ".7z"),
        ("text", ".txt"),
        ("txt", ".txt"),
        ("jpg", ".jpg"),
        ("jpeg", ".jpg"),
        ("png", ".png"),
        ("html", ".html"),
        ("ascii", ".txt"),
        ("potx", ".potx"),
        ("unknown_type", ".unknown_type"),
    ],
)
def test_suffix_returns_correct_extensions_for_mime_types(mime_type: str, expected_suffix: str):
    """Test that _suffix returns appropriate file extensions for various mime types."""
    file_item = FileItem(session=None, parent=None, id=1, name="test", mime_type=mime_type, size_kb=100, last_modified="2023-01-01T00:00:00Z")

    assert file_item._suffix == expected_suffix


def test_real_download_returns_bytes_when_no_target(file_item: FileItem, mocker):
    mock_response = mocker.Mock(spec=Response)
    mock_response.content = b"file content"
    mock_response.headers = {}
    mock_session = mocker.patch.object(file_item.session, "get", return_value=mock_response)
    mocker.patch("smartschool.courses.save_test_response")

    result = file_item._real_download(None)

    mock_session.assert_called_once_with(file_item.download_url)
    mock_response.raise_for_status.assert_called_once()
    assert result == b"file content"


def test_real_download_writes_to_target_and_returns_path(file_item: FileItem, mocker, tmp_path):
    target = tmp_path / "test.pdf"
    mock_response = mocker.Mock(spec=Response)
    mock_response.content = b"file content"
    mock_response.headers = {}
    mocker.patch.object(file_item.session, "get", return_value=mock_response)
    mocker.patch("smartschool.courses.save_test_response")

    result = file_item._real_download(target)

    assert result == target
    assert target.read_bytes() == b"file content"


def test_real_download_logs_filename_suffix_mismatch(file_item: FileItem, mocker):
    mock_response = mocker.Mock(spec=Response)
    mock_response.content = b"file content"
    mock_response.headers = {"Content-Disposition": 'attachment; filename="test.txt"'}
    mocker.patch.object(file_item.session, "get", return_value=mock_response)
    mock_logger = mocker.patch("smartschool.courses.logger")

    file_item._real_download(None)

    mock_logger.warning.assert_called_once_with("Expected suffix .pdf, got .txt")


def test_real_download_no_warning_when_suffix_matches(file_item: FileItem, mocker):
    mock_response = mocker.Mock(spec=Response)
    mock_response.content = b"file content"
    mock_response.headers = {"Content-Disposition": 'attachment; filename="test.pdf"'}
    mocker.patch.object(file_item.session, "get", return_value=mock_response)
    mocker.patch("smartschool.courses.save_test_response")
    mock_logger = mocker.patch("smartschool.courses.logger")

    file_item._real_download(None)

    mock_logger.warning.assert_not_called()


def test_real_download_no_content_disposition_header(file_item: FileItem, mocker):
    mock_response = mocker.Mock(spec=Response)
    mock_response.content = b"file content"
    mock_response.headers = {}
    mocker.patch.object(file_item.session, "get", return_value=mock_response)
    mocker.patch("smartschool.courses.save_test_response")

    result = file_item._real_download(None)

    assert result == b"file content"


def test_real_download_content_disposition_without_filename(file_item: FileItem, mocker):
    mock_response = mocker.Mock(spec=Response)
    mock_response.content = b"file content"
    mock_response.headers = {"Content-Disposition": "attachment"}
    mocker.patch.object(file_item.session, "get", return_value=mock_response)
    mocker.patch("smartschool.courses.save_test_response")

    result = file_item._real_download(None)

    assert result == b"file content"


def test_download_returns_bytes_when_no_to_file(file_item: FileItem, mocker):
    mock_real_download = mocker.patch.object(file_item, "_real_download", return_value=b"content")

    result = file_item.download()

    mock_real_download.assert_called_once_with(None)
    assert result == b"content"


def test_download_creates_target_path_and_calls_real_download(file_item: FileItem, mocker, tmp_path):
    target_dir = tmp_path / "subdir"
    target_file = target_dir / "test.pdf"
    mock_create_safe_path = mocker.patch("smartschool.courses.create_filesystem_safe_path", return_value=target_file)
    mock_real_download = mocker.patch.object(file_item, "_real_download", return_value=target_file)

    result = file_item.download("some/path")

    mock_create_safe_path.assert_called_once_with("some/path")
    assert target_dir.exists()
    mock_real_download.assert_called_once_with(target_file)
    assert result == target_file


def test_download_returns_existing_file_when_not_overwrite(file_item: FileItem, mocker, tmp_path):
    existing_file = tmp_path / "existing.pdf"
    existing_file.write_bytes(b"existing content")
    mocker.patch("smartschool.courses.create_filesystem_safe_path", return_value=existing_file)
    mock_real_download = mocker.patch.object(file_item, "_real_download")

    result = file_item.download("some/path", overwrite=False)

    mock_real_download.assert_not_called()
    assert result == existing_file


def test_download_overwrites_existing_file_when_overwrite_true(file_item: FileItem, mocker, tmp_path):
    existing_file = tmp_path / "existing.pdf"
    existing_file.write_bytes(b"existing content")
    mocker.patch("smartschool.courses.create_filesystem_safe_path", return_value=existing_file)
    mock_real_download = mocker.patch.object(file_item, "_real_download", return_value=existing_file)

    result = file_item.download("some/path", overwrite=True)

    mock_real_download.assert_called_once_with(existing_file)
    assert result == existing_file


def test_download_with_path_object(file_item: FileItem, mocker, tmp_path):
    target_file = tmp_path / "test.pdf"
    mock_create_safe_path = mocker.patch("smartschool.courses.create_filesystem_safe_path", return_value=target_file)
    mock_real_download = mocker.patch.object(file_item, "_real_download", return_value=target_file)

    result = file_item.download(target_file)

    mock_create_safe_path.assert_called_once_with(target_file)
    mock_real_download.assert_called_once_with(target_file)
    assert result == target_file
