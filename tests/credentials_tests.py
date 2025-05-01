from pathlib import Path

import pytest

from smartschool import EnvCredentials, PathCredentials


@pytest.fixture(autouse=True)
def _set_default_envvars(monkeypatch):
    monkeypatch.setenv("SMARTSCHOOL_USERNAME", "user")
    monkeypatch.setenv("SMARTSCHOOL_PASSWORD", "pass")
    monkeypatch.setenv("SMARTSCHOOL_MAIN_URL", "site")


def _create_credentials_file(user: str = "", pass_: str = "", url: str = ""):
    file = Path("credentials.yml")

    file.write_text(
        f"""
        username: {user}
        password: {pass_}
        main_url: {url}
    """
    )

    return file


def test_env_credentials():
    sut = EnvCredentials()
    sut.validate()

    assert sut.username == "user"
    assert sut.password == "pass"
    assert sut.main_url == "site"


@pytest.mark.parametrize("make_empty", ["SMARTSCHOOL_USERNAME", "SMARTSCHOOL_PASSWORD", "SMARTSCHOOL_MAIN_URL"])
def test_env_credentials_empty(monkeypatch, make_empty):
    monkeypatch.delenv(make_empty, raising=False)

    with pytest.raises(RuntimeError, match="Please verify and correct these attribute"):
        EnvCredentials().validate()


def test_path_credentials():
    args = {
        "user": "user",
        "pass_": "pass",
        "url": "site",
    }
    sut = PathCredentials(_create_credentials_file(**args))
    sut.validate()

    assert sut.username == "user"
    assert sut.password == "pass"
    assert sut.main_url == "site"


@pytest.mark.parametrize("make_empty", ["user", "pass_", "url"])
def test_path_credentials_empty(monkeypatch, make_empty):
    args = {"user": "user", "pass_": "pass", "url": "site", make_empty: ""}

    with pytest.raises(RuntimeError, match="Please verify and correct these attribute"):
        PathCredentials(_create_credentials_file(**args)).validate()
