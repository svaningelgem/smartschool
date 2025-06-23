import pytest
from requests_mock import ANY

from smartschool import DownloadError, ResultDetail, Results, Smartschool


def test_results_normal_flow(mocker, session: Smartschool):
    mocker.patch("smartschool.results.RESULTS_PER_PAGE", new=1)

    sut = list(Results(session))

    assert len(sut) == 1
    assert sut[0].name == "Repetitie hoofdstuk 1"
    assert sut[0].graphic.total_points == 18
    assert sut[0].graphic.achieved_points == 13.5
    assert sut[0].graphic.percentage == 0.75


def test_result_detail_normal_flow(session: Smartschool):
    sut = ResultDetail(session, result_id="abc_normal_123").get()

    assert sut.name == "Repetitie hoofdstuk 1"
    assert sut.graphic.achieved_points == 13.5
    assert sut.details.teachers[0].name.startingWithFirstName == "Gert Segers"


def test_result_detail_with_empty_return_value(session: Smartschool):
    with pytest.raises(DownloadError):
        ResultDetail(session, result_id="empty_return_value").get()


def test_result_detail_with_faulty_session_get(requests_mock, session: Smartschool):
    requests_mock.register_uri(ANY, ANY, status_code=404)

    with pytest.raises(DownloadError):
        ResultDetail(session, result_id="abc_normal_123").get()


def test_result_with_empty_return_value(requests_mock, session: Smartschool):
    requests_mock.register_uri(ANY, ANY, text="")

    with pytest.raises(DownloadError):
        next(iter(Results(session)))


def test_result_with_faulty_session_get(requests_mock, session: Smartschool):
    requests_mock.register_uri(ANY, ANY, status_code=404)

    with pytest.raises(DownloadError):
        next(iter(Results(session)))
