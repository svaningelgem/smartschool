import dataclasses
import platform
import types
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


class _FakeKeyringError(Exception):
    pass


class _FakeKeyring:
    """Tiny stand-in for the `keyring` module: an in-memory keychain that can also simulate a broken backend."""

    errors = types.SimpleNamespace(KeyringError=_FakeKeyringError)

    def __init__(self, secrets: dict[tuple[str, str], str | None], *, broken: bool = False):
        self.secrets = secrets
        self.broken = broken

    def set_password(self, service: str, username: str, password: str | None) -> None:
        self.secrets[(service, username)] = password

    def get_password(self, service: str, username: str) -> str | None:
        if self.broken:
            raise _FakeKeyringError("No recommended backend was available")
        return self.secrets.get((service, username))

    def get_keyring(self) -> str:
        return "fake backend"


@pytest.fixture(name="fake_keyring")
def _fake_keyring(monkeypatch):
    fake = _FakeKeyring({("smartschool", "bumba"): "keyring-secret", ("my-service", "bumba"): "other-secret"})
    monkeypatch.setattr("smartschool._credentials.keyring", fake)
    return fake


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


@pytest.mark.usefixtures("fake_keyring")
def test_keyring_credentials():
    sut = KeyringCredentials(username="bumba", main_url="site", mfa="1234-56-78")
    sut.validate()

    assert sut.username == "bumba"
    assert sut.password == "keyring-secret"
    assert sut.main_url == "site"
    assert sut.mfa == "1234-56-78"
    assert sut.as_dict() == {"username": "bumba", "password": "keyring-secret", "main_url": "site", "mfa": "1234-56-78"}


@pytest.mark.usefixtures("fake_keyring")
def test_keyring_credentials_custom_service():
    sut = KeyringCredentials(username="bumba", main_url="site", mfa="1234-56-78", service="my-service")

    assert sut.password == "other-secret"


@pytest.mark.usefixtures("fake_keyring")
def test_keyring_credentials_strips_the_username():
    sut = KeyringCredentials(username=" bumba ", main_url="site", mfa="1234-56-78")

    assert sut.password == "keyring-secret"


@pytest.mark.parametrize("stored", [None, ""])
def test_keyring_credentials_password_not_stored(fake_keyring, stored):
    fake_keyring.set_password("smartschool", "bumba", stored)

    with pytest.raises(
        RuntimeError,
        match=(
            r"No password found in the keyring \(fake backend\) for service 'smartschool' and account 'bumba'\. "
            r"Store it with: python -m keyring set smartschool bumba$"
        ),
    ):
        KeyringCredentials(username="bumba", main_url="site", mfa="1234-56-78")


@pytest.mark.usefixtures("fake_keyring")
def test_keyring_credentials_missing_password_hint_has_no_trailing_space():
    with pytest.raises(RuntimeError, match=r"python -m keyring set smartschool other$"):
        KeyringCredentials(username="other ", main_url="site", mfa="1234-56-78")


def test_keyring_credentials_backend_error_is_wrapped(fake_keyring):
    fake_keyring.broken = True

    with pytest.raises(RuntimeError, match=r"keyring backend could not be used.*No recommended backend.*keyrings\.alt"):
        KeyringCredentials(username="bumba", main_url="site", mfa="1234-56-78")


def test_keyring_credentials_without_keyring_package():
    with pytest.raises(RuntimeError, match=r'pip install "smartschool\[keyring\]"'):
        KeyringCredentials(username="bumba", main_url="site", mfa="1234-56-78")


@pytest.mark.usefixtures("fake_keyring")
def test_keyring_credentials_empty_username_is_caught_by_validate():
    sut = KeyringCredentials(username="", main_url="site", mfa="1234-56-78")

    assert sut.password == ""
    with pytest.raises(RuntimeError, match="Please verify and correct these attribute"):
        sut.validate()


@pytest.mark.usefixtures("fake_keyring")
def test_keyring_credentials_blank_username_is_caught_by_validate():
    sut = KeyringCredentials(username="   ", main_url="site", mfa="1234-56-78")

    assert sut.password == ""
    with pytest.raises(RuntimeError, match=r"Please verify and correct these attributes: \['username', 'password'\]"):
        sut.validate()


@pytest.mark.usefixtures("fake_keyring")
def test_path_credentials_blank_username_does_not_query_keyring(tmp_path: Path):
    sut = PathCredentials(_create_credentials_file_without_password(tmp_path, keyring=True, username="   "))

    assert sut.password == ""
    with pytest.raises(RuntimeError, match=r"Please verify and correct these attributes: \['username', 'password'\]"):
        sut.validate()


@pytest.mark.usefixtures("fake_keyring")
def test_keyring_service_is_stripped(tmp_path: Path):
    assert KeyringCredentials(username="bumba", main_url="site", mfa="1234-56-78", service=" my-service ").password == "other-secret"
    assert PathCredentials(_create_credentials_file_without_password(tmp_path, keyring=" my-service ")).password == "other-secret"


@pytest.mark.usefixtures("fake_keyring")
def test_path_credentials_keyring_opt_in(tmp_path: Path):
    sut = PathCredentials(_create_credentials_file_without_password(tmp_path, keyring=True))
    sut.validate()

    assert sut.password == "keyring-secret"
    assert sut.other_info == {}  # the `keyring` setting is not leaked into `other_info`


@pytest.mark.usefixtures("fake_keyring")
def test_path_credentials_keyring_opt_in_with_custom_service(tmp_path: Path):
    sut = PathCredentials(_create_credentials_file_without_password(tmp_path, keyring="my-service"))

    assert sut.password == "other-secret"


@pytest.mark.usefixtures("fake_keyring")
def test_path_credentials_keyring_opt_in_strips_the_username(tmp_path: Path):
    sut = PathCredentials(_create_credentials_file_without_password(tmp_path, keyring=True, username="bumba "))
    sut.validate()

    assert sut.username == "bumba"
    assert sut.password == "keyring-secret"


@pytest.mark.usefixtures("fake_keyring")
def test_path_credentials_no_opt_in_means_no_keyring_lookup(tmp_path: Path):
    """Having the `keyring` package installed is not a reason to consult it."""
    sut = PathCredentials(_create_credentials_file_without_password(tmp_path))

    assert sut.password == ""
    with pytest.raises(RuntimeError, match=r"Please verify and correct these attributes: \['password'\]"):
        sut.validate()


@pytest.mark.parametrize("keyring_setting", [False, None, ""])
@pytest.mark.usefixtures("fake_keyring")
def test_path_credentials_keyring_switched_off(tmp_path: Path, keyring_setting):
    sut = PathCredentials(_create_credentials_file_without_password(tmp_path, keyring=keyring_setting))

    assert sut.password == ""
    assert sut.other_info == {}


@pytest.mark.usefixtures("fake_keyring")
def test_path_credentials_password_in_file_wins_over_keyring(tmp_path: Path):
    sut = PathCredentials(_create_credentials_file_without_password(tmp_path, keyring=True, password="from-file"))

    assert sut.password == "from-file"


@pytest.mark.parametrize("blank_password", [None, "", False, 0])
@pytest.mark.usefixtures("fake_keyring")
def test_path_credentials_blank_password_does_not_fall_back_on_keyring(tmp_path: Path, blank_password):
    """`password:`, `''`, `no` and `0000` all load as falsy: the line is there, so the keychain is not consulted."""
    sut = PathCredentials(_create_credentials_file_without_password(tmp_path, keyring=True, password=blank_password))

    with pytest.raises(RuntimeError, match=r"Please verify and correct these attributes: \['password'\]"):
        sut.validate()


@pytest.mark.parametrize("stored", [None, ""])
def test_path_credentials_keyring_password_not_stored(tmp_path: Path, fake_keyring, stored):
    fake_keyring.set_password("smartschool", "bumba", stored)

    with pytest.raises(RuntimeError, match=r"python -m keyring set smartschool bumba$"):
        PathCredentials(_create_credentials_file_without_password(tmp_path, keyring=True))


def test_path_credentials_keyring_backend_error_is_wrapped(tmp_path: Path, fake_keyring):
    fake_keyring.broken = True

    with pytest.raises(RuntimeError, match=r"keyring backend could not be used"):
        PathCredentials(_create_credentials_file_without_password(tmp_path, keyring=True))


def test_path_credentials_keyring_opt_in_without_keyring_package(tmp_path: Path):
    with pytest.raises(RuntimeError, match=r'pip install "smartschool\[keyring\]"'):
        PathCredentials(_create_credentials_file_without_password(tmp_path, keyring=True))


def test_path_credentials_without_password_and_without_keyring_package(tmp_path: Path):
    sut = PathCredentials(_create_credentials_file_without_password(tmp_path))

    with pytest.raises(RuntimeError, match=r"Please verify and correct these attributes: \['password'\]"):
        sut.validate()


@pytest.mark.usefixtures("fake_keyring")
def test_path_credentials_without_username_does_not_query_keyring(tmp_path: Path):
    sut = PathCredentials(_create_credentials_file_without_password(tmp_path, keyring=True, username=""))

    assert sut.password == ""
    with pytest.raises(RuntimeError, match="Please verify and correct these attribute"):
        sut.validate()


@pytest.mark.usefixtures("fake_keyring")
def test_password_is_not_in_repr(tmp_path: Path):
    credentials = [
        KeyringCredentials(username="bumba", main_url="site", mfa="1234-56-78"),
        PathCredentials(_create_credentials_file_without_password(tmp_path, keyring=True)),
        PathCredentials(_create_credentials_file_without_password(tmp_path, password="from-file")),
        AppCredentials(username="bumba", password="app-secret", main_url="site", mfa="1234-56-78"),
    ]

    for sut in credentials:
        assert sut.password
        assert sut.password not in repr(sut)
        assert sut.password not in str(sut)


@pytest.mark.usefixtures("fake_keyring")
def test_second_factor_is_not_in_repr(tmp_path: Path):
    """`mfa` is the TOTP seed of a 2FA account, and extra yml keys (web_monitor's `totp`) can be one too."""
    seed = "JBSWY3DPEHPK3PXP"
    credentials = [
        KeyringCredentials(username="bumba", main_url="site", mfa=seed),
        PathCredentials(_create_credentials_file_without_password(tmp_path, keyring=True, mfa=seed, totp=seed)),
        AppCredentials(username="bumba", password="app-secret", main_url="site", mfa=seed),
    ]

    for sut in credentials:
        assert seed not in repr(sut)
        assert seed not in str(sut)
