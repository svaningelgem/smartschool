from pathlib import Path

import pytest

from smartschool import Results, Smartschool
from smartschool.objects import GraphicColor, IconGraphic, ResultType


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


def test_permissive_result_fields(session: Smartschool, requests_mock):
    """Issue #130: tolerate new colors, result types, and icon graphics."""
    fixture = Path(__file__).parent / "requests/get/results/api/v1/evaluations/permissive_fields.json"
    requests_mock.get("https://site/results/api/v1/evaluations/?pageNumber=1&itemsOnPage=50", content=fixture.read_bytes())
    sut = list(Results(session))

    assert len(sut) == 3

    # Newly introduced "grass" color is coerced to the enum.
    grass = sut[0]
    assert grass.graphic.type == "percentage"
    assert grass.graphic.color is GraphicColor.GRASS
    assert grass.graphic.color == "grass"

    # Project-with-rubrics result type with an icon graphic.
    project = sut[1]
    assert project.type is ResultType.PROJECT_WITH_RUBRICS
    assert project.type == "project-with-rubrics"
    assert isinstance(project.graphic, IconGraphic)
    assert project.graphic.color == "lpd_steel"
    assert project.graphic.value == "target_lpd_steel"
    assert project.graphic.description is None

    # Normal result with an icon graphic.
    icon = sut[2]
    assert icon.type is ResultType.NORMAL
    assert isinstance(icon.graphic, IconGraphic)
    assert icon.graphic.value == "bullet_square_green"
