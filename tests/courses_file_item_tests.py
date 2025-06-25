from datetime import datetime

import pytest

from smartschool.courses import FileItem, FolderItem
from smartschool.objects import CourseCondensed


class TestFileItemHappyFlow:
    @pytest.fixture
    def mock_folder(self, session):
        """Create a mock folder for testing file items."""
        course = CourseCondensed(id=123, name="Test Course", platformId="platform_123")
        return FolderItem(session=session, parent=None, course=course, name="Test Folder")

    @pytest.fixture
    def sample_file_item(self, session, mock_folder):
        """Create a sample file item for testing."""
        return FileItem(
            session=session,
            parent=mock_folder,
            id=1,
            name="test_document",
            mime_type="pdf",
            size_kb="150.5",
            last_modified="2024-01-15 10:30:00",
            download_url="/download/test_document.pdf",
            view_url="/view/test_document.pdf",
        )

    def test_file_item_initialization(self, sample_file_item):
        """Test file item is properly initialized with parsed values."""
        assert sample_file_item.id == 1
        assert sample_file_item.name == "test_document"
        assert sample_file_item.mime_type == "pdf"
        assert sample_file_item.size_kb == 150.5
        assert isinstance(sample_file_item.last_modified, datetime)
        assert sample_file_item.filename == "test_document.pdf"

    def test_file_item_suffix_mapping(self, session, mock_folder):
        """Test different mime types map to correct file suffixes."""
        test_cases = [
            ("docx", ".docx"),
            ("xlsx", ".xlsx"),
            ("pdf", ".pdf"),
            ("mp4", ".mp4"),
            ("jpg", ".jpg"),
            ("zip", ".zip"),
            ("unknown_type", ".unknown_type"),
        ]

        for mime_type, expected_suffix in test_cases:
            file_item = FileItem(
                session=session, parent=mock_folder, id=1, name="test_file", mime_type=mime_type, size_kb="100", last_modified="2024-01-15 10:30:00"
            )
            assert file_item._suffix == expected_suffix

    def test_file_download_bytes(self, sample_file_item):
        """Test downloading file as bytes."""
        content = sample_file_item.download()
        assert isinstance(content, bytes)

    def test_file_download_to_path(self, sample_file_item, tmp_path):
        """Test downloading file to specific path."""
        target_file = tmp_path / "downloaded_file.pdf"
        result_path = sample_file_item.download(target_file)

        assert result_path == target_file
        assert target_file.exists()

    def test_file_download_to_dir(self, sample_file_item, tmp_path):
        """Test downloading file to directory."""
        result_path = sample_file_item.download_to_dir(tmp_path)

        expected_path = tmp_path / "test_document.pdf"
        assert result_path == expected_path
        assert expected_path.exists()

    def test_file_download_skip_existing(self, sample_file_item, tmp_path):
        """Test that existing files are skipped when overwrite=False."""
        existing_file = tmp_path / "existing.pdf"
        existing_file.write_bytes(b"existing content")

        result_path = sample_file_item.download(existing_file, overwrite=False)

        assert result_path == existing_file
        assert existing_file.read_bytes() == b"existing content"

    def test_filename_without_extension(self, session, mock_folder):
        """Test filename generation when name has no extension."""
        file_item = FileItem(
            session=session, parent=mock_folder, id=1, name="document_without_ext", mime_type="pdf", size_kb="100", last_modified="2024-01-15 10:30:00"
        )
        assert file_item.filename == "document_without_ext.pdf"

    def test_filename_with_extension(self, session, mock_folder):
        """Test filename generation when name already has extension."""
        file_item = FileItem(
            session=session, parent=mock_folder, id=1, name="document.pdf", mime_type="pdf", size_kb="100", last_modified="2024-01-15 10:30:00"
        )
        assert file_item.filename == "document.pdf"
