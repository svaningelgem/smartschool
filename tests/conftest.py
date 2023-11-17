import os
import re
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import parse_qs, quote_plus

import pytest
from requests_mock import ANY

from smartschool import EnvCredentials, SmartSchool


@pytest.fixture(scope="session", autouse=True)
def _setup_smartschool_for_tests() -> None:
    original_dir = Path.cwd()

    with TemporaryDirectory() as tmp_dir:  # Because cookies.txt will be written
        os.chdir(tmp_dir)

        try:
            with pytest.MonkeyPatch.context() as monkeypatch:
                monkeypatch.setenv("SMARTSCHOOL_USERNAME", "bumba")
                monkeypatch.setenv("SMARTSCHOOL_PASSWORD", "delu")
                monkeypatch.setenv("SMARTSCHOOL_MAIN_URL", "site")

                SmartSchool.start(EnvCredentials())

                yield
        finally:
            os.chdir(original_dir)


@pytest.fixture(autouse=True)
def _clear_caches_from_agenda() -> None:
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
def _setup_automated_fixtures_for_agenda_calls(request, requests_mock) -> None:
    def text_callback(req, context) -> str:
        try:
            xml = parse_qs(req.body)["command"][0]

            subsystem = re.search("<subsystem>(.*?)</subsystem>", xml).group(1)
            action = re.search("<action>(.*?)</action>", xml).group(1)
        except (AttributeError, KeyError):
            specific_filename = Path(__file__).parent.joinpath(
                "requests", req.method.lower(), *req.path.split("/"), quote_plus(req.query), f"{request.node.name}.json"
            )
            default_filename = specific_filename.parent.with_suffix(".json")
        else:
            specific_filename = Path(__file__).parent.joinpath("requests", req.method.lower(), subsystem, f"{request.node.name}.xml")
            default_filename = specific_filename.with_stem(action)

        if specific_filename.exists():  # Something specific for the test that is running
            return specific_filename.read_text(encoding="utf8")

        return default_filename.read_text(encoding="utf8")

    requests_mock.register_uri(ANY, ANY, text=text_callback)


@pytest.fixture()
def tmp_path(tmp_path) -> Path:
    original_dir = Path.cwd()
    try:
        os.chdir(tmp_path)
        yield
    finally:
        os.chdir(original_dir)
