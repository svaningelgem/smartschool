from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from smartschool import MyDocs, MyDocsFile, MyDocsFolder
from smartschool._exceptions import SmartSchoolAttachmentUploadError

if TYPE_CHECKING:
    from smartschool import Smartschool


@pytest.fixture
def mydocs(session: Smartschool) -> MyDocs:
    return MyDocs(session=session)


def test_mydocs_basic_properties(mydocs: MyDocs):
    assert mydocs.name == "mydocs"
    assert mydocs.parent is None
    assert mydocs.id == ""


def test_mydocs_items(mydocs: MyDocs):
    items = mydocs.items
    assert len(items) == 3
    # Folders first (natural-sorted), then files.
    assert isinstance(items[0], MyDocsFolder)
    assert items[0].name == "Documenten"
    assert items[0].id == "f0000000-0000-4000-8000-000000000001"
    assert items[0].color == "yellow"
    assert isinstance(items[1], MyDocsFolder)
    assert items[1].name == "Examens"
    assert isinstance(items[2], MyDocsFile)
    assert items[2].name == "welkom.docx"


def test_mydocs_iter(mydocs: MyDocs):
    assert [item.name for item in mydocs] == ["Documenten", "Examens", "welkom.docx"]


def test_folder_parent_reference(mydocs: MyDocs):
    assert mydocs.items[0].parent is mydocs


def test_subfolder_items(mydocs: MyDocs):
    documenten = mydocs.items[0]
    assert isinstance(documenten, MyDocsFolder)

    sub_items = documenten.items
    assert len(sub_items) == 2
    assert isinstance(sub_items[0], MyDocsFolder)
    assert sub_items[0].name == "Archief"
    assert isinstance(sub_items[1], MyDocsFile)
    assert sub_items[1].name == "info.pdf"
    assert sub_items[1].parent is documenten


def test_empty_folder(mydocs: MyDocs):
    examens = mydocs.items[1]
    assert isinstance(examens, MyDocsFolder)
    assert examens.items == []
    assert list(examens) == []


def test_file_properties(mydocs: MyDocs):
    file = mydocs.items[2]
    assert isinstance(file, MyDocsFile)
    assert file.filename == "welkom.docx"
    assert file.size == 1234
    assert file.revision_id == "b0000000-0000-4000-8000-000000000001"
    assert file.parent is mydocs


def test_file_download_bytes(mydocs: MyDocs):
    content = mydocs.items[2].download()
    assert isinstance(content, bytes)
    assert b"test file content" in content


def test_file_download_to_file(mydocs: MyDocs, tmp_path):
    target = tmp_path / "downloaded.docx"
    result = mydocs.items[2].download(target, overwrite=True)
    assert result.exists()
    assert b"test file content" in result.read_bytes()


def test_file_download_to_dir(mydocs: MyDocs, tmp_path):
    result = mydocs.items[2].download_to_dir(tmp_path)
    assert result.exists()
    assert result.name == "welkom.docx"


def test_create_folder(mydocs: MyDocs, requests_mock):
    folder = mydocs.create_folder("Homework")
    assert isinstance(folder, MyDocsFolder)
    assert folder.name == "Homework"
    assert folder.id == "f0000000-0000-4000-8000-000000000077"
    assert folder.color == "blue"
    assert folder.parent is mydocs

    last = requests_mock.request_history[-1]
    assert last.method == "POST"
    assert last.path == "/mydoc/api/v1/folders/"
    assert last.json() == {"name": "Homework", "color": "blue", "parentId": ""}


def test_upload(mydocs: MyDocs, tmp_path):
    to_upload = tmp_path / "report.txt"
    to_upload.write_text("the quick brown fox")

    documenten = mydocs.items[0]
    uploaded = documenten.upload(to_upload)

    assert isinstance(uploaded, MyDocsFile)
    assert uploaded.name == "report.txt"
    assert uploaded.size == 19
    assert uploaded.revision_id == "b0000000-0000-4000-8000-000000000099"
    assert uploaded.parent is documenten


def test_upload_missing_file(mydocs: MyDocs, tmp_path):
    with pytest.raises(FileNotFoundError):
        mydocs.upload(tmp_path / "does-not-exist.txt")


def test_upload_rejected_by_server(mydocs: MyDocs, tmp_path, requests_mock):
    requests_mock.post("/Upload/Upload/Index", text="false")
    to_upload = tmp_path / "report.txt"
    to_upload.write_text("x")

    with pytest.raises(SmartSchoolAttachmentUploadError):
        mydocs.upload(to_upload)


def test_delete_file(mydocs: MyDocs, requests_mock):
    mydocs.items[2].delete()
    last = requests_mock.request_history[-1]
    assert last.method == "DELETE"
    assert last.path == "/mydoc/api/v1/files/a0000000-0000-4000-8000-000000000001"


def test_delete_folder(mydocs: MyDocs, requests_mock):
    mydocs.items[0].delete()
    last = requests_mock.request_history[-1]
    assert last.method == "DELETE"
    assert last.path == "/mydoc/api/v1/folders/f0000000-0000-4000-8000-000000000001"
