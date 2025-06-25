import pytest

from smartschool.courses import FolderItem
from smartschool.objects import CourseCondensed


class TestFolderItemHappyFlow:
    @pytest.fixture
    def sample_folder(self, session):
        """Create a sample folder for testing."""
        course = CourseCondensed(id=123, name="Test Course", platformId="platform_123")
        return FolderItem(session=session, parent=None, course=course, name="Documents", browse_url="/Documents/Index/Index/courseID/123/ssID/platform_123")

    def test_folder_initialization(self, sample_folder):
        """Test folder is properly initialized."""
        assert sample_folder.name == "Documents"
        assert sample_folder.course.name == "Test Course"
        assert "/Documents/Index/Index/courseID/123/ssID/platform_123" in sample_folder.browse_url

    def test_folder_default_browse_url(self, session):
        """Test folder generates default browse URL when none provided."""
        course = CourseCondensed(id=456, name="Another Course", platformId="platform_456")
        folder = FolderItem(session=session, parent=None, course=course, name="Assignments")

        expected_url = "/Documents/Index/Index/courseID/456/ssID/platform_456"
        assert folder.browse_url == expected_url

    def test_folder_with_parent(self, session):
        """Test folder with parent relationship."""
        course = CourseCondensed(id=123, name="Test Course", platformId="platform_123")
        parent_folder = FolderItem(session=session, parent=None, course=course, name="Root")
        child_folder = FolderItem(session=session, parent=parent_folder, course=course, name="Subfolder", browse_url="/Documents/subfolder")

        assert child_folder.parent == parent_folder
        assert child_folder.name == "Subfolder"
        assert child_folder.course == course

    def test_folder_items_property_exists(self, sample_folder):
        """Test that items property exists and is callable."""
        assert hasattr(sample_folder, "items")
        assert callable(sample_folder.items)

    def test_folder_nested_structure(self, session):
        """Test creating nested folder structure."""
        course = CourseCondensed(id=789, name="Math Course", platformId="platform_789")

        root_folder = FolderItem(session=session, parent=None, course=course, name="Math Materials")
        chapter1_folder = FolderItem(session=session, parent=root_folder, course=course, name="Chapter 1")
        exercises_folder = FolderItem(session=session, parent=chapter1_folder, course=course, name="Exercises")

        assert exercises_folder.parent == chapter1_folder
        assert chapter1_folder.parent == root_folder
        assert root_folder.parent is None

        assert exercises_folder.course == course
        assert chapter1_folder.course == course
        assert root_folder.course == course

    def test_folder_url_construction_with_special_ids(self, session):
        """Test URL construction with different ID formats."""
        course = CourseCondensed(id=999, name="Special Course", platformId="special_platform_999")
        folder = FolderItem(session=session, parent=None, course=course, name="Special Folder")

        expected_url = "/Documents/Index/Index/courseID/999/ssID/special_platform_999"
        assert folder.browse_url == expected_url
