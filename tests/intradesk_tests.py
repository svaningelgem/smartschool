from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from smartschool import Intradesk, IntradeskFile, IntradeskFolder

if TYPE_CHECKING:
    from smartschool import Smartschool


@pytest.fixture
def intradesk(session: Smartschool) -> Intradesk:
    return Intradesk(session=session)


def test_intradesk_platform_id(intradesk: Intradesk):
    assert intradesk.platform_id == "49"
    assert intradesk.name == "intradesk"
    assert intradesk.parent is None
    assert intradesk.id == ""


def test_intradesk_items(intradesk: Intradesk):
    items = intradesk.items
    assert len(items) == 3
    # Folders first (sorted), then files
    assert isinstance(items[0], IntradeskFolder)
    assert items[0].name == "Documents"
    assert items[0].id == "100"
    assert isinstance(items[1], IntradeskFolder)
    assert items[1].name == "Photos"
    assert items[1].id == "101"
    assert isinstance(items[2], IntradeskFile)
    assert items[2].name == "readme.txt"
    assert items[2].id == "200"


def test_intradesk_iter(intradesk: Intradesk):
    items = list(intradesk)
    assert len(items) == 3
    assert items[0].name == "Documents"


def test_folder_parent_reference(intradesk: Intradesk):
    folder = intradesk.items[0]
    assert isinstance(folder, IntradeskFolder)
    assert folder.parent is intradesk


def test_subfolder_items(intradesk: Intradesk):
    documents = intradesk.items[0]
    assert isinstance(documents, IntradeskFolder)

    sub_items = documents.items
    assert len(sub_items) == 2
    assert all(isinstance(item, IntradeskFile) for item in sub_items)
    # Sorted by natural sort
    assert sub_items[0].name == "data.xlsx"
    assert sub_items[1].name == "report.pdf"


def test_empty_folder(intradesk: Intradesk):
    photos = intradesk.items[1]
    assert isinstance(photos, IntradeskFolder)
    assert photos.items == []
    assert list(photos) == []


def test_file_filename(intradesk: Intradesk):
    file = intradesk.items[2]
    assert isinstance(file, IntradeskFile)
    assert file.filename == "readme.txt"


def test_file_download_bytes(intradesk: Intradesk):
    file = intradesk.items[2]
    assert isinstance(file, IntradeskFile)
    content = file.download()
    assert isinstance(content, bytes)
    assert b"test file content" in content


def test_file_download_to_file(intradesk: Intradesk, tmp_path):
    file = intradesk.items[2]
    target = tmp_path / "downloaded.txt"
    result = file.download(target, overwrite=False)
    assert result.exists()
    assert b"test file content" in result.read_bytes()


def test_file_download_no_overwrite(intradesk: Intradesk):
    file = intradesk.items[2]
    target = Path("downloaded.txt")
    target.write_text("existing content")

    result = file.download(target, overwrite=False)
    assert result == target.resolve()
    assert target.read_text() == "existing content"


def test_file_download_with_overwrite(intradesk: Intradesk):
    file = intradesk.items[2]
    target = Path("downloaded.txt")
    target.write_text("existing content")

    result = file.download(target, overwrite=True)
    assert result.exists()
    assert b"test file content" in result.read_bytes()


def test_file_download_to_dir(intradesk: Intradesk, tmp_path):
    file = intradesk.items[2]
    result = file.download_to_dir(tmp_path)
    assert result.exists()
    assert result.name == "readme.txt"


def test_file_parent_reference(intradesk: Intradesk):
    file = intradesk.items[2]
    assert isinstance(file, IntradeskFile)
    assert file.parent is intradesk


def test_subfolder_file_parent(intradesk: Intradesk):
    documents = intradesk.items[0]
    sub_file = documents.items[0]
    assert isinstance(sub_file, IntradeskFile)
    assert sub_file.parent is documents


def test_folder_platform_id_propagation(intradesk: Intradesk):
    documents = intradesk.items[0]
    assert isinstance(documents, IntradeskFolder)
    assert documents.platform_id == "49"

    sub_file = documents.items[0]
    assert isinstance(sub_file, IntradeskFile)
    assert sub_file.platform_id == "49"
