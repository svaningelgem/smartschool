from __future__ import annotations

import contextlib
import functools
import json
import time
from dataclasses import dataclass, field
from functools import cached_property
from http.cookiejar import LWPCookieJar
from pathlib import Path
from typing import TYPE_CHECKING, Self
from urllib.parse import urljoin

from requests import Session

from .common import bs4_html, get_all_values_from_form

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

        self._session.cookies.save(ignore_discard=True)

        return resp

    return inner


@dataclass
class Smartschool:
    creds: Credentials = None

    already_logged_on: bool = field(init=False, default=None)
    _session: Session = field(init=False, default_factory=Session)

    def _try_login(self) -> None:
        if self.already_logged_on is None:
            # Created in the last 10 minutes? Assume we're still logged on...
            self.already_logged_on = self.cookie_file.exists() and self.cookie_file.stat().st_mtime > (time.time() - 600)

        if self.already_logged_on:
            return

        self.already_logged_on = True

        resp = session.get("/login")  # This will either log you in, or redirect to the main page. Refreshing the cookies in the meanwhile
        if resp.url.endswith("/login"):  # Not redirect >> do log in
            session._do_login(resp)

    @classmethod
    def start(cls, creds: Credentials) -> Self:
        global session

        creds.validate()
        session.creds = creds

        return session

    @property
    def cookie_file(self) -> Path:
        return Path.cwd() / "cookies.txt"

    def __post_init__(self):
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
            r = self.get(url, *args, **kwargs)

        json_ = r.text

        while isinstance(json_, str):
            json_ = json.loads(json_)

        return json_

    def _do_login(self, response: Response) -> Response:
        html = bs4_html(response)
        inputs = get_all_values_from_form(html, 'form[name="login_form"]')

        final = 0
        data = {}
        for input_ in inputs:
            if "username" in input_["name"]:
                data[input_["name"]] = self.creds.username
                final |= 1
            elif "password" in input_["name"]:
                data[input_["name"]] = self.creds.password
                final |= 2
            else:
                data[input_["name"]] = input_["value"]

        assert final == 3, "We're missing something here!"

        return self.post(response.url, data=data)

    @cached_property
    def _url(self) -> str:
        return "https://" + self.creds.main_url

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(for: {self.creds.username})"


session: Smartschool = Smartschool()
