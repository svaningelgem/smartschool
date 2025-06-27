from pathlib import Path

from smartschool import Results, Smartschool


def test_results_normal_flow(mocker, session: Smartschool):
    mocker.patch("smartschool.results.RESULTS_PER_PAGE", new=1)

    sut = list(Results(session))

    assert len(sut) == 1

    result = sut[0]
    assert result.name == "Repetitie hoofdstuk 1"
    assert result.graphic.total_points == 18
    assert result.graphic.achieved_points == 13.5
    assert result.graphic.percentage == 0.75

    assert result.details is not None
    assert result.details.class_.name == "3ENW"


def test_mauro_results(session: Smartschool, requests_mock):
    component_file = Path(__file__).parent / "requests/get/results/api/v1/evaluations/mauro_component.json"
    requests_mock.get("https://site/results/api/v1/evaluations/?pageNumber=1&itemsOnPage=50", content=component_file.read_bytes())
    sut = list(Results(session))
    assert len(sut) == 1
    result = sut[0]
    assert result.graphic.color == "olive"
    assert result.component is None
