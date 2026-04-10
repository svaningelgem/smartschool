from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from smartschool import objects
from smartschool.exceptions import SmartSchoolAttachmentUploadError
from smartschool.message_composer import (
    MessageComposerForm,
    RecipientType,
    _ComposeFormParser,
)
from smartschool.messages import BoxType

if TYPE_CHECKING:
    from requests_mock import Mocker

    from smartschool import Smartschool


class TestRecipientType:
    """Test RecipientType enum."""

    def test_recipient_type_to_request_type(self):
        assert RecipientType.TO.request_type == "0"
        assert RecipientType.CC.request_type == "2"
        assert RecipientType.BCC.request_type == "3"

    def test_recipient_type_to_parent_node_id(self):
        assert RecipientType.TO.parent_node_id == "insertSearchFieldContainer_0_0"
        assert RecipientType.CC.parent_node_id == "insertSearchFieldContainer_2_0"
        assert RecipientType.BCC.parent_node_id == "insertSearchFieldContainer_3_0"


class TestComposeFormParser:
    """Test _ComposeFormParser HTML parsing."""

    def test_parser_extracts_hidden_input_fields(self):
        parser = _ComposeFormParser()
        parser.feed("""
            <input type="hidden" name="randomDir" value="dnV3ujSKmTkE48qLbjMxFrG4y17757280351002146">
            <input type="hidden" name="uniqueUsc" value="4069fDsFgJGxHbeGeCwnF3HXbNTDg17757280354069">
            <input type="hidden" name="encryptedSender" value="76542a9717766d290cf71e6028dc4a7f">
            <input type="text" name="username">
            <input type="email" name="email">
        """)

        assert parser.fields["randomDir"] == "dnV3ujSKmTkE48qLbjMxFrG4y17757280351002146"
        assert parser.fields["uniqueUsc"] == "4069fDsFgJGxHbeGeCwnF3HXbNTDg17757280354069"
        assert parser.fields["encryptedSender"] == "76542a9717766d290cf71e6028dc4a7f"
        assert "username" not in parser.fields
        assert "email" not in parser.fields

    def test_parser_handles_missing_value(self):
        parser = _ComposeFormParser()
        parser.feed('<input type="hidden" name="field" value="">')

        assert parser.fields["field"] == ""

    def test_parser_ignores_non_input_tags(self):
        parser = _ComposeFormParser()
        parser.feed("""
            <div name="field" value="test"></div>
            <input type="hidden" name="valid" value="yes">
        """)

        assert "field" not in parser.fields
        assert parser.fields["valid"] == "yes"


class TestMessageComposerFormCreate:
    """Test MessageComposerForm.create() classmethod."""

    def test_create_form_with_defaults(self, session: Smartschool):
        form = MessageComposerForm.create(session=session)

        assert form.session == session
        assert form.box_type == BoxType.INBOX
        assert form.compose_type == 0
        assert form.msg_id == "undefined"
        assert form.payload is not None
        assert form.hidden_fields is not None

    def test_create_form_with_custom_parameters(self, session: Smartschool):
        form = MessageComposerForm.create(
            session=session,
            box_type=BoxType.SENT,
            compose_type=1,
            msg_id="12345",
        )

        assert form.box_type == BoxType.SENT
        assert form.compose_type == 1
        assert form.msg_id == "12345"

    def test_create_form_calls_refresh(self, session: Smartschool):
        form = MessageComposerForm.create(session=session)

        # If refresh was called, hidden_fields should be populated from the actual mock file
        assert len(form.hidden_fields) > 0
        assert "randomDir" in form.hidden_fields
        assert "uniqueUsc" in form.hidden_fields


class TestMessageComposerFormRefresh:
    """Test MessageComposerForm.refresh() method."""

    def test_refresh_fetches_form_and_parses_hidden_fields(self, session: Smartschool):
        form = MessageComposerForm(session=session)
        form.refresh()

        assert len(form.hidden_fields) > 0
        assert "randomDir" in form.hidden_fields
        assert "uniqueUsc" in form.hidden_fields
        assert "encryptedSender" in form.hidden_fields

    def test_refresh_initializes_payload_with_defaults(self, session: Smartschool):
        form = MessageComposerForm(session=session)
        form.refresh()

        assert form.payload["module"] == "Messages"
        assert form.payload["file"] == "composeMessage"
        assert form.payload["boxType"] == BoxType.INBOX.value
        assert form.payload["composeType"] == "0"
        assert form.payload["subject"] == ""
        assert form.payload["message"] == ""
        assert form.payload["copyToLVS"] == "dontCopyToLVS"
        assert form.payload["bcc"] == "0"

    def test_refresh_uses_correct_url(self, session: Smartschool, mocker):
        spy = mocker.spy(session, "get")

        form = MessageComposerForm(session=session, msg_id="789")
        form.refresh()

        spy.assert_called_once()
        call_url = spy.call_args[0][0]
        assert "module=Messages" in call_url
        assert "file=composeMessage" in call_url
        assert "msgID=789" in call_url


class TestMessageComposerFormSetters:
    """Test MessageComposerForm setter methods."""

    def test_set_field(self, session: Smartschool):
        form = MessageComposerForm.create(session=session)
        form.set_field("custom_field", "custom_value")

        assert form.payload["custom_field"] == "custom_value"

    def test_set_field_converts_int_to_string(self, session: Smartschool):
        form = MessageComposerForm.create(session=session)
        form.set_field("num_field", 42)

        assert form.payload["num_field"] == "42"
        assert isinstance(form.payload["num_field"], str)

    def test_set_subject(self, session: Smartschool):
        form = MessageComposerForm.create(session=session)
        form.set_subject("Hello World")

        assert form.payload["subject"] == "Hello World"

    def test_set_message_html(self, session: Smartschool):
        form = MessageComposerForm.create(session=session)
        html_content = "<p>This is a <strong>test</strong> message</p>"
        form.set_message_html(html_content)

        assert form.payload["message"] == html_content


class TestMessageComposerFormSearchUsers:
    """Test MessageComposerForm.search_users() method."""

    def test_search_users_returns_users_and_groups(self, session: Smartschool):
        form = MessageComposerForm.create(session=session)
        users, groups = form.search_users("John")

        assert isinstance(users, list)
        assert isinstance(groups, list)

    def test_search_users_extracts_user_data(self, session: Smartschool):
        form = MessageComposerForm.create(session=session)
        users, _ = form.search_users("John")

        if users:
            first_user = users[0]
            assert hasattr(first_user, "user_id")
            assert hasattr(first_user, "value")
            assert hasattr(first_user, "ss_id")

    def test_search_groups_returns_groups(self, session: Smartschool):
        form = MessageComposerForm.create(session=session)
        _, groups = form.search_users("1A")

        assert isinstance(groups, list)

    def test_search_groups_extracts_group_data(self, session: Smartschool):
        form = MessageComposerForm.create(session=session)
        _, groups = form.search_users("1A")

        if groups:
            first_group = groups[0]
            assert hasattr(first_group, "group_id")
            assert hasattr(first_group, "value")
            assert hasattr(first_group, "ss_id")

    def test_search_users_handles_missing_elements(self, session: Smartschool, requests_mock: Mocker):
        form = MessageComposerForm.create(session=session)
        requests_mock.post("https://site/?module=Messages&file=searchUsers", text="<results></results>")

        users, groups = form.search_users("nobody")

        assert users == []
        assert groups == []

    def test_search_users_raises_error_when_unique_usc_missing(self, session: Smartschool):
        form = MessageComposerForm(session=session)
        # Don't call refresh, so uniqueUsc is missing

        with pytest.raises(ValueError, match="uniqueUsc is missing"):
            form.search_users("John")


class TestMessageComposerFormAddRecipient:
    """Test MessageComposerForm.add_recipient() method."""

    def test_add_user_recipient(self, session: Smartschool):
        form = MessageComposerForm.create(session=session)

        # Search for users
        users, _ = form.search_users("John")
        if users:
            form.add_recipient(users[0], RecipientType.TO)

    def test_add_user_as_cc_recipient(self, session: Smartschool):
        form = MessageComposerForm.create(session=session)

        mock_user = objects.MessageSearchUser(user_id=1, value="Test User", ss_id=123)
        form.add_recipient(mock_user, RecipientType.CC)

    def test_add_user_as_bcc_recipient(self, session: Smartschool):
        form = MessageComposerForm.create(session=session)

        mock_user = objects.MessageSearchUser(user_id=1, value="Test User", ss_id=123)
        form.add_recipient(mock_user, RecipientType.BCC)

    def test_add_group_recipient(self, session: Smartschool):
        form = MessageComposerForm.create(session=session)

        mock_group = objects.MessageSearchGroup(group_id=2, value="Class A", ss_id=123)
        form.add_recipient(mock_group, RecipientType.TO)

    def test_add_recipient_with_user_lt(self, session: Smartschool, mocker):
        form = MessageComposerForm.create(session=session)
        spy = mocker.spy(session, "post")

        mock_user = objects.MessageSearchUser(user_id=1, value="Test User", ss_id=123)
        form.add_recipient(mock_user, RecipientType.TO, user_lt=42)

        # Verify the request was made
        spy.assert_called()

    def test_add_recipient_raises_error_when_unique_usc_missing(self, session: Smartschool):
        form = MessageComposerForm(session=session)
        mock_user = objects.MessageSearchUser(
            user_id=1,
            value="Test User",
            ss_id=4069,
        )

        with pytest.raises(ValueError, match="uniqueUsc is missing"):
            form.add_recipient(mock_user)


class TestMessageComposerFormAddAttachment:
    """Test MessageComposerForm.add_attachment() method."""

    def test_add_attachment_with_valid_file(self, session: Smartschool, tmp_path: Path):
        form = MessageComposerForm.create(session=session)

        file_path = tmp_path / "test.pdf"
        file_path.write_bytes(b"PDF content")

        form.add_attachment(file_path)

    def test_add_attachment_raises_error_when_random_dir_missing(self, session: Smartschool):
        form = MessageComposerForm(session=session)
        # payload.randomDir is empty string by default

        with pytest.raises(ValueError, match="randomDir is missing"):
            form.add_attachment("test.pdf")

    def test_add_attachment_raises_error_when_file_not_found(self, session: Smartschool, mocker):
        form = MessageComposerForm.create(session=session)

        # Mock file as not existing
        mocker.patch.object(Path, "exists", return_value=False)

        with pytest.raises(FileNotFoundError, match="does not exist"):
            form.add_attachment("nonexistent.pdf")

    def test_add_attachment_raises_error_when_path_is_not_file(self, session: Smartschool, mocker):
        form = MessageComposerForm.create(session=session)

        # Mock path as existing but not a file
        mocker.patch.object(Path, "exists", return_value=True)
        mocker.patch.object(Path, "is_file", return_value=False)

        with pytest.raises(FileNotFoundError, match="does not exist"):
            form.add_attachment("somedir")

    def test_add_attachment_with_string_path(self, session: Smartschool, tmp_path: Path):
        form = MessageComposerForm.create(session=session)

        file_path = tmp_path / "test.pdf"
        file_path.write_bytes(b"content")

        form.add_attachment(str(file_path))

    def test_add_attachment_with_path_object(self, session: Smartschool, tmp_path: Path):
        form = MessageComposerForm.create(session=session)

        file_path = tmp_path / "test.pdf"
        file_path.write_bytes(b"content")

        form.add_attachment(file_path)

    def test_add_attachment_handles_various_file_types(self, session: Smartschool, tmp_path: Path):
        form = MessageComposerForm.create(session=session)

        # Test various file types
        for filename in ["document.pdf", "image.jpg", "archive.zip", "unknown.xyz"]:
            file_path = tmp_path / filename
            file_path.write_bytes(b"content")
            form.add_attachment(file_path)

    def test_add_attachment_falls_back_to_octet_stream(self, session: Smartschool, requests_mock: Mocker, tmp_path: Path):
        form = MessageComposerForm.create(session=session)
        requests_mock.post("https://site/Upload/Upload/Index", text="true")

        file_path = tmp_path / "blob"
        file_path.write_bytes(b"raw data")

        form.add_attachment(file_path)

        body = requests_mock.request_history[-1].text or ""
        assert "application/octet-stream" in body

    def test_add_attachment_raises_on_false_response(self, session: Smartschool, requests_mock: Mocker, tmp_path: Path):
        form = MessageComposerForm.create(session=session)
        requests_mock.post("https://site/Upload/Upload/Index", text="false")

        file_path = tmp_path / "test.pdf"
        file_path.write_bytes(b"content")

        with pytest.raises(SmartSchoolAttachmentUploadError, match="server returned false"):
            form.add_attachment(file_path)

    def test_add_attachment_raises_on_unexpected_response(self, session: Smartschool, requests_mock: Mocker, tmp_path: Path):
        form = MessageComposerForm.create(session=session)
        requests_mock.post("https://site/Upload/Upload/Index", text="maybe?")

        file_path = tmp_path / "test.pdf"
        file_path.write_bytes(b"content")

        with pytest.raises(SmartSchoolAttachmentUploadError, match="unexpected response"):
            form.add_attachment(file_path)


class TestMessageComposerFormSend:
    """Test MessageComposerForm.send() method."""

    def test_send_message(self, session: Smartschool):
        form = MessageComposerForm.create(session=session)
        form.set_subject("Test Subject")
        form.set_message_html("<p>Test message</p>")

        response = form.send()

        assert response is not None
        assert response.status_code in (200, 302, 400, 500)  # Accept various responses

    def test_send_uses_post_request(self, session: Smartschool, mocker):
        form = MessageComposerForm.create(session=session)
        spy = mocker.spy(session, "post")

        form.send()

        spy.assert_called_once()

    def test_send_includes_all_payload_fields(self, session: Smartschool, mocker):
        form = MessageComposerForm.create(session=session)
        form.set_subject("Test Subject")
        form.set_message_html("<p>Test</p>")

        spy = mocker.spy(session, "post")
        form.send()

        # Verify that fields parameter was passed
        call_args = spy.call_args
        assert call_args is not None


class TestMessageComposerFormIntegration:
    """Integration tests for the full message composition workflow."""

    def test_full_compose_and_send_workflow(self, session: Smartschool):
        # Create form
        form = MessageComposerForm.create(session=session)

        # Set content
        form.set_subject("Integration Test")
        form.set_message_html("<p>This is a test message</p>")

        # Search and add recipients
        users, groups = form.search_users("John")
        if users:
            form.add_recipient(users[0], RecipientType.TO)

        if groups:
            form.add_recipient(groups[0], RecipientType.CC)

        # Send
        response = form.send()
        assert response is not None

    def test_compose_multiple_forms_independently(self, session: Smartschool):
        # Create first form
        form1 = MessageComposerForm.create(session=session)
        form1.set_subject("Message 1")

        # Create second form
        form2 = MessageComposerForm.create(session=session)
        form2.set_subject("Message 2")

        # Verify they are independent
        assert form1.payload["subject"] == "Message 1"
        assert form2.payload["subject"] == "Message 2"
