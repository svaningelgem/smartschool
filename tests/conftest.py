import os
import re
import sys
from collections.abc import Generator
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, quote_plus

import pytest
from requests_mock import ANY

from smartschool import EnvCredentials, Smartschool


@pytest.fixture
def session(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Generator[Smartschool, None, None]:
    original_dir = Path.cwd()

    try:
        os.chdir(tmp_path)
        cache_path = tmp_path / ".cache"
        cache_path.mkdir(parents=True, exist_ok=True)

        monkeypatch.setenv("SMARTSCHOOL_USERNAME", "bumba")
        monkeypatch.setenv("SMARTSCHOOL_PASSWORD", "delu")
        monkeypatch.setenv("SMARTSCHOOL_MAIN_URL", "site")
        monkeypatch.setenv("SMARTSCHOOL_MFA", "1234-56-78")

        monkeypatch.setattr(Smartschool, "cache_path", cache_path)
        yield Smartschool(EnvCredentials())
    finally:
        os.chdir(original_dir)


@pytest.fixture(autouse=True)
def _clear_caches_from_agenda() -> Generator[None, Any, None]:
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
    def text_callback(req, _) -> str:
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

        if specific_filename.exists():  # Something specific for the test that is running
            return specific_filename.read_text(encoding="utf8")

        return default_filename.read_text(encoding="utf8")

    requests_mock.register_uri(ANY, ANY, text=text_callback)

    login_link: str = "/login"
    account_verification_link: str = "/account-verification"

    requests_mock.get(login_link, text=Path(__file__).parent.joinpath("requests", "get", "login.json").read_text(encoding="utf8"))
    requests_mock.post(login_link, status_code=302, headers={"Location": account_verification_link})
    requests_mock.get(account_verification_link, text=Path(__file__).parent.joinpath("requests", "get", "account-verification.json").read_text(encoding="utf8"))
    requests_mock.post(account_verification_link, text="ok")


@pytest.fixture
def tmp_path(tmp_path) -> Generator[Any, Any, None]:
    original_dir = Path.cwd()
    try:
        os.chdir(tmp_path)
        yield tmp_path
    finally:
        os.chdir(original_dir)
