from __future__ import annotations

import contextlib
import functools
import json
import re
import time
from functools import cached_property
from http.cookiejar import LWPCookieJar
from pathlib import Path
from typing import TYPE_CHECKING, Self
from urllib.parse import urljoin, urlencode

import yaml
from logprise import logger
from requests import Session

from .common import bs4_html, fill_form

if TYPE_CHECKING:  # pragma: no cover
    from requests import Response

    from .credentials import Credentials


def _handle_cookies_and_login(func):
    @functools.wraps(func)
    def inner(self: Smartschool, *args, **kwargs):
        if self.creds is None:
            raise RuntimeError("Please start smartschool first via: `Smartschool.start(PathCredentials())`")

        self._try_login()
        resp = func(self, *args, **kwargs)
        self._save_cookies()

        return resp

    return inner


class Smartschool:
    def __init__(self, creds: Credentials | None = None) -> None:
        self._creds: Credentials | None = creds
        self._authenticated_user: dict | None = None
        self.already_logged_on: bool | None = None

        self._initialize_session()

        if self.creds:
            self.creds.validate()

            if self._authenticated_user_file.exists():
                self._authenticated_user = yaml.safe_load(self._authenticated_user_file.read_text(encoding="utf8"))

    @property
    def creds(self) -> Credentials:
        return self._creds

    @creds.setter
    def creds(self, creds: Credentials) -> None:
        creds.validate()
        self._creds = creds

    @property
    def authenticated_user(self) -> dict | None:
        if self._authenticated_user is None:
            self._try_login()

        if self._authenticated_user is None:
            raise ValueError("We couldn't retrieve the authenticated user somehow!")

        return self._authenticated_user

    @authenticated_user.setter
    def authenticated_user(self, new_user: dict | None) -> None:
        self._authenticated_user = new_user
        if new_user and self.creds:
            with self._authenticated_user_file.open(mode="w", encoding="utf8") as fp:
                yaml.dump(new_user, fp)
        else:
            self._authenticated_user_file.unlink(missing_ok=True)

    @property
    def _authenticated_user_file(self) -> Path | None:
        if self.creds:
            return self.cache_path / "authenticated_user.yml"
        return None

    def _try_login(self) -> None:
        if self.already_logged_on is None:
            # Created in the last 10 minutes? Assume we're still logged on...
            self.already_logged_on = self.cookie_file.exists() and self.cookie_file.stat().st_mtime > (time.time() - 600)

        if self.already_logged_on:
            return

        self.already_logged_on = True

        resp = self.get("/login")  # This will either log you in, or redirect to the main page. Refreshing the cookies in the meanwhile
        if resp.url.endswith("/login"):
            resp = self._do_login(resp)
        if resp.url.endswith("/account-verification"):
            self._parse_login_information(resp)
            resp = self._do_login_verification(resp)
        self._parse_login_information(resp)

    @classmethod
    def start(cls, creds: Credentials) -> Self:
        global session
        session.creds = creds
        return session

    @classmethod
    def credentials(cls) -> Credentials:
        return session.creds

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
        self._session: Session = Session()
        self._session.headers["User-Agent"] = "unofficial Smartschool API interface"

        cookie_jar = LWPCookieJar(self.cookie_file)
        with contextlib.suppress(FileNotFoundError):
            cookie_jar.load(ignore_discard=True)

        self._session.cookies = cookie_jar

    def create_url(self, url: str) -> str:
        return urljoin(self._url, url)

    @_handle_cookies_and_login
    def post(self, url, *args, **kwargs) -> Response:
        return self._session.post(self.create_url(url), *args, **kwargs)

    @_handle_cookies_and_login
    def get(self, url, *args, **kwargs) -> Response:
        return self._session.get(self.create_url(url), *args, **kwargs)

    def json(self, url, *args, method: str = "get", **kwargs) -> dict:
        """Sometimes this is double json-encoded. So we keep trying until it isn't a string anymore."""
        if method.lower() == "post":
            r = self.post(url, *args, **kwargs)
        else:
            if "data" in kwargs:
                data = urlencode(kwargs.pop("data"))
                if "?" in url:
                    url += "&" + data
                else:
                    url += "?" + data
            r = self.get(url, *args, **kwargs)

        json_ = r.text

        while isinstance(json_, str):
            json_ = json.loads(json_)

        return json_

    def _do_login(self, response: Response) -> Response:
        logger.info(f"Logging in with {self.creds.username}")

        data = fill_form(
            response,
            'form[name="login_form"]',
            {
                "username": self.creds.username,
                "password": self.creds.password,
            },
        )
        return self.post(response.url, data=data)

    def _do_login_verification(self, response: Response) -> Response:
        logger.info(f"2FA for {self.creds.username}")

        data = fill_form(
            response,
            'form[name="account_verification_form"]',
            {
                "security_question_answer": self.creds.birthday,
            },
        )
        return self.post(response.url, data=data)

    def _parse_login_information(self, response: Response) -> None:
        html = bs4_html(response)
        possible_scripts = [s for s in html.select("script") if s.get("src") is None and "extend" in s.text]
        for script in possible_scripts:
            txt = script.text
            if match := re.search(r"JSON\s*\.\s*parse\s*\(\s*'(.*)'\s*\)\s*\)\s*;?\s*$", txt, flags=re.IGNORECASE):
                result = re.sub(r"\\u([0-9a-fA-F]{4})", lambda m: chr(int(m.group(1), 16)), match.group(1))
                data = json.loads(result.replace("\\\\", "\\"))
                with contextlib.suppress(KeyError, TypeError, IndexError):
                    self.authenticated_user = data["vars"]["authenticatedUser"]
                    return

    def _save_cookies(self) -> None:
        self._session.cookies.save(ignore_discard=True)

    @cached_property
    def _url(self) -> str:
        return "https://" + self.creds.main_url

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(for: {self.creds.username})"


session = Smartschool()
