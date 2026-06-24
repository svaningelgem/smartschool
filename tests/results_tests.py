from pathlib import Path

import pytest

from smartschool import Result, Results, Smartschool, objects


def test_results_normal_flow(mocker, session: Smartschool):
    mocker.patch("smartschool.results.RESULTS_PER_PAGE", new=1)

    sut = list(Results(session))

    assert len(sut) == 1

    result = sut[0]
    assert result.name == "Repetitie hoofdstuk 1"
    assert result.graphic.total_points == 18
    assert result.graphic.achieved_points == pytest.approx(13.5)
    assert result.graphic.percentage == pytest.approx(0.75)

    assert result.details is not None
    assert result.details.class_.name == "3ENW"


def test_details_provided_at_construction_is_kept(session: Smartschool):
    # When the source data already carries `details`, it is kept as-is and not re-fetched.
    data = session.json("/results/api/v1/evaluations/49_10880_0_normal_769824")
    pyd = objects.Result(**data)
    assert pyd.details is not None  # fixture includes details inline

    result = Result(session=session, **pyd.__dict__)

    assert result.details is pyd.details


def test_mauro_results(session: Smartschool, requests_mock):
    component_file = Path(__file__).parent / "requests/get/results/api/v1/evaluations/mauro_component.json"
    requests_mock.get("https://site/results/api/v1/evaluations/?pageNumber=1&itemsOnPage=50", content=component_file.read_bytes())
    sut = list(Results(session))

    assert len(sut) == 1

    result = sut[0]
    assert result.graphic.color == "olive"
    assert result.component is None


def test_letter_grade_results(session: Smartschool, requests_mock):
    letter_file = Path(__file__).parent / "requests/get/results/api/v1/evaluations/letter_grades.json"
    requests_mock.get("https://site/results/api/v1/evaluations/?pageNumber=1&itemsOnPage=50", content=letter_file.read_bytes())
    sut = list(Results(session))

    assert len(sut) == 2

    # Percentage result still works
    assert sut[0].graphic.type == "percentage"
    assert sut[0].graphic.value == 100

    # Text/letter grade result
    result = sut[1]
    assert result.graphic.type == "text"
    assert result.graphic.color == "yellow"
    assert result.graphic.value == "B"
    assert result.graphic.description == "First leaves"
