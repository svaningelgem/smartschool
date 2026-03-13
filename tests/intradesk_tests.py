from __future__ import annotations

import pytest
from requests import RequestException

from smartschool import Smartschool
from smartschool.courses import FileItem, InternetShortcut
from smartschool.exceptions import SmartSchoolException, SmartSchoolParsingError
from smartschool.intradesk import Intradesk, IntradeskDocumentOrFolder, IntradeskFolder


@pytest.fixture(autouse=True)
def _dont_autosave_intradesk(mocker):
    mocker.patch("smartschool.intradesk.save_test_response")


@pytest.fixture
def folder(session: Smartschool) -> IntradeskFolder:
    return IntradeskFolder(
        session=session,
        parent=None,
        platform_id=49,
        name="(Root)",
    )


@pytest.fixture
def subfolder(session: Smartschool, folder: IntradeskFolder) -> IntradeskFolder:
    return IntradeskFolder(
        session=session,
        parent=folder,
        platform_id=49,
        name="My Folder",
        browse_url="/Intradesk/Index/Index/ssID/49/parentID/100",
    )


# --- IntradeskFolder tests ---


class TestIntradeskFolderPostInit:
    def test_default_browse_url_when_none(self, session: Smartschool):
        """When browse_url is None, it should be set from platform_id."""
        f = IntradeskFolder(session=session, parent=None, platform_id=49, name="root")
        assert f.browse_url == "/Intradesk/Index/Index/ssID/49"

    def test_explicit_browse_url_is_preserved(self, session: Smartschool):
        """When browse_url is provided, it should not be overwritten."""
        f = IntradeskFolder(session=session, parent=None, platform_id=49, name="sub", browse_url="/custom/url")
        assert f.browse_url == "/custom/url"


class TestGetFolderHtml:
    def test_success(self, folder: IntradeskFolder):
        """Should return BeautifulSoup on successful response."""
        soup = folder._get_folder_html()
        assert soup is not None

    def test_exception_is_wrapped(self, folder: IntradeskFolder, mocker):
        """Network error should be wrapped in SmartSchoolException."""
        mocker.patch.object(folder.session, "get", side_effect=RequestException("Network error"))

        with pytest.raises(SmartSchoolException, match="Failed to fetch folder HTML: Network error"):
            folder._get_folder_html()


class TestGetMimeFromRowImage:
    def test_returns_mime_type(self, folder: IntradeskFolder, mocker):
        """Should extract MIME type from background-image URL."""
        mock_row = mocker.Mock()
        mock_div = mocker.Mock()
        mock_div.get.return_value = "background-image:url('/smsc/img/mime_pdf/mime_pdf_32x32.png')"
        mock_row.select_one.return_value = mock_div

        result = folder._get_mime_from_row_image(mock_row)
        assert result == "pdf"

    def test_returns_none_when_no_background_image(self, folder: IntradeskFolder, mocker):
        """Should return None when no background-image is found."""
        mock_row = mocker.Mock()
        mock_div = mocker.Mock()
        mock_div.get.return_value = "color: red; font-size: 12px"
        mock_row.select_one.return_value = mock_div

        result = folder._get_mime_from_row_image(mock_row)
        assert result is None

    def test_skips_empty_entries(self, folder: IntradeskFolder, mocker):
        """Should skip empty CSS entries and still find background-image."""
        mock_row = mocker.Mock()
        mock_div = mocker.Mock()
        mock_div.get.return_value = "  ;  ; background-image:url('/smsc/img/mime_html/mime_html_32x32.png')"
        mock_row.select_one.return_value = mock_div

        result = folder._get_mime_from_row_image(mock_row)
        assert result == "html"


class TestExtractUrlFromOnclick:
    def test_extracts_url_with_single_quotes(self, folder: IntradeskFolder):
        result = folder._extract_url_from_onclick("window.open('/some/url')")
        assert result == "/some/url"

    def test_extracts_url_with_double_quotes(self, folder: IntradeskFolder):
        result = folder._extract_url_from_onclick('window.open("/some/url")')
        assert result == "/some/url"

    def test_returns_none_when_no_match(self, folder: IntradeskFolder):
        result = folder._extract_url_from_onclick("alert('hello')")
        assert result is None


class TestFigureOutItemLinks:
    def test_download_link_class(self, folder: IntradeskFolder, mocker):
        """Should detect download-link class."""
        mock_row = mocker.Mock()
        mock_link = mocker.Mock()
        mock_link.get.side_effect = lambda k, default=None: {
            "class": ["download-link"],
            "href": "/dl/url",
        }.get(k, default)
        mock_row.select.return_value = [mock_link]

        dl, view, onclick = folder._figure_out_item_links(mock_row)
        assert dl == "/dl/url"
        assert view is None
        assert onclick is None

    def test_smsc_download_icon_class(self, folder: IntradeskFolder, mocker):
        """Should detect smsc-download__icon class."""
        mock_row = mocker.Mock()
        mock_link = mocker.Mock()
        mock_link.get.side_effect = lambda k, default=None: {
            "class": ["smsc-download__icon"],
            "href": "/dl/icon",
        }.get(k, default)
        mock_row.select.return_value = [mock_link]

        dl, view, onclick = folder._figure_out_item_links(mock_row)
        assert dl == "/dl/icon"

    def test_smsc_download_link_class(self, folder: IntradeskFolder, mocker):
        """Should detect smsc-download__link class."""
        mock_row = mocker.Mock()
        mock_link = mocker.Mock()
        mock_link.get.side_effect = lambda k, default=None: {
            "class": ["smsc-download__link"],
            "href": "/view/url",
        }.get(k, default)
        mock_row.select.return_value = [mock_link]

        dl, view, onclick = folder._figure_out_item_links(mock_row)
        assert view == "/view/url"

    def test_smsc_cm_link_with_onclick(self, folder: IntradeskFolder, mocker):
        """Should detect smsc_cm_link with onclick and extract URL."""
        mock_row = mocker.Mock()
        mock_link = mocker.Mock()
        mock_link.get.side_effect = lambda k, default=None: {
            "class": ["smsc_cm_link"],
            "href": None,
            "onclick": "window.open('/onclick/url')",
        }.get(k, default)
        mock_row.select.return_value = [mock_link]

        dl, view, onclick = folder._figure_out_item_links(mock_row)
        assert onclick == "/onclick/url"

    def test_smsc_cm_link_without_onclick(self, folder: IntradeskFolder, mocker):
        """smsc_cm_link without onclick should not set onclick_link."""
        mock_row = mocker.Mock()
        mock_link = mocker.Mock()
        mock_link.get.side_effect = lambda k, default=None: {
            "class": ["smsc_cm_link"],
            "href": "/some/url",
            "onclick": None,
        }.get(k, default)
        mock_row.select.return_value = [mock_link]

        dl, view, onclick = folder._figure_out_item_links(mock_row)
        assert dl is None
        assert view is None
        assert onclick is None

    def test_no_known_class(self, folder: IntradeskFolder, mocker):
        """Links with unknown classes should not set any link."""
        mock_row = mocker.Mock()
        mock_link = mocker.Mock()
        mock_link.get.side_effect = lambda k, default=None: {
            "class": ["unknown-class"],
            "href": "/url",
            "onclick": None,
        }.get(k, default)
        mock_row.select.return_value = [mock_link]

        dl, view, onclick = folder._figure_out_item_links(mock_row)
        assert dl is None
        assert view is None
        assert onclick is None


class TestParseDocumentRow:
    def test_regular_file(self, folder: IntradeskFolder):
        """Test parsing a regular file row."""
        item = folder.items[1]
        assert isinstance(item, FileItem)
        assert item.name == "My Document"
        assert item.mime_type == "pdf"
        assert item.id == 200
        assert item.download_url == "/Intradesk/Download/Index/docID/200/ssID/49"

    def test_inline_anchor_link(self, subfolder: IntradeskFolder):
        """Test parsing a row with an inline <a> link (internet shortcut)."""
        item = subfolder.items[0]
        assert isinstance(item, InternetShortcut)
        assert item.name == "My Link"
        assert item.link == "https://www.example.com"
        assert item.id == 0

    def test_inline_iframe_link(self, subfolder: IntradeskFolder):
        """Test parsing a row with an inline <iframe> link."""
        item = subfolder.items[0]
        assert isinstance(item, InternetShortcut)
        assert item.link == "https://www.youtube.com/embed/abc123"

    def test_onclick_link(self, subfolder: IntradeskFolder):
        """Test parsing a row with an onclick internet shortcut."""
        item = subfolder.items[1]
        assert isinstance(item, InternetShortcut)
        assert item.name == "My Onclick Link"
        assert item.link == "/Intradesk/Download/Index/docID/301/ssID/49"
        assert item.id == 301

    def test_no_link_texts_raises(self, folder: IntradeskFolder, mocker):
        """Should raise AssertionError when no link texts are found."""
        mock_row = mocker.Mock()
        mock_row.get.side_effect = lambda k, default=None: {
            "id": "docid_999",
        }.get(k, default)
        mock_row.select_one.return_value.get_text.return_value = "type - 1.00 KB - 01/01/2024 10:00"
        mocker.patch.object(folder, "_get_mime_from_row_image", return_value="pdf")
        mock_row.select.return_value = []  # no links
        mock_row.select.side_effect = lambda sel: (
            []
            if "smsc_cm_body_row_block_mime" not in sel
            else [mocker.Mock(get_text=lambda **kw: "type - 1.00 KB - 01/01/2024 10:00")]
        )

        with pytest.raises(AssertionError, match="Expected exactly one link text"):
            folder._parse_document_row(mock_row)

    def test_unknown_inline_link_type_raises(self, folder: IntradeskFolder, mocker):
        """Should raise AssertionError when inline link type is unknown."""
        mock_row = mocker.Mock()
        mock_row.get.side_effect = lambda k, default=None: {
            "id": "docid_999",
        }.get(k, default)

        mock_mime = mocker.Mock()
        mock_mime.get_text.return_value = "pdf - 1.00 KB - 01/01/2024 10:00"

        mock_link = mocker.Mock()
        mock_link.get_text.return_value = "Some File"

        mock_inline_element = mocker.Mock()
        mock_inline_element.name = "div"  # unknown type
        mock_inline_element.__getitem__ = mocker.Mock(return_value="/url")

        def select_side_effect(sel, **kw):
            if "smsc_cm_body_row_block_mime" in sel:
                return [mock_mime]
            if "inline" in sel:
                return [mock_inline_element]
            return [mock_link]  # links

        mock_row.select_one.return_value = mock_mime
        mock_row.select.side_effect = select_side_effect
        mocker.patch.object(folder, "_get_mime_from_row_image", return_value="pdf")

        with pytest.raises(AssertionError, match="Unknown inline link type"):
            folder._parse_document_row(mock_row)


class TestParseFolderRow:
    def test_parses_folder(self, folder: IntradeskFolder):
        """Test parsing a folder row from mock HTML."""
        item = folder.items[0]
        assert isinstance(item, IntradeskFolder)
        assert item.name == "My Folder"
        assert item.browse_url == "/Intradesk/Index/Index/ssID/49/parentID/100"
        assert item.platform_id == 49
        assert item.parent is folder

    def test_raises_when_no_browse_url(self, folder: IntradeskFolder, mocker):
        """Should raise SmartSchoolParsingError when no smsc_cm_link found."""
        mock_row = mocker.Mock()
        mock_link = mocker.Mock()
        mock_link.get.return_value = ["other_class"]
        mock_row.select.return_value = [mock_link]

        with pytest.raises(SmartSchoolParsingError, match="No browse URL found"):
            folder._parse_folder_row(mock_row)


class TestParseRow:
    def test_dispatches_to_document_for_docid(self, folder: IntradeskFolder, mocker):
        """Should call _parse_document_row for rows with id starting with docid_."""
        mock_row = mocker.Mock()
        mock_row.get.side_effect = lambda k, default=None: {"id": "docid_123"}.get(k, default)
        mock_parse_doc = mocker.patch.object(folder, "_parse_document_row", return_value=mocker.Mock())

        folder._parse_row(mock_row)
        mock_parse_doc.assert_called_once_with(mock_row)

    def test_dispatches_to_folder_for_non_docid(self, folder: IntradeskFolder, mocker):
        """Should call _parse_folder_row for rows without docid_ id."""
        mock_row = mocker.Mock()
        mock_row.get.side_effect = lambda k, default=None: {"id": None}.get(k, default)
        mock_parse_folder = mocker.patch.object(folder, "_parse_folder_row", return_value=mocker.Mock())

        folder._parse_row(mock_row)
        mock_parse_folder.assert_called_once_with(mock_row)


class TestItems:
    def test_items_are_sorted_folders_first(self, folder: IntradeskFolder):
        """Items should be sorted with folders first, then files, alphabetically."""
        items = folder.items
        assert len(items) == 2
        assert isinstance(items[0], IntradeskFolder)
        assert isinstance(items[1], FileItem)

    def test_subfolder_items(self, subfolder: IntradeskFolder):
        """Subfolder items should contain the expected entries."""
        items = subfolder.items
        assert len(items) == 2
        assert all(isinstance(i, InternetShortcut) for i in items)


# --- Intradesk class tests ---


class TestIntradesk:
    def test_platform_id_from_authenticated_user(self, session: Smartschool):
        """Platform ID should be extracted from authenticated user id."""
        intradesk = Intradesk(session=session)
        assert intradesk._platform_id == 49

    def test_root_returns_intradesk_folder(self, session: Smartschool):
        """root property should return an IntradeskFolder for the root."""
        intradesk = Intradesk(session=session)
        root = intradesk.root
        assert isinstance(root, IntradeskFolder)
        assert root.name == "(Root)"
        assert root.browse_url == "/Intradesk/Index/Index/ssID/49"
        assert root.parent is None

    def test_iter_yields_root_items(self, session: Smartschool):
        """Iterating over Intradesk should yield root folder items."""
        intradesk = Intradesk(session=session)
        items = list(intradesk)
        assert len(items) == 2
        assert isinstance(items[0], IntradeskFolder)
        assert items[0].name == "My Folder"
        assert isinstance(items[1], FileItem)
        assert items[1].name == "My Document"
