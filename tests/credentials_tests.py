import dataclasses
import platform
from datetime import datetime
from pathlib import Path

import pytest
import yaml

from smartschool import AppCredentials, EnvCredentials, KeyringCredentials, PathCredentials


def _create_credentials_file(tmp_path: Path):
    file = tmp_path.joinpath("creds.yml")

    with file.open(mode="w", encoding="utf8") as fp:
        yaml.dump(EnvCredentials().as_dict(), fp)

    return file


@pytest.fixture(autouse=True)
def _no_real_keyring(monkeypatch):
    """Never touch a real keychain, even when the optional `keyring` package is installed on the dev machine."""
    monkeypatch.setattr("smartschool._credentials.keyring", None)


@pytest.fixture
def mock_keyring(mocker):
    """Stand-in for the `keyring` module; `get_password` returns the stored secret."""
    mock = mocker.patch("smartschool._credentials.keyring")
    mock.get_password.return_value = "keyring-secret"
    return mock


def _create_credentials_file_without_password(tmp_path: Path, **overrides) -> Path:
    file = tmp_path.joinpath("creds_no_password.yml")
    data = {"username": "bumba", "main_url": "site", "mfa": "1234-56-78", **overrides}
    file.write_text(yaml.dump(data), encoding="utf8")
    return file


@pytest.mark.usefixtures("session")
def test_env_credentials():
    # This information comes from conftest.py:session (included fixture)

    sut = EnvCredentials()
    sut.validate()

    assert sut.username == "bumba"
    assert sut.password == "delu"
    assert sut.main_url == "site"
    assert sut.mfa == "1234-56-78"


@pytest.mark.parametrize("make_empty", ["SMARTSCHOOL_USERNAME", "SMARTSCHOOL_PASSWORD", "SMARTSCHOOL_MAIN_URL", "SMARTSCHOOL_MFA"])
def test_env_credentials_empty(monkeypatch, make_empty):
    monkeypatch.delenv(make_empty, raising=False)

    with pytest.raises(RuntimeError, match="Please verify and correct these attribute"):
        EnvCredentials().validate()


@pytest.mark.parametrize("as_type", [Path, str])
@pytest.mark.usefixtures("session")
def test_path_credentials(tmp_path: Path, as_type: type):
    tmp_credentials = _create_credentials_file(tmp_path)
    sut = PathCredentials(as_type(tmp_credentials))
    sut.validate()

    assert sut.username == "bumba"
    assert sut.password == "delu"
    assert sut.main_url == "site"
    assert sut.mfa == "1234-56-78"


@pytest.mark.usefixtures("session")
def test_path_credentials_without_path(monkeypatch, tmp_path: Path):
    monkeypatch.setattr("pathlib.Path.cwd", lambda: tmp_path)
    tmp_path.joinpath(PathCredentials.CREDENTIALS_FILENAME).write_text(yaml.dump(EnvCredentials().as_dict()), encoding="utf8")

    sut = PathCredentials()
    sut.validate()

    assert sut.username == "bumba"
    assert sut.password == "delu"
    assert sut.main_url == "site"
    assert sut.mfa == "1234-56-78"


@pytest.mark.skipif("microsoft" in platform.release().lower(), reason="WSL tmpdir resolves inside project tree, parent-traversal finds credentials.yml")
def test_path_credentials_file_not_found(tmp_path: Path, mocker):
    mocker.patch.object(Path, "home", return_value=tmp_path)
    with pytest.raises(FileNotFoundError):
        PathCredentials(tmp_path / "not_found.yml")


@pytest.mark.parametrize(
    "make_empty",
    [
        "USERNAME",
        "PASSWORD",
        "MAIN_URL",
        "MFA",
    ],
)
@pytest.mark.usefixtures("session")
def test_path_credentials_empty(monkeypatch, make_empty, tmp_path: Path):
    monkeypatch.setenv(f"SMARTSCHOOL_{make_empty}", "")

    with pytest.raises(RuntimeError, match="Please verify and correct these attribute"):
        PathCredentials(_create_credentials_file(tmp_path)).validate()


@pytest.mark.usefixtures("session")
def test_credentials_exporting_as_dict_with_other_info():
    sut = EnvCredentials()
    object.__setattr__(sut, "other_info", {"test": "something"})

    assert sut.as_dict() == {
        "username": "bumba",
        "password": "delu",
        "main_url": "site",
        "mfa": "1234-56-78",
        "other_info": {"test": "something"},
    }


@pytest.mark.usefixtures("session")
def test_credentials_exporting_as_dict_without_other_info():
    sut = EnvCredentials()

    assert sut.as_dict() == {
        "username": "bumba",
        "password": "delu",
        "main_url": "site",
        "mfa": "1234-56-78",
    }


@pytest.mark.usefixtures("session")
def test_env_credentials_mfa_as_datetime():
    """Test that MFA is properly converted to string when entered as a datetime object."""
    sut = AppCredentials("username", "password", "main_url", datetime(2024, 1, 15))  # ty: ignore[invalid-argument-type]  # YAML may load a birthday as a date

    # Validate should convert datetime to string without raising an error
    sut.validate()

    # Verify that MFA is now a string
    assert isinstance(sut.mfa, str)
    assert sut.mfa == "2024-01-15 00:00:00"


def test_path_credentials_fields_default_to_empty_strings():
    """The fields `__post_init__` fills are declared with empty defaults, not `None`."""
    defaults = {field.name: field.default for field in dataclasses.fields(PathCredentials) if not field.init}

    assert defaults == {"username": "", "password": "", "main_url": "", "mfa": "", "other_info": None}
    assert PathCredentials.username == ""


def test_keyring_credentials(mock_keyring):
    sut = KeyringCredentials(username="bumba", main_url="site", mfa="1234-56-78")
    sut.validate()

    mock_keyring.get_password.assert_called_once_with("smartschool", "bumba")
    assert sut.username == "bumba"
    assert sut.password == "keyring-secret"
    assert sut.main_url == "site"
    assert sut.mfa == "1234-56-78"


def test_keyring_credentials_custom_service(mock_keyring):
    sut = KeyringCredentials(username="bumba", main_url="site", mfa="1234-56-78", service="my-service")

    mock_keyring.get_password.assert_called_once_with("my-service", "bumba")
    assert sut.password == "keyring-secret"


def test_keyring_credentials_password_not_stored(mock_keyring):
    mock_keyring.get_password.return_value = None

    with pytest.raises(RuntimeError, match=r"No password found in the keyring.*python -m keyring set smartschool bumba"):
        KeyringCredentials(username="bumba", main_url="site", mfa="1234-56-78")


def test_keyring_credentials_without_keyring_package():
    with pytest.raises(RuntimeError, match=r"pip install smartschool\[keyring\]"):
        KeyringCredentials(username="bumba", main_url="site", mfa="1234-56-78")


def test_keyring_credentials_empty_username_is_caught_by_validate(mock_keyring):
    sut = KeyringCredentials(username="", main_url="site", mfa="1234-56-78")

    mock_keyring.get_password.assert_not_called()
    with pytest.raises(RuntimeError, match="Please verify and correct these attribute"):
        sut.validate()


def test_keyring_credentials_as_dict(mock_keyring):
    sut = KeyringCredentials(username="bumba", main_url="site", mfa="1234-56-78")

    assert sut.as_dict() == {"username": "bumba", "password": "keyring-secret", "main_url": "site", "mfa": "1234-56-78"}


def test_path_credentials_falls_back_on_keyring(tmp_path: Path, mock_keyring):
    sut = PathCredentials(_create_credentials_file_without_password(tmp_path))
    sut.validate()

    mock_keyring.get_password.assert_called_once_with("smartschool", "bumba")
    assert sut.password == "keyring-secret"
    assert sut.other_info == {}


def test_path_credentials_password_in_file_wins_over_keyring(tmp_path: Path, mock_keyring):
    sut = PathCredentials(_create_credentials_file_without_password(tmp_path, password="from-file"))

    mock_keyring.get_password.assert_not_called()
    assert sut.password == "from-file"


def test_path_credentials_keyring_password_not_stored(tmp_path: Path, mock_keyring):
    mock_keyring.get_password.return_value = None

    with pytest.raises(RuntimeError, match=r"python -m keyring set smartschool bumba"):
        PathCredentials(_create_credentials_file_without_password(tmp_path))


def test_path_credentials_without_password_and_without_keyring_package(tmp_path: Path):
    sut = PathCredentials(_create_credentials_file_without_password(tmp_path))

    with pytest.raises(RuntimeError, match=r"Please verify and correct these attributes: \['password'\]"):
        sut.validate()


def test_path_credentials_without_username_does_not_query_keyring(tmp_path: Path, mock_keyring):
    sut = PathCredentials(_create_credentials_file_without_password(tmp_path, username=""))

    mock_keyring.get_password.assert_not_called()
    with pytest.raises(RuntimeError, match="Please verify and correct these attribute"):
        sut.validate()


def test_password_is_not_in_repr(tmp_path: Path, mock_keyring):
    credentials = [
        KeyringCredentials(username="bumba", main_url="site", mfa="1234-56-78"),
        PathCredentials(_create_credentials_file_without_password(tmp_path)),
        PathCredentials(_create_credentials_file_without_password(tmp_path, password="from-file")),
        AppCredentials(username="bumba", password="app-secret", main_url="site", mfa="1234-56-78"),
    ]

    for sut in credentials:
        assert sut.password
        assert sut.password not in repr(sut)
        assert sut.password not in str(sut)
