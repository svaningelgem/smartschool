import pytest

from smartschool.courses import FolderItem, InternetShortcut
from smartschool.exceptions import SmartSchoolException
from smartschool.objects import CourseCondensed


class TestInternetShortcutHappyFlow:
    @pytest.fixture
    def sample_shortcut(self, session):
        """Create a sample internet shortcut for testing."""
        course = CourseCondensed(id=123, name="Test Course", platformId="platform_123")
        folder = FolderItem(session=session, parent=None, course=course, name="Test Folder")

        return InternetShortcut(
            session=session,
            parent=folder,
            id=2,
            name="Google Search",
            mime_type="url",
            size_kb="1",
            last_modified="2024-01-15 10:30:00",
            link="https://www.google.com",
        )

    def test_shortcut_initialization(self, sample_shortcut):
        """Test internet shortcut is properly initialized."""
        assert sample_shortcut.name == "Google Search"
        assert sample_shortcut.link == "https://www.google.com"
        assert sample_shortcut.filename == "Google_Search.url"

    def test_shortcut_download_bytes(self, sample_shortcut):
        """Test downloading shortcut as bytes."""
        content = sample_shortcut.download()

        expected_content = b"[InternetShortcut]\r\nURL=https://www.google.com"
        assert content == expected_content

    def test_shortcut_download_to_file(self, sample_shortcut, tmp_path):
        """Test downloading shortcut to file."""
        target_file = tmp_path / "shortcut.url"
        result_path = sample_shortcut.download(target_file)

        assert result_path == target_file
        assert target_file.exists()

        content = target_file.read_text(encoding="utf8")
        assert "[InternetShortcut]" in content
        assert "URL=https://www.google.com" in content

    def test_filename_generation_with_extension(self, session):
        """Test filename generation when name has extension."""
        course = CourseCondensed(id=123, name="Test Course", platformId="platform_123")
        folder = FolderItem(session=session, parent=None, course=course, name="Test Folder")

        shortcut = InternetShortcut(
            session=session,
            parent=folder,
            id=1,
            name="My Link.html",
            mime_type="url",
            size_kb="1",
            last_modified="2024-01-15 10:30:00",
            link="https://example.com",
        )
        assert shortcut.filename == "My_Link.url"

    def test_filename_generation_without_extension(self, session):
        """Test filename generation when name has no extension."""
        course = CourseCondensed(id=123, name="Test Course", platformId="platform_123")
        folder = FolderItem(session=session, parent=None, course=course, name="Test Folder")

        shortcut = InternetShortcut(
            session=session, parent=folder, id=1, name="My Link", mime_type="url", size_kb="1", last_modified="2024-01-15 10:30:00", link="https://example.com"
        )
        assert shortcut.filename == "My_Link.url"

    def test_shortcut_initialization_without_link_raises_exception(self, session):
        """Test that creating shortcut without link raises exception."""
        course = CourseCondensed(id=123, name="Test Course", platformId="platform_123")
        folder = FolderItem(session=session, parent=None, course=course, name="Test Folder")

        with pytest.raises(SmartSchoolException, match="No link found in internet shortcut"):
            InternetShortcut(
                session=session, parent=folder, id=1, name="Invalid Shortcut", mime_type="url", size_kb="1", last_modified="2024-01-15 10:30:00", link=""
            )

    def test_shortcut_download_to_dir(self, sample_shortcut, tmp_path):
        """Test downloading shortcut to directory."""
        result_path = sample_shortcut.download_to_dir(tmp_path)

        expected_path = tmp_path / "Google_Search.url"
        assert result_path == expected_path
        assert expected_path.exists()

        content = expected_path.read_text(encoding="utf8")
        assert "URL=https://www.google.com" in content
