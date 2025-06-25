from datetime import datetime, timedelta, timezone

from smartschool import TopNavCourses
from smartschool.courses import FileItem, FolderItem, InternetShortcut
from smartschool.objects import CourseCondensed


def test_full_file_workflow(session, tmp_path):
    """Test complete workflow from folder to file download."""
    courses = list(TopNavCourses(session))
    course = courses[1]  # AV
    folder = FolderItem(session=session, parent=None, course=course, name="Assignments")

    assert [item.name for item in folder.items] == [
        "thema 1: persoonlijke interesses in kunst",
        "thema 2: sprookjes",
        "thema 3: aan de slag met akkoorden",
        "Thema 4: handkaleidiscoop",
        "Thema 5: videoclip/reclamespot",
    ]

    thema_1 = folder.items[0]  # thema 1: persoonlijke interesses in kunst
    assert len(thema_1.items) == 4

    # file without a '.' in the name
    pdf_file = thema_1.items[1]  # "Evaluatieblad persoonlijke interesse in kunst"

    assert pdf_file.name == "Evaluatieblad persoonlijke interesse in kunst"
    assert pdf_file.filename == "Evaluatieblad persoonlijke interesse in kunst.pdf"
    assert pdf_file.mime_type == "pdf"
    assert pdf_file.id == 461338
    assert pdf_file.size_kb == 75.54
    assert pdf_file.download_url == "/Documents/Download/Index/htm/0/courseID/4496/docID/461338/ssID/49"
    assert pdf_file.view_url == "/Documents/Wopi/Index/docID/461338/courseID/4496/mode/view/ssID/49"
    assert pdf_file.last_modified == datetime(2024, 10, 8, 12, 45, tzinfo=timezone(timedelta(hours=2)))
    assert pdf_file.parent.name == "thema 1: persoonlijke interesses in kunst"
    assert pdf_file.session is session

    downloaded_file = pdf_file.download_to_dir(tmp_path)
    assert downloaded_file.exists()
    assert downloaded_file.read_bytes()[:8] == b"%PDF-1.3"

    # file with a "." in the name:
    pptx_file = thema_1.items[3]
    assert pptx_file.name == "Persoonlijke kunstinteresse.pptx"
    assert pptx_file.filename == "Persoonlijke kunstinteresse.pptx"


def test_full_shortcut_workflow(session, tmp_path):
    """Test complete workflow from folder to shortcut download."""
    course = CourseCondensed(id=456, name="Science_2024", platformId="platform_456")

    folder = FolderItem(session=session, parent=None, course=course, name="Links")

    shortcut = InternetShortcut(
        session=session,
        parent=folder,
        id=2,
        name="Wikipedia",
        mime_type="url",
        size_kb="1",
        last_modified="2024-01-15 10:30:00",
        link="https://en.wikipedia.org",
    )

    result_path = shortcut.download_to_dir(tmp_path)

    assert result_path == tmp_path / "Wikipedia.url"
    assert result_path.exists()

    content = result_path.read_text(encoding="utf8")
    assert "URL=https://en.wikipedia.org" in content


def test_nested_folder_structure_with_files(session, tmp_path):
    """Test nested folder structure with mixed content types."""
    course = CourseCondensed(id=789, name="History_2024", platformId="platform_789")

    root_folder = FolderItem(session=session, parent=None, course=course, name="Course Materials")
    chapter_folder = FolderItem(session=session, parent=root_folder, course=course, name="Chapter 1")

    pdf_file = FileItem(
        session=session,
        parent=chapter_folder,
        id=1,
        name="chapter1_notes.pdf",
        mime_type="pdf",
        size_kb="500",
        last_modified="2024-01-15 10:30:00",
        download_url="/download/chapter1_notes.pdf",
    )

    video_link = InternetShortcut(
        session=session,
        parent=chapter_folder,
        id=2,
        name="Lecture Video",
        mime_type="url",
        size_kb="1",
        last_modified="2024-01-15 11:00:00",
        link="https://youtube.com/watch?v=example",
    )

    chapter_dir = tmp_path / "chapter1"
    chapter_dir.mkdir()

    pdf_path = pdf_file.download_to_dir(chapter_dir)
    shortcut_path = video_link.download_to_dir(chapter_dir)

    assert pdf_path == chapter_dir / "chapter1_notes.pdf"
    assert shortcut_path == chapter_dir / "Lecture_Video.url"
    assert pdf_path.exists()
    assert shortcut_path.exists()

    shortcut_content = shortcut_path.read_text(encoding="utf8")
    assert "URL=https://youtube.com/watch?v=example" in shortcut_content


def test_file_types_and_extensions(session):
    """Test various file types get correct extensions."""
    course = CourseCondensed(id=100, name="Mixed_Course", platformId="platform_100")
    folder = FolderItem(session=session, parent=None, course=course, name="Files")

    file_types = [
        ("document", "docx", "document.docx"),
        ("spreadsheet", "xlsx", "spreadsheet.xlsx"),
        ("presentation", "pptx", "presentation.pptx"),
        ("video_file", "mp4", "video_file.mp4"),
        ("image", "jpg", "image.jpg"),
        ("archive", "zip", "archive.zip"),
        ("text_file", "txt", "text_file.txt"),
    ]

    for name, mime_type, expected_filename in file_types:
        file_item = FileItem(session=session, parent=folder, id=1, name=name, mime_type=mime_type, size_kb="100", last_modified="2024-01-15 10:30:00")
        assert file_item.filename == expected_filename


def test_overwrite_behavior_consistency(session, tmp_path):
    """Test overwrite behavior across file types."""
    course = CourseCondensed(id=200, name="Test_Course", platformId="platform_200")
    folder = FolderItem(session=session, parent=None, course=course, name="Test_Folder")

    existing_file = tmp_path / "existing.pdf"
    existing_file.write_bytes(b"original content")

    existing_shortcut = tmp_path / "existing.url"
    existing_shortcut.write_text("[InternetShortcut]\r\nURL=https://original.com", encoding="utf8")

    pdf_file = FileItem(
        session=session,
        parent=folder,
        id=1,
        name="existing.pdf",
        mime_type="pdf",
        size_kb="100",
        last_modified="2024-01-15 10:30:00",
        download_url="/download/existing.pdf",
    )

    shortcut = InternetShortcut(
        session=session, parent=folder, id=2, name="existing", mime_type="url", size_kb="1", last_modified="2024-01-15 10:30:00", link="https://new.com"
    )

    pdf_result = pdf_file.download(existing_file, overwrite=False)
    shortcut_result = shortcut.download(existing_shortcut, overwrite=False)

    assert pdf_result == existing_file
    assert shortcut_result == existing_shortcut
    assert existing_file.read_bytes() == b"original content"
    assert "https://original.com" in existing_shortcut.read_text(encoding="utf8")
