from pathlib import Path

import pytest

from smartschool.session import session


def test_smartschool_not_started_yet(mocker):
    mocker.patch.object(session, "creds", new=None)

    with pytest.raises(RuntimeError, match="Please start smartschool first via"):
        session.get("/")


def test_smartschool_not_logged_on_yet(requests_mock):
    counter = 0

    def fake_redirect_to_login(req, context):
        nonlocal counter

        req.url = "https://site"

        if counter == 0:
            req.url += "/login"

        counter += 1

        return Path(__file__).parent.joinpath("requests", "login.html").read_text(encoding="utf8")

    requests_mock.get("/", text=fake_redirect_to_login)
    requests_mock.post("/login", text=fake_redirect_to_login)
    session.get("/")


def test_smartschool_repr():
    assert repr(session) == "Smartschool(for: bumba)"
