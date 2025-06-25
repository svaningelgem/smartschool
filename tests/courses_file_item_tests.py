import pytest

from smartschool.courses import FileItem


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
