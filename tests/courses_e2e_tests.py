from datetime import datetime, timedelta, timezone

import pytest

from smartschool import TopNavCourses, Smartschool
from smartschool.courses import FileItem, FolderItem, InternetShortcut
from smartschool.courses import CourseCondensed


@pytest.fixture
def courses(session: Smartschool) -> list[CourseCondensed]:
    """Create a session for testing."""
    return list(TopNavCourses(session))


def test_full_workflow(courses: list[CourseCondensed], tmp_path):
    """Test a complete workflow from folder to file download."""
    items = courses[1].items  # AV

    assert [item.name for item in items] == [
        "thema 1: persoonlijke interesses in kunst",
        "thema 2: sprookjes",
        "thema 3: aan de slag met akkoorden",
        "Thema 4: handkaleidiscoop",
        "Thema 5: videoclip/reclamespot",
    ]

    thema_1 = items[0]  # thema 1: persoonlijke interesses in kunst
    assert isinstance(thema_1, FolderItem)
    assert len(thema_1.items) == 4

    # file without a '.' in the name
    pdf_file = thema_1.items[1]  # "Evaluatieblad persoonlijke interesse in kunst"

    assert pdf_file.name == "Evaluatieblad persoonlijke interesse in kunst"
    assert pdf_file.filename == "Evaluatieblad persoonlijke interesse in kunst.pdf"
    assert pdf_file.mime_type == "pdf"
    assert pdf_file.id == 461338
    assert pdf_file.size_kb == pytest.approx(75.54)
    assert pdf_file.download_url == "/Documents/Download/Index/htm/0/courseID/4496/docID/461338/ssID/49"
    assert pdf_file.view_url == "/Documents/Wopi/Index/docID/461338/courseID/4496/mode/view/ssID/49"
    assert pdf_file.last_modified == datetime(2024, 10, 8, 12, 45, tzinfo=timezone(timedelta(hours=2)))
    assert pdf_file.parent.name == "thema 1: persoonlijke interesses in kunst"

    downloaded_file = pdf_file.download_to_dir(tmp_path)
    assert downloaded_file.exists()
    assert downloaded_file.read_bytes()[:8] == b"%PDF-1.3"

    # file with a "." in the name:
    pptx_file = thema_1.items[3]
    assert pptx_file.name == "Persoonlijke kunstinteresse.pptx"
    assert pptx_file.filename == "Persoonlijke kunstinteresse.pptx"


def test_shortcut_via_window_open_click(courses: list[CourseCondensed], tmp_path):
    shortcut = courses[4].items[1].items[8]  # chemie / oefeningen en verbetersleutels / shortcut
    assert shortcut.name == 'extra oefeningen elektrolyten en ionisatie+dissociatie'
    assert shortcut.filename == 'extra oefeningen elektrolyten en ionisatie_dissociatie.url'
    assert shortcut.mime_type == 'html'
    assert shortcut.size_kb == pytest.approx(487.0)
    assert shortcut.last_modified == datetime(2025, 1, 31, 10, 55, tzinfo=timezone(timedelta(hours=1)))
    assert shortcut.link == 'http://chemieleerkracht.blackbox.website/index.php/elektrolyten/'

    dl_file = shortcut.download_to_dir(tmp_path)
    assert dl_file.exists()
    assert dl_file.read_text().splitlines() == ["[InternetShortcut]", "URL=http://chemieleerkracht.blackbox.website/index.php/elektrolyten/"]

def test_shortcut_via_iframe_src(courses: list[CourseCondensed], tmp_path):
    shortcut = courses[12].items[2].items[0]  # ICT / OneDrive... / shortcut

    assert shortcut.name == 'Hoe je gebruik je OneDrive?'
    assert shortcut.filename == 'Hoe je gebruik je OneDrive.url'
    assert shortcut.mime_type == 'html'
    assert shortcut.size_kb == 1485.0
    assert shortcut.last_modified == datetime(2020, 6, 19, 11, 20, tzinfo=timezone(timedelta(hours=2)))
    assert shortcut.link == 'https://www.youtube.com/embed/Zm-g5PpzsEE'
