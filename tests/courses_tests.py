from smartschool import Courses, Smartschool, TopNavCourses


def test_topnav_courses_normal_flow(session: Smartschool):
    sut = list(TopNavCourses(session))

    assert sut[0].name == "Aardrijkskunde_4_LOPE_2024-2025"
    assert sut[1].name == "AV_tweede graad_24-25"


def test_courses_normal_flow(session: Smartschool):
    sut = list(Courses(session))

    assert sut[0].name == "Aardrijkskunde"
    assert sut[1].name == "Biologie"
