import os
import re
import sys
from collections.abc import Generator
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, quote_plus

import pytest
from loguru import logger
from requests_mock import ANY

from smartschool import EnvCredentials, Smartschool


@pytest.fixture
def session(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Generator[Smartschool, None, None]:
    """Create a Smartschool session with mocked environment and cache."""
    original_dir = Path.cwd()

    try:
        os.chdir(tmp_path)
        cache_path = tmp_path / ".cache"
        cache_path.mkdir(parents=True, exist_ok=True)

        cache_path.joinpath("authenticated_user.yml").write_text("id: '49_10880_2'", encoding="utf8")

        monkeypatch.setenv("SMARTSCHOOL_USERNAME", "bumba")
        monkeypatch.setenv("SMARTSCHOOL_PASSWORD", "delu")
        monkeypatch.setenv("SMARTSCHOOL_MAIN_URL", "site")
        monkeypatch.setenv("SMARTSCHOOL_MFA", "1234-56-78")

        monkeypatch.setattr(Smartschool, "cache_path", cache_path)

        yield Smartschool(EnvCredentials())
    finally:
        os.chdir(original_dir)


@pytest.fixture
def session_no_creds(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Generator[Smartschool, None, None]:
    """Create a Smartschool session without credentials for testing error cases."""
    original_dir = Path.cwd()

    try:
        os.chdir(tmp_path)
        cache_path = tmp_path / ".cache"
        cache_path.mkdir(parents=True, exist_ok=True)

        monkeypatch.setattr(Smartschool, "cache_path", cache_path)
        yield Smartschool()
    finally:
        os.chdir(original_dir)


@pytest.fixture
def mock_credentials():
    """Create mock credentials for testing."""

    class MockCreds:
        username = "test_user"
        password = "test_pass"
        main_url = "test.smartschool.be"
        mfa = "123456"

        def validate(self):
            """Empty validation method for testing."""

    return MockCreds()


@pytest.fixture
def authenticated_user_data():
    """Sample authenticated user data for testing."""
    return {"id": 12345, "username": "test_user", "firstName": "Test", "lastName": "User", "email": "test@example.com", "roles": ["student"]}


@pytest.fixture(autouse=True)
def _clear_caches_from_agenda() -> Generator[None, Any, None]:
    """Clear caches after each test to prevent test pollution."""
    try:
        yield
    finally:
        for name, mod in sys.modules.items():
            if not name.startswith("smartschool"):
                continue

            for v in vars(mod).values():
                if isinstance(v, type) and hasattr(v, "cache") and not isinstance(v.cache, property):
                    v.cache.clear()


@pytest.fixture(autouse=True)
def _setup_requests_mocker(request, requests_mock) -> None:
    """Setup comprehensive request mocking for all tests."""

    def get_filename(req) -> Path:
        try:
            xml = parse_qs(req.body)["command"][0]
            subsystem = re.search("<subsystem>(.*?)</subsystem>", xml).group(1)
            action = re.search("<action>(.*?)</action>", xml).group(1)
        except (AttributeError, KeyError):
            specific_filename = Path(__file__).parent.joinpath(
                "requests", req.method.lower(), *map(str.lower, req.path.split("/")), quote_plus(req.query), f"{request.node.name}.json"
            )
            default_filename = specific_filename.parent.with_suffix(".json")
        else:
            specific_filename = Path(__file__).parent.joinpath("requests", req.method.lower(), subsystem, f"{request.node.name}.xml")
            default_filename = specific_filename.with_stem(action)

        if specific_filename.exists():
            return specific_filename
        return default_filename

    def binary_callback(req, _) -> bytes:
        filename = get_filename(req)

        logger.debug(f"[REQUESTMOCK-BIN] {filename.exists()=} -> {filename}")
        if filename.exists():
            return filename.read_bytes()

        # Fallback for missing files
        return b'{"error": "mock response not found"}'

    requests_mock.register_uri(ANY, ANY, content=binary_callback)

    # Authentication flow mocking
    login_link = "/login"
    account_verification_link = "/account-verification"
    twofa_link = "/2fa"

    # Mock login form
    login_form = """
    <form name="login_form" method="post">
        <input type="text" name="username" />
        <input type="password" name="password" />
        <input type="submit" value="Login" />
    </form>
    """

    # Mock account verification form
    verification_form = """
    <form name="account_verification_form" method="post">
        <input type="text" name="security_question_answer" />
        <input type="submit" value="Verify" />
    </form>
    <script>
        window.extend(JSON.parse('{"vars":{"authenticatedUser":{"id":12345,"username":"test_user","firstName":"Test","lastName":"User"}}}'));
    </script>
    """

    # Mock 2FA config response
    twofa_config = '{"possibleAuthenticationMechanisms":["googleAuthenticator"]}'

    requests_mock.get(login_link, text=login_form)
    requests_mock.post(login_link, status_code=302, headers={"Location": account_verification_link})
    requests_mock.get(account_verification_link, text=verification_form)
    requests_mock.post(account_verification_link, status_code=302, headers={"Location": "/dashboard"})
    requests_mock.get(twofa_link, text="<form>2FA form</form>")
    requests_mock.get(f"{twofa_link}/api/v1/config", text=twofa_config)
    requests_mock.post(f"{twofa_link}/api/v1/google-authenticator", status_code=302, headers={"Location": "/dashboard"})

    # Mock successful dashboard response
    requests_mock.get("/dashboard", text="<html><body>Dashboard</body></html>")


@pytest.fixture
def tmp_path(tmp_path) -> Generator[Any, Any, None]:
    """Enhanced tmp_path fixture that changes working directory."""
    original_dir = Path.cwd()
    try:
        os.chdir(tmp_path)
        yield tmp_path
    finally:
        os.chdir(original_dir)


@pytest.fixture(autouse=True)
def _dont_autosave(mocker):
    mocker.patch("smartschool.courses.save_test_response")
