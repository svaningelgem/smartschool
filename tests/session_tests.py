import json
from unittest.mock import patch

import pytest
import requests
import yaml

from smartschool import Smartschool, SmartSchoolAuthenticationError


def test_smartschool_not_started_yet():
    with pytest.raises(RuntimeError, match="Smartschool instance must have valid credentials"):
        Smartschool().get("/")


def test_smartschool_repr(session: Smartschool):
    assert repr(session) == "Smartschool(for: bumba)"


def test_smartschool_without_params():
    assert Smartschool().creds is None


def test_smartschool_with_credentials(session: Smartschool):
    assert session.creds is not None


class TestSmartschoolInitialization:
    """Test Smartschool session initialization."""

    def test_initialization_with_credentials(self, mock_credentials, tmp_path):
        """Should initialize properly with credentials."""
        with patch("smartschool.session.Path.home", return_value=tmp_path):
            ss = Smartschool(creds=mock_credentials)

            assert ss.creds == mock_credentials
            assert ss._login_attempts == 0
            assert ss._max_login_attempts == 3
            assert ss._authenticated_user is None

    def test_initialization_without_credentials(self, tmp_path):
        """Should initialize without credentials."""
        with patch("smartschool.session.Path.home", return_value=tmp_path):
            ss = Smartschool()

            assert ss.creds is None
            assert ss._login_attempts == 0

    def test_cache_path_creation(self, session):
        """Should create a proper cache path structure."""
        cache_path = session.cache_path

        assert cache_path.exists()
        assert cache_path.is_dir()

    def test_cookie_file_path(self, session):
        """Should create a correct cookie file path."""
        cookie_file = session.cookie_file

        assert cookie_file.name == "cookies.txt"
        assert cookie_file.parent == session.cache_path

    def test_url_property(self, session):
        """Should construct URL correctly."""
        assert session._url == "https://site"


class TestSmartschoolAuthentication:
    """Test authentication flow and user management."""

    def test_authenticated_user_property_without_user(self, session):
        """Should raise ValueError when no authenticated user."""
        session._authenticated_user = None

        with pytest.raises(ValueError, match="We couldn't retrieve the authenticated user"):
            _ = session.authenticated_user

    def test_authenticated_user_setter_with_data(self, session, authenticated_user_data):
        """Should save authenticated user data to file."""
        session.authenticated_user = authenticated_user_data

        assert session._authenticated_user == authenticated_user_data

        user_file = session._authenticated_user_file
        assert user_file.exists()

        loaded_data = yaml.safe_load(user_file.read_text())
        assert loaded_data == authenticated_user_data

    def test_authenticated_user_setter_with_none(self, session, authenticated_user_data):
        """Should remove user file when set to None."""
        # First set user data
        session.authenticated_user = authenticated_user_data
        user_file = session._authenticated_user_file
        assert user_file.exists()

        # Then set to None
        session.authenticated_user = None
        assert not user_file.exists()
        assert session._authenticated_user is None

    def test_authenticated_user_file_loading(self, session, authenticated_user_data, tmp_path):
        """Should load existing user file on initialization."""
        # Create user file manually
        user_file = session.cache_path / "authenticated_user.yml"
        with user_file.open("w") as f:
            yaml.dump(authenticated_user_data, f)

        # Create new session that should load the file
        with patch("smartschool.session.Path.home", return_value=tmp_path):
            new_session = Smartschool(creds=session.creds)
            assert new_session._authenticated_user == authenticated_user_data


class TestSmartschoolRequests:
    """Test request handling and authentication flow."""

    def test_request_without_credentials(self, session_no_creds):
        """Should raise RuntimeError when making requests without credentials."""
        with pytest.raises(RuntimeError, match="Smartschool instance must have valid credentials"):
            session_no_creds.request("GET", "/some-url")

    def test_create_url_relative(self, session):
        """Should create absolute URL from relative path."""
        url = session.create_url("/api/test")
        assert url == "https://site/api/test"

    def test_create_url_absolute(self, session):
        """Should handle absolute URLs correctly."""
        absolute_url = "https://example.com/test"
        url = session.create_url(absolute_url)
        assert url == absolute_url

    def test_successful_request_resets_login_attempts(self, session):
        """Should reset login attempts after successful request."""
        session._login_attempts = 2

        # Make request to dashboard (mocked as successful)
        response = session.request("GET", "/dashboard")

        assert response.status_code == 200
        assert session._login_attempts == 0

    def test_json_get_request(self, session, requests_mock):
        """Should handle JSON GET requests properly."""
        test_data = {"key": "value", "number": 42}
        requests_mock.get("https://site/api/test", json=test_data)

        result = session.json("/api/test")
        assert result == test_data

    def test_json_post_request(self, session, requests_mock):
        """Should handle JSON POST requests properly."""
        test_data = {"result": "success"}
        requests_mock.post("https://site/api/test", json=test_data)

        result = session.json("/api/test", method="post", data={"param": "value"})
        assert result == test_data

    def test_json_get_with_query_params(self, session, requests_mock):
        """Should handle GET requests with query parameters."""
        test_data = {"filtered": "data"}
        requests_mock.get("https://site/api/test?param=value", json=test_data)

        result = session.json("/api/test", data={"param": "value"})
        assert result == test_data

    def test_json_empty_response(self, session, requests_mock):
        """Should handle empty JSON responses."""
        requests_mock.get("https://site/api/empty", text="")

        result = session.json("/api/empty")
        assert result == {}

    def test_json_double_encoded_response(self, session, requests_mock):
        """Should handle double-encoded JSON responses."""
        double_encoded = json.dumps(json.dumps({"data": "test"}))
        requests_mock.get("https://site/api/double", text=double_encoded)

        result = session.json("/api/double")
        assert result == {"data": "test"}


class TestAuthenticationFlow:
    """Test authentication flow handling."""

    def test_needs_auth_detection(self, session):
        """Should correctly detect when authentication is needed."""
        assert session._is_auth_url("https://site/login")
        assert session._is_auth_url("https://site/account-verification")
        assert session._is_auth_url("https://site/2fa")
        assert session._is_auth_url("https://site/2fa/")
        assert not session._is_auth_url("https://site/dashboard")

    def test_login_flow(self, session):
        """Should handle complete login flow successfully."""
        response = session.get("/login")
        assert response.url.endswith("/dashboard")

        # Should eventually reach dashboard after auth
        assert session._login_attempts == 0  # Reset after successful auth

    def test_max_login_attempts_exceeded(self, session):
        """Should raise error when max login attempts exceeded."""
        session._login_attempts = 3

        with pytest.raises(SmartSchoolAuthenticationError, match="Max login attempts"):
            session.request("GET", "/login")

    def test_2fa_without_pyotp(self, session, monkeypatch, mocker):
        """Should raise error when 2FA needed but pyotp not available."""
        # Mock pyotp as None in the session module
        monkeypatch.setattr("smartschool.session.pyotp", None)

        # Create a fresh session instance to ensure the None pyotp is used
        mock_response = mocker.Mock(spec=requests.Response, url="https://site/2fa")

        with pytest.raises(SmartSchoolAuthenticationError, match="2FA verification requires 'pyotp'"):
            session._handle_auth_redirect(mock_response)

    def test_2fa_success(self, session, mocker):
        """Should handle 2FA authentication successfully when pyotp is available."""
        with patch("smartschool.session.pyotp") as mock_pyotp:
            # Setup mock TOTP
            mock_totp = mock_pyotp.TOTP.return_value
            mock_totp.now.return_value = "123456"

            mock_response = mocker.Mock(
                spec=requests.Response,
                url="https://site/2fa",
                status_code=302,
            )

            # This should complete without error
            result = session._handle_auth_redirect(mock_response)
            assert result.url == "https://site/dashboard"

    def test_2fa_not_returning_200(self, session, requests_mock, mocker):
        with patch("smartschool.session.pyotp"):
            requests_mock.get("https://site/2fa/api/v1/config", status_code=304)
            mock_response = mocker.Mock(spec=requests.Response, url="https://site/2fa", status_code=302)
            with pytest.raises(SmartSchoolAuthenticationError, match="Could not access 2FA API endpoint"):
                session._handle_auth_redirect(mock_response)

    def test_2fa_unsupported_mechanism(self, session, requests_mock, mocker):
        """Should raise error for unsupported 2FA mechanisms."""
        # Mock config response without googleAuthenticator
        with patch("smartschool.session.pyotp"):
            requests_mock.get("https://site/2fa/api/v1/config", json={"possibleAuthenticationMechanisms": ["sms"]})

            mock_response = mocker.Mock(spec=requests.Response, url="https://site/2fa")
            with pytest.raises(SmartSchoolAuthenticationError, match="Only googleAuthenticator 2FA is supported"):
                session._handle_auth_redirect(mock_response)


class TestSmartschoolProperties:
    """Test Smartschool properties and methods."""

    def test_repr(self, session):
        """Should provide meaningful string representation."""
        repr_str = repr(session)
        assert "Smartschool" in repr_str
        assert "bumba" in repr_str  # username from fixture

    def test_cache_path_without_credentials(self, tmp_path):
        """Should create cache path without username when no credentials."""
        with patch("smartschool.session.Path.home", return_value=tmp_path):
            ss = Smartschool()
            cache_path = ss.cache_path

            assert cache_path.exists()
            assert cache_path == tmp_path / ".cache/smartschool"

    def test_authenticated_user_file_without_credentials(self, tmp_path):
        """Should return None for authenticated user file without credentials."""
        with patch("smartschool.session.Path.home", return_value=tmp_path):
            ss = Smartschool()
            assert ss._authenticated_user_file is None


class TestErrorHandling:
    """Test error handling scenarios."""

    def test_invalid_json_response(self, session, requests_mock):
        """Should handle invalid JSON gracefully."""
        requests_mock.get("https://site/api/invalid", text="not json")

        with pytest.raises(json.JSONDecodeError):
            session.json("/api/invalid")

    def test_request_with_invalid_url(self, session):
        """Should handle requests with malformed URLs."""
        # The session should still attempt the request
        response = session.request("GET", "not-a-valid-url")
        # Should get a mocked response due to our ANY matcher
        assert response is not None


def test_no_auth_file():
    sut = Smartschool()
    assert sut._authenticated_user_file is None
    sut.authenticated_user = None


def test_parse_login_information_continue_branch(mocker):
    """Test continue branch when script has src or no 'extend' in text."""
    parser = Smartschool()

    # Mock response with scripts that should be skipped
    mock_response = mocker.Mock()
    mock_html = mocker.Mock()
    mock_html.select.return_value = [
        mocker.Mock(get=lambda x: "some-src.js", text="some script"),  # has src
        mocker.Mock(get=lambda x: None, text="no extend keyword here"),  # no 'extend'
    ]

    mocker.patch("smartschool.session.bs4_html", return_value=mock_html)

    parser._parse_login_information(mock_response)

    # Should not set authenticated_user since all scripts are skipped
    with pytest.raises(ValueError, match="We couldn't retrieve the authenticated user"):
        _ = parser.authenticated_user
