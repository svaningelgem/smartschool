from smartschool import Courses, TopNavCourses


def test_topnav_courses_normal_flow():
    sut = list(TopNavCourses())

    assert sut[0].name == "Aardrijkskunde_3_LOP_2023-2024"
    assert sut[1].name == "bibliotheek"


def test_courses_normal_flow():
    sut = list(Courses())

    assert sut[0].name == "Aardrijkskunde"
    assert sut[1].name == "Biologie"
