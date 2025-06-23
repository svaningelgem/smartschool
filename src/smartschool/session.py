from __future__ import annotations

import contextlib
import json
import re
from dataclasses import dataclass, field
from functools import cached_property
from http.cookiejar import LWPCookieJar
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import urlencode, urljoin

import yaml
from logprise import logger
from requests import Session

from .common import bs4_html, fill_form
from .exceptions import SmartSchoolAuthenticationError

try:
    import pyotp
except ImportError:
    pyotp = None

if TYPE_CHECKING:  # pragma: no cover
    from requests import Response
    from .credentials import Credentials


@dataclass
class Smartschool(Session):
    creds: Credentials | None = None
    _login_attempts: int = field(init=False, default=0)
    _max_login_attempts: int = field(init=False, default=3)
    _auth_chain: list[str] = field(init=False, default_factory=list)
    _authenticated_user: dict | None = field(init=False, default=None)

    def __post_init__(self):
        super().__init__()

        if self.creds:
            self.creds.validate()

        self._initialize_session()

        if self._authenticated_user_file and self._authenticated_user_file.exists():
            self._authenticated_user = yaml.safe_load(self._authenticated_user_file.read_text(encoding="utf8"))

    @property
    def authenticated_user(self) -> dict | None:
        if self._authenticated_user is None:
            raise ValueError("We couldn't retrieve the authenticated user somehow!")
        return self._authenticated_user

    @authenticated_user.setter
    def authenticated_user(self, new_user: dict | None) -> None:
        self._authenticated_user = new_user
        if not self._authenticated_user_file:
            return

        if new_user:
            with self._authenticated_user_file.open(mode="w", encoding="utf8") as fp:
                yaml.dump(new_user, fp)
        else:
            self._authenticated_user_file.unlink(missing_ok=True)

    @property
    def _authenticated_user_file(self) -> Path | None:
        if self.creds:
            return self.cache_path / "authenticated_user.yml"
        return None

    def _needs_auth(self, response: Response) -> bool:
        """Check if response indicates authentication is needed."""
        return any(entry in response.url for entry in ("/login", "/account-verification", "/2fa"))

    def _handle_auth_redirect(self, response: Response) -> Response | None:
        """Handle authentication redirects with chain support."""
        if not self._needs_auth(response):
            return None

        # Check for infinite recursion in auth chain
        auth_type = response.url.split("/")[-1]
        if len(self._auth_chain) > 0 and auth_type in self._auth_chain:
            raise SmartSchoolAuthenticationError(
                f"Auth recursion detected: {' -> '.join(self._auth_chain)} -> {auth_type}"
            )

        if self._login_attempts >= self._max_login_attempts:
            raise SmartSchoolAuthenticationError(f"Max login attempts ({self._max_login_attempts}) reached")

        logger.debug(f"Auth redirect detected: {response.url}")
        self._login_attempts += 1
        self._auth_chain.append(auth_type)

        try:
            if response.url.endswith("/login"):
                return self._do_login(response)
            elif response.url.endswith("/account-verification"):
                self._parse_login_information(response)
                return self._do_login_verification(response)
            elif response.url.endswith("/2fa"):
                return self._complete_verification_2fa(response)
        finally:
            self._auth_chain.pop()

        return None

    def _reset_login_attempts(self):
        """Reset login attempt counter on successful request."""
        if self._login_attempts > 0:
            logger.debug("Resetting login attempts after successful request")
            self._login_attempts = 0
            self._auth_chain.clear()

    @property
    def cache_path(self) -> Path:
        p = Path.home() / ".cache/smartschool"
        if self.creds:
            p /= self.creds.username

        p.mkdir(parents=True, exist_ok=True)

        return p

    @property
    def cookie_file(self) -> Path:
        return self.cache_path / "cookies.txt"

    def _initialize_session(self):
        self.headers["User-Agent"] = "unofficial Smartschool API interface"
        cookie_jar = LWPCookieJar(self.cookie_file)
        with contextlib.suppress(FileNotFoundError):
            cookie_jar.load(ignore_discard=True)
        self.cookies = cookie_jar

    def create_url(self, url: str) -> str:
        return urljoin(self._url, url)

    def request(self, method, url, **kwargs) -> Response:
        """Override Session.request to handle auth and cookies transparently."""
        if self.creds is None:
            raise RuntimeError("Smartschool instance must have valid credentials.")

        # Convert relative URLs to absolute
        full_url = self.create_url(url) if not url.startswith('http') else url

        # Make the request
        response = super().request(method, full_url, **kwargs)

        # Handle auth redirects
        auth_response = self._handle_auth_redirect(response)
        if auth_response:
            logger.debug(f"Retrying original {method.upper()} after auth")
            response = super().request(method, full_url, **kwargs)

        # Reset attempts on successful non-auth response
        if not self._needs_auth(response):
            self._reset_login_attempts()

        # Save cookies
        self.cookies.save(ignore_discard=True)

        return response

    def json(self, url, method: str = "get", **kwargs) -> dict:
        """Handle JSON responses with potential double encoding."""
        if method.lower() == "post":
            r = self.request('POST', url, **kwargs)
        else:
            if "data" in kwargs:
                data = urlencode(kwargs.pop("data"))
                url += ("&" if "?" in url else "?") + data
            r = self.request('GET', url, **kwargs)

        json_ = r.text
        while isinstance(json_, str):
            if not json_:
                return {}
            json_ = json.loads(json_)
        return json_

    def _do_login(self, response: Response) -> Response:
        """Handle login form submission."""
        logger.info(f"Logging in with {self.creds.username}")
        data = fill_form(response, 'form[name="login_form"]', {
            "username": self.creds.username,
            "password": self.creds.password,
        })
        return super().request('POST', response.url, data=data, allow_redirects=True)

    def _do_login_verification(self, response: Response) -> Response:
        """Handle account verification (birthday)."""
        logger.info(f"Account verification for {self.creds.username}")
        data = fill_form(response, 'form[name="account_verification_form"]', {
            "security_question_answer": self.creds.mfa,
        })
        return super().request('POST', response.url, data=data, allow_redirects=True)

    def _complete_verification_2fa(self, response: Response) -> Response:
        """Handle 2FA verification using TOTP."""
        if pyotp is None:
            raise SmartSchoolAuthenticationError(
                "2FA verification requires 'pyotp' package. Install with: pip install pyotp"
            )

        logger.info(f"2FA verification for {self.creds.username}")

        # Check 2FA config
        config_resp = super().request('GET', self.create_url("/2fa/api/v1/config"), allow_redirects=True)
        config_resp.raise_for_status()

        if config_resp.status_code != 200:
            raise SmartSchoolAuthenticationError("Could not access 2FA API endpoint")

        config_data = json.loads(config_resp.text)
        if "googleAuthenticator" not in config_data.get("possibleAuthenticationMechanisms", []):
            raise SmartSchoolAuthenticationError("Only googleAuthenticator 2FA is supported")

        # Generate TOTP code and submit
        totp = pyotp.TOTP(self.creds.mfa)
        data = f'{{"google2fa":"{totp.now()}"}}'

        return super().request('POST', self.create_url("/2fa/api/v1/google-authenticator"),
                               data=data, allow_redirects=True)

    def _parse_login_information(self, response: Response) -> None:
        """Parse authenticated user information from response."""
        html = bs4_html(response)
        for script in html.select("script"):
            if script.get("src") or "extend" not in script.text:
                continue

            if match := re.search(r"JSON\s*\.\s*parse\s*\(\s*'(.*)'\s*\)\s*\)\s*;?\s*$",
                                  script.text, flags=re.IGNORECASE):
                result = re.sub(r"\\u([0-9a-fA-F]{4})",
                                lambda m: chr(int(m.group(1), 16)), match.group(1))
                data = json.loads(result.replace("\\\\", "\\"))
                with contextlib.suppress(KeyError, TypeError, IndexError):
                    self.authenticated_user = data["vars"]["authenticatedUser"]
                    return

    @cached_property
    def _url(self) -> str:
        return "https://" + self.creds.main_url

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(for: {self.creds.username})"


@dataclass
class SessionMixin():
    session: Smartschool
