from datetime import datetime, timezone

import pytest

from smartschool.objects import Class_, Course, CourseGraphic, DateRange, PersonDescription, SkoreWorkYear, Teacher


@pytest.fixture
def create_course():
    def _create(num_teachers: int = 2):
        gr = CourseGraphic(type="icon", value="")
        dr = DateRange(start=datetime.now(tz=timezone.utc), end=datetime.now(tz=timezone.utc))
        swy = SkoreWorkYear(0, dr)
        cl = Class_("0", 0, 0, "", "", "")

        teachers = []
        for i in range(1, num_teachers + 1):
            pd = PersonDescription(f"first_{i} last_{i}", f"last_{i}, first_{i}")
            teachers.append(Teacher(str(i), f"hash{i}", f"url{i}", pd, pd, f"sort{i}"))

        return Course(1, "Math", gr, teachers, 123, None, swy, cl)

    return _create


def test_course_str_single_teacher(create_course):
    course = create_course(1)
    assert str(course) == "Math (Teacher: last_1, first_1)"


def test_course_str_multiple_teachers(create_course):
    course = create_course(2)
    assert str(course) == "Math (Teachers: last_1, first_1, last_2, first_2)"


def test_course_str_no_teachers(create_course):
    course = create_course(0)
    assert str(course) == "Math (Teachers: )"
