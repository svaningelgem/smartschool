from datetime import datetime, timezone

import pytest
from requests import Response

from smartschool import FileItem, Smartschool


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


def _mock_get(file_item: FileItem, mocker, *, content: bytes = b"file content", headers: dict | None = None):
    """Stub the HTTP boundary (session.get) — the only thing a download test legitimately mocks."""
    response = mocker.Mock(spec=Response)
    response.content = content
    response.headers = headers or {}
    return mocker.patch.object(file_item.session, "get", return_value=response)


def test_real_download_returns_bytes_when_no_target(file_item: FileItem, mocker):
    mock_get = _mock_get(file_item, mocker)

    result = file_item._real_download(None)

    mock_get.assert_called_once_with(file_item.download_url)
    assert result == b"file content"


def test_real_download_writes_to_target_and_returns_path(file_item: FileItem, mocker, tmp_path):
    target = tmp_path / "test.pdf"
    _mock_get(file_item, mocker)

    result = file_item._real_download(target)

    assert result == target
    assert target.read_bytes() == b"file content"


def test_real_download_logs_filename_suffix_mismatch(file_item: FileItem, mocker):
    _mock_get(file_item, mocker, headers={"Content-Disposition": 'attachment; filename="test.txt"'})
    mock_logger = mocker.patch("smartschool.courses.logger")

    file_item._real_download(None)

    mock_logger.warning.assert_called_once_with("Expected suffix {}, got {}", ".pdf", ".txt")


def test_real_download_no_warning_when_suffix_matches(file_item: FileItem, mocker):
    _mock_get(file_item, mocker, headers={"Content-Disposition": 'attachment; filename="test.pdf"'})
    mock_logger = mocker.patch("smartschool.courses.logger")

    file_item._real_download(None)

    mock_logger.warning.assert_not_called()


def test_real_download_no_content_disposition_header(file_item: FileItem, mocker):
    _mock_get(file_item, mocker)

    assert file_item._real_download(None) == b"file content"


def test_real_download_content_disposition_without_filename(file_item: FileItem, mocker):
    _mock_get(file_item, mocker, headers={"Content-Disposition": "attachment"})

    assert file_item._real_download(None) == b"file content"


def test_real_download_skips_fixture_capture_unless_dev_tracing(file_item: FileItem, mocker):
    _mock_get(file_item, mocker)
    save = mocker.patch("smartschool.courses.save_test_response")

    file_item._real_download(None)
    save.assert_not_called()

    file_item.session.dev_tracing = True
    file_item._real_download(None)
    save.assert_called_once()


def test_download_returns_bytes_when_no_to_file(file_item: FileItem, mocker):
    _mock_get(file_item, mocker, content=b"content")

    assert file_item.download() == b"content"


def test_download_creates_parent_dirs_and_writes_file(file_item: FileItem, mocker, tmp_path):
    target = tmp_path / "subdir" / "test.pdf"
    _mock_get(file_item, mocker)

    result = file_item.download(target)

    assert (tmp_path / "subdir").is_dir()
    assert result.read_bytes() == b"file content"


def test_download_returns_existing_file_without_downloading(file_item: FileItem, mocker, tmp_path):
    (tmp_path / "test.pdf").write_bytes(b"existing content")
    mock_get = _mock_get(file_item, mocker)

    result = file_item.download_to_dir(tmp_path, overwrite=False)

    mock_get.assert_not_called()
    assert result.read_bytes() == b"existing content"


def test_download_overwrites_existing_file_when_overwrite_true(file_item: FileItem, mocker, tmp_path):
    (tmp_path / "test.pdf").write_bytes(b"old content")
    _mock_get(file_item, mocker, content=b"new content")

    result = file_item.download_to_dir(tmp_path, overwrite=True)

    assert result.read_bytes() == b"new content"


def test_download_accepts_string_path(file_item: FileItem, mocker, tmp_path):
    _mock_get(file_item, mocker)

    result = file_item.download(str(tmp_path / "out.pdf"))

    assert result.read_bytes() == b"file content"
