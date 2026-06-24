import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from smartschool import GraphicColor, IconGraphic, PercentageGraphic, Result, Results, ResultType, Smartschool
from smartschool import _objects as objects


def test_results_normal_flow(mocker, session: Smartschool):
    mocker.patch("smartschool._results.RESULTS_PER_PAGE", new=1)

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


def test_extended_result_fields(session: Smartschool, requests_mock):
    """Issue #130: support new colors, result types, and icon graphics."""
    fixture = Path(__file__).parent / "requests/get/results/api/v1/evaluations/permissive_fields.json"
    requests_mock.get("https://site/results/api/v1/evaluations/?pageNumber=1&itemsOnPage=50", content=fixture.read_bytes())
    sut = list(Results(session))

    assert len(sut) == 3

    grass = sut[0]
    assert grass.graphic.type == "percentage"
    assert grass.graphic.color is GraphicColor.GRASS

    project = sut[1]
    assert project.type is ResultType.PROJECT_WITH_RUBRICS
    assert isinstance(project.graphic, IconGraphic)
    assert project.graphic.color == "lpd_steel"
    assert project.graphic.value == "target_lpd_steel"
    assert project.graphic.description is None

    icon = sut[2]
    assert icon.type is ResultType.NORMAL
    assert isinstance(icon.graphic, IconGraphic)
    assert icon.graphic.value == "bullet_square_green"


def test_unknown_graphic_color_raises():
    """Strict enum: unknown colors must fail loudly so we add the member."""
    with pytest.raises(ValidationError):
        PercentageGraphic(type="percentage", color="periwinkle", value=50, description="5/10")


def test_unknown_result_type_raises(session: Smartschool, requests_mock):
    """Strict enum: unknown result types must fail loudly."""
    payload = [{**_minimal_result_payload(), "type": "brand-new-type"}]
    requests_mock.get("https://site/results/api/v1/evaluations/?pageNumber=1&itemsOnPage=50", json=payload)
    with pytest.raises(ValidationError):
        list(Results(session))


def _minimal_result_payload() -> dict:
    fixture = Path(__file__).parent / "requests/get/results/api/v1/evaluations/permissive_fields.json"
    return json.loads(fixture.read_text())[0]
