import pytest
import pytest_mock
from more_itertools.more import side_effect

from smartschool import Courses, Smartschool, TopNavCourses
from smartschool.exceptions import SmartSchoolJsonError


def test_topnav_courses_normal_flow(session: Smartschool):
    sut = list(TopNavCourses(session))

    assert sut[0].name == "Aardrijkskunde_4_LOPE_2024-2025"
    assert sut[1].name == "AV_tweede graad_24-25"


def test_courses_normal_flow(session: Smartschool):
    sut = list(Courses(session))

    assert sut[0].name == "Aardrijkskunde"
    assert sut[1].name == "Biologie"


def test_courses_no_results_available_yet(session: Smartschool, mocker: pytest_mock.MockerFixture):
    mocker.patch.object(session, "json", side_effect=SmartSchoolJsonError("msg", mocker.Mock()))
    with pytest.raises(SmartSchoolJsonError, match="Failed to fetch the courses"):
        sut = list(Courses(session))
