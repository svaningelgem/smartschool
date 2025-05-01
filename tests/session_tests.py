import pytest

from smartschool import EnvCredentials, Smartschool
from smartschool.session import session


def test_smartschool_not_started_yet(mocker):
    mocker.patch.object(session, "_creds", new=None)

    with pytest.raises(RuntimeError, match="Please start smartschool first via"):
        session.get("/")


def test_smartschool_already_logged_on(mocker, requests_mock):
    def fake_redirect_to_login(req, context):
        req.url = "https://site"
        return "ok"

    mocker.patch.object(session, "already_logged_on", new=False)
    requests_mock.get("/login", text=fake_redirect_to_login)

    session.get("/login")


def test_smartschool_repr():
    assert repr(session) == "Smartschool(for: bumba)"


def test_smartschool_without_params():
    assert Smartschool().creds is None


def test_smartschool_with_credentials():
    assert Smartschool(EnvCredentials()).creds is not None
