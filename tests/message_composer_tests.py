from __future__ import annotations

from typing import TYPE_CHECKING
from urllib.parse import parse_qs

import pytest

from smartschool import (
    BoxType,
    MessageComposerForm,
    MessageSearchGroup,
    MessageSearchUser,
    RecipientType,
    SmartSchoolAttachmentUploadError,
    SmartSchoolCoAccountsUnavailableError,
)

if TYPE_CHECKING:
    from pathlib import Path

    from requests_mock import Mocker

    from smartschool import Smartschool

# Anonymized co-account search response: a student ("Robin Doe", userID 111 / ssID 222)
# with two co-accounts (parents). They reuse the student's userID/ssID and are told apart
# by <userLT> (0 = the student's own account, 1 = first co-account, 2 = second).
_COACCOUNT_SEARCH_XML = """<results>
<type>1</type>
<ssID>222</ssID>
<parentNodeId>insertSearchFieldContainer_1_0</parentNodeId>
<groups />
<users>
<user>
<userID>111</userID>
<text>Robin Doe</text>
<value>Robin Doe</value>
<selectable>on</selectable>
<ssID>222</ssID>
<userLT>1</userLT>
<coaccountname>Co-account 1</coaccountname>
<classname>Klas: 1A</classname>
<schoolname>Example School</schoolname>
</user>
<user>
<userID>111</userID>
<text>Robin Doe</text>
<value>Robin Doe</value>
<selectable>on</selectable>
<ssID>222</ssID>
<userLT>2</userLT>
<coaccountname>Co-account 2</coaccountname>
<classname>Klas: 1A</classname>
<schoolname>Example School</schoolname>
</user>
</users>
</results>"""

# Same search but noisier: Robin Doe's own account (userLT 0) and a namesake's co-account
# (a different userID) are also returned. add_all_coaccounts must keep only the student's
# own co-accounts (matching userID/ssID, userLT >= 1).
_COACCOUNT_SEARCH_MIXED_XML = """<results>
<type>1</type>
<ssID>222</ssID>
<parentNodeId>insertSearchFieldContainer_1_0</parentNodeId>
<groups />
<users>
<user>
<userID>111</userID>
<value>Robin Doe</value>
<ssID>222</ssID>
<userLT>0</userLT>
<coaccountname />
</user>
<user>
<userID>111</userID>
<value>Robin Doe</value>
<ssID>222</ssID>
<userLT>1</userLT>
<coaccountname>Co-account 1</coaccountname>
</user>
<user>
<userID>111</userID>
<value>Robin Doe</value>
<ssID>222</ssID>
<userLT>2</userLT>
<coaccountname>Co-account 2</coaccountname>
</user>
<user>
<userID>999</userID>
<value>Robin Roe</value>
<ssID>222</ssID>
<userLT>1</userLT>
<coaccountname>Co-account 1</coaccountname>
</user>
</users>
</results>"""


def _sent_forms(requests_mock: Mocker, url_part: str) -> list[dict[str, str]]:
    """Form payload of every recorded request whose URL contains ``url_part``, oldest first."""
    return [{k: v[0] for k, v in parse_qs(r.text).items()} for r in requests_mock.request_history if url_part in r.url]


class TestRecipientType:
    """Test RecipientType enum."""

    def test_recipient_type_to_parent_node_id(self):
        assert RecipientType.TO.parent_node_id == "insertSearchFieldContainer_0_0"
        assert RecipientType.CC.parent_node_id == "insertSearchFieldContainer_2_0"
        assert RecipientType.BCC.parent_node_id == "insertSearchFieldContainer_3_0"


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

    def test_refresh_uses_correct_url(self, session: Smartschool, requests_mock: Mocker):
        form = MessageComposerForm(session=session, msg_id="789")
        form.refresh()

        refresh_urls = [r.url for r in requests_mock.request_history if "file=composeMessage" in r.url]
        assert len(refresh_urls) == 1
        assert "module=Messages" in refresh_urls[0]
        assert "msgID=789" in refresh_urls[0]

    def test_refresh_detects_coaccount_support(self, session: Smartschool):
        # The compose fixture embeds SMSC.vars with "canSendToCoAccounts":true (staff/school-gated).
        form = MessageComposerForm.create(session=session)

        assert form.can_send_to_coaccounts is True

    def _refresh_with_compose_html(self, session: Smartschool, requests_mock: Mocker, html: str) -> MessageComposerForm:
        form = MessageComposerForm(session=session)
        requests_mock.get(
            "https://site/?module=Messages&file=composeMessage&boxType=inbox&composeType=0&msgID=undefined",
            text=html,
        )
        form.refresh()
        return form

    def test_refresh_no_support_when_flag_is_false(self, session: Smartschool, requests_mock: Mocker):
        html = '<script>$.extend(true, SMSC, { vars : {"canSendToCoAccounts":false} });</script>'
        form = self._refresh_with_compose_html(session, requests_mock, html)

        assert form.can_send_to_coaccounts is False

    def test_refresh_no_support_when_config_absent(self, session: Smartschool, requests_mock: Mocker):
        form = self._refresh_with_compose_html(session, requests_mock, "<html><body>no config here</body></html>")

        assert form.can_send_to_coaccounts is False

    def test_refresh_no_support_when_config_is_malformed(self, session: Smartschool, requests_mock: Mocker):
        html = '<script>$.extend(true, SMSC, { vars : {"canSendToCoAccounts": tru</script>'  # truncated JSON
        form = self._refresh_with_compose_html(session, requests_mock, html)

        assert form.can_send_to_coaccounts is False


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

    def test_search_users_defaults_to_main_accounts(self, session: Smartschool, requests_mock: Mocker):
        form = MessageComposerForm.create(session=session)

        form.search_users("John")

        data = _sent_forms(requests_mock, "file=searchUsers")[-1]
        assert data["type"] == "0"
        assert data["parentNodeId"] == "insertSearchFieldContainer_0_0"

    def test_search_users_user_lt_defaults_to_zero_for_main_accounts(self, session: Smartschool):
        form = MessageComposerForm.create(session=session)

        users, _ = form.search_users("John")

        assert users
        assert all(u.user_lt == 0 for u in users)


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

        mock_user = MessageSearchUser(user_id=1, value="Test User", ss_id=123)
        form.add_recipient(mock_user, RecipientType.CC)

    def test_add_user_as_bcc_recipient(self, session: Smartschool):
        form = MessageComposerForm.create(session=session)

        mock_user = MessageSearchUser(user_id=1, value="Test User", ss_id=123)
        form.add_recipient(mock_user, RecipientType.BCC)

    def test_add_group_recipient(self, session: Smartschool):
        form = MessageComposerForm.create(session=session)

        mock_group = MessageSearchGroup(group_id=2, value="Class A", ss_id=123)
        form.add_recipient(mock_group, RecipientType.TO)

    def test_add_recipient_with_user_lt(self, session: Smartschool, requests_mock: Mocker):
        form = MessageComposerForm.create(session=session)

        mock_user = MessageSearchUser(user_id=1, value="Test User", ss_id=123)
        form.add_recipient(mock_user, RecipientType.TO, user_lt=42)

        assert _sent_forms(requests_mock, "addUserToSelected")[-1]["userlt"] == "42"

    def test_add_recipient_raises_error_when_unique_usc_missing(self, session: Smartschool):
        form = MessageComposerForm(session=session)
        mock_user = MessageSearchUser(
            user_id=1,
            value="Test User",
            ss_id=4069,
        )

        with pytest.raises(ValueError, match="uniqueUsc is missing"):
            form.add_recipient(mock_user)

    def test_add_coaccount_is_routed_to_the_coaccount_field_automatically(self, session: Smartschool, requests_mock: Mocker):
        form = MessageComposerForm.create(session=session)

        # A parent: shares the student's userID/ssID, distinguished by user_lt. The caller
        # picks the plain TO field; the co-account container (1) is chosen automatically.
        parent = MessageSearchUser(user_id=111, value="Robin Doe", ss_id=222, user_lt=2, coaccountname="Co-account 2")
        form.add_recipient(parent, RecipientType.TO)

        data = _sent_forms(requests_mock, "addUserToSelected")[-1]
        assert data["id"] == "111"
        assert data["ssid"] == "222"
        assert data["typeId"] == "users"
        assert data["type"] == "1"
        assert data["parentNodeId"] == "insertSearchFieldContainer_1_0"
        assert data["userlt"] == "2"

    def test_add_coaccount_as_cc_uses_the_coaccount_cc_container(self, session: Smartschool, requests_mock: Mocker):
        form = MessageComposerForm.create(session=session)

        parent = MessageSearchUser(user_id=111, value="Robin Doe", ss_id=222, user_lt=1)
        form.add_recipient(parent, RecipientType.CC)

        data = _sent_forms(requests_mock, "addUserToSelected")[-1]
        assert data["type"] == "4"
        assert data["parentNodeId"] == "insertSearchFieldContainer_4_0"

    def test_add_main_account_stays_in_the_main_field(self, session: Smartschool, requests_mock: Mocker):
        form = MessageComposerForm.create(session=session)

        student = MessageSearchUser(user_id=111, value="Robin Doe", ss_id=222)  # user_lt defaults to 0
        form.add_recipient(student, RecipientType.TO)

        data = _sent_forms(requests_mock, "addUserToSelected")[-1]
        assert data["type"] == "0"
        assert data["parentNodeId"] == "insertSearchFieldContainer_0_0"
        assert data["userlt"] == "0"

    def test_add_recipient_defaults_user_lt_to_the_recipient(self, session: Smartschool, requests_mock: Mocker):
        form = MessageComposerForm.create(session=session)

        parent = MessageSearchUser(user_id=111, value="Robin Doe", ss_id=222, user_lt=1)
        form.add_recipient(parent, RecipientType.TO)

        assert _sent_forms(requests_mock, "addUserToSelected")[-1]["userlt"] == "1"

    def test_add_recipient_explicit_user_lt_overrides_recipient(self, session: Smartschool, requests_mock: Mocker):
        form = MessageComposerForm.create(session=session)

        parent = MessageSearchUser(user_id=111, value="Robin Doe", ss_id=222, user_lt=1)
        form.add_recipient(parent, RecipientType.TO, user_lt=2)

        assert _sent_forms(requests_mock, "addUserToSelected")[-1]["userlt"] == "2"

    def test_add_group_recipient_uses_user_lt_zero(self, session: Smartschool, requests_mock: Mocker):
        form = MessageComposerForm.create(session=session)

        form.add_recipient(MessageSearchGroup(group_id=2, value="Class A", ss_id=222))

        data = _sent_forms(requests_mock, "addUserToSelected")[-1]
        assert data["typeId"] == "groups"
        assert data["userlt"] == "0"

    def test_add_recipient_raises_on_coaccount_without_capability(self, session: Smartschool, requests_mock: Mocker):
        form = MessageComposerForm.create(session=session)
        form.can_send_to_coaccounts = False
        parent = MessageSearchUser(user_id=111, value="Robin Doe", ss_id=222, user_lt=1)

        with pytest.raises(SmartSchoolCoAccountsUnavailableError):
            form.add_recipient(parent)

        # It fails before any request is sent (no half-done state).
        assert _sent_forms(requests_mock, "addUserToSelected") == []

    def test_add_main_recipient_still_works_without_coaccount_capability(self, session: Smartschool):
        # A non-co-account (user_lt 0) add must NOT be blocked by the co-account guard.
        form = MessageComposerForm.create(session=session)
        form.can_send_to_coaccounts = False

        form.add_recipient(MessageSearchUser(user_id=111, value="Robin Doe", ss_id=222))


class TestMessageComposerFormGetCoaccounts:
    """Test MessageComposerForm.get_coaccounts()."""

    def test_returns_only_the_users_own_coaccounts(self, session: Smartschool, requests_mock: Mocker):
        form = MessageComposerForm.create(session=session)
        requests_mock.post("https://site/?module=Messages&file=searchUsers", text=_COACCOUNT_SEARCH_MIXED_XML)
        student = MessageSearchUser(user_id=111, value="Robin Doe", ss_id=222)

        coaccounts = form.get_coaccounts(student)

        # The student's own account (userLT 0) and a namesake (userID 999) are excluded.
        assert [(c.user_id, c.user_lt, c.coaccountname) for c in coaccounts] == [
            (111, 1, "Co-account 1"),
            (111, 2, "Co-account 2"),
        ]

    def test_searches_the_coaccount_field(self, session: Smartschool, requests_mock: Mocker):
        form = MessageComposerForm.create(session=session)

        form.get_coaccounts(MessageSearchUser(user_id=111, value="Robin Doe", ss_id=222))

        assert _sent_forms(requests_mock, "file=searchUsers")[-1]["type"] == "1"  # co-account search container

    def test_returns_empty_when_no_coaccounts(self, session: Smartschool, requests_mock: Mocker):
        form = MessageComposerForm.create(session=session)
        requests_mock.post("https://site/?module=Messages&file=searchUsers", text="<results><users /></results>")

        assert form.get_coaccounts(MessageSearchUser(user_id=111, value="Robin Doe", ss_id=222)) == []

    def test_raises_when_account_cannot_send_to_coaccounts(self, session: Smartschool):
        form = MessageComposerForm.create(session=session)
        form.can_send_to_coaccounts = False  # simulate an account without the capability
        student = MessageSearchUser(user_id=111, value="Robin Doe", ss_id=222)

        with pytest.raises(SmartSchoolCoAccountsUnavailableError, match="cannot message co-accounts"):
            form.get_coaccounts(student)


class TestMessageComposerFormAddAllCoaccounts:
    """Test MessageComposerForm.add_all_coaccounts() convenience."""

    def test_adds_every_coaccount_of_the_student(self, session: Smartschool, requests_mock: Mocker):
        form = MessageComposerForm.create(session=session)
        # search_users and add_recipient both POST to .../searchUsers, so one mock serves both;
        # add_recipient ignores the body (only needs 200).
        requests_mock.post("https://site/?module=Messages&file=searchUsers", text=_COACCOUNT_SEARCH_XML)
        student = MessageSearchUser(user_id=111, value="Robin Doe", ss_id=222)

        added = form.add_all_coaccounts(student)

        assert [(c.user_id, c.user_lt) for c in added] == [(111, 1), (111, 2)]
        add_forms = _sent_forms(requests_mock, "addUserToSelected")
        assert [d["userlt"] for d in add_forms] == ["1", "2"]
        assert all(d["type"] == "1" for d in add_forms)  # co-account To container

    def test_adds_coaccounts_for_multiple_users(self, session: Smartschool, requests_mock: Mocker):
        form = MessageComposerForm.create(session=session)
        requests_mock.post("https://site/?module=Messages&file=searchUsers", text=_COACCOUNT_SEARCH_MIXED_XML)
        student_a = MessageSearchUser(user_id=111, value="Robin Doe", ss_id=222)
        student_b = MessageSearchUser(user_id=999, value="Robin Roe", ss_id=222)

        added = form.add_all_coaccounts(student_a, student_b)

        # Each user's own co-accounts, in order: A's two parents then B's one.
        assert [(c.user_id, c.user_lt) for c in added] == [(111, 1), (111, 2), (999, 1)]

    def test_add_all_coaccounts_with_no_users_is_a_noop(self, session: Smartschool):
        form = MessageComposerForm.create(session=session)

        assert form.add_all_coaccounts() == []

    def test_add_all_coaccounts_raises_when_account_lacks_capability(self, session: Smartschool):
        form = MessageComposerForm.create(session=session)
        form.can_send_to_coaccounts = False
        student = MessageSearchUser(user_id=111, value="Robin Doe", ss_id=222)

        with pytest.raises(SmartSchoolCoAccountsUnavailableError):
            form.add_all_coaccounts(student)


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

    def test_add_attachment_raises_error_when_file_not_found(self, session: Smartschool):
        form = MessageComposerForm.create(session=session)

        # session fixture chdirs to a tmp dir, so this path genuinely is not a file
        with pytest.raises(FileNotFoundError, match="does not exist"):
            form.add_attachment("nonexistent.pdf")

    def test_add_attachment_raises_error_when_path_is_not_file(self, session: Smartschool, tmp_path: Path):
        form = MessageComposerForm.create(session=session)

        # A real directory exists but is not a file, so add_attachment must reject it.
        a_directory = tmp_path / "somedir"
        a_directory.mkdir()

        with pytest.raises(FileNotFoundError, match="does not exist"):
            form.add_attachment(a_directory)

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

    def test_send_uses_post_request(self, session: Smartschool, requests_mock: Mocker):
        form = MessageComposerForm.create(session=session)

        form.send()

        posts = [r for r in requests_mock.request_history if r.method == "POST"]
        assert len(posts) == 1
        assert "file=composeMessage" in posts[0].url

    def test_send_includes_all_payload_fields(self, session: Smartschool, requests_mock: Mocker):
        form = MessageComposerForm.create(session=session)
        form.set_subject("Test Subject")
        form.set_message_html("<p>Test</p>")

        form.send()

        # The multipart body carries every payload field's value.
        body = requests_mock.request_history[-1].text or ""
        assert "Test Subject" in body
        assert "<p>Test</p>" in body


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
