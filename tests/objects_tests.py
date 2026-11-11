import dataclasses
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError
from pydantic.dataclasses import is_pydantic_dataclass

import smartschool
from smartschool import Course, CourseGraphic, DateRange, MessageSearchUser, PersonDescription, SchoolClass, SkoreWorkYear, Teacher, _objects


def test_every_response_model_is_keyword_only():
    """A positional argument would silently land in another field as soon as a model gains or moves one."""
    models = {cls for module in (smartschool, _objects) for cls in vars(module).values() if isinstance(cls, type) and is_pydantic_dataclass(cls)}

    assert models
    assert not [f"{cls.__name__}.{field.name}" for cls in models for field in dataclasses.fields(cls) if not field.kw_only]


@pytest.fixture(name="create_course")
def fixture_create_course():
    def _create(num_teachers: int = 2):
        gr = CourseGraphic(type="icon", value="")
        dr = DateRange(start=datetime.now(tz=timezone.utc), end=datetime.now(tz=timezone.utc))
        swy = SkoreWorkYear(id=0, date_range=dr)
        cl = SchoolClass(identifier="0", id=0, platform_id=0, name="", type="", icon="")

        teachers = []
        for i in range(1, num_teachers + 1):
            pd = PersonDescription(starting_with_first_name=f"first_{i} last_{i}", starting_with_last_name=f"last_{i}, first_{i}")
            teachers.append(Teacher(id=str(i), picture_hash=f"hash{i}", picture_url=f"url{i}", description=pd, name=pd, sort=f"sort{i}"))

        return Course(id=1, name="Math", graphic=gr, teachers=teachers, skore_class_id=123, parent_course_id=None, skore_work_year=swy, class_=cl)

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


def test_course_graphic_accepts_image():
    """Issue #165: some schools use image graphics for courses, not only icons."""
    assert CourseGraphic(type="image", value="foo").type == "image"
    assert CourseGraphic(type="icon", value="foo").type == "icon"


def test_message_search_user_accepts_both_spellings_and_reports_the_one_used():
    """The composer builds these by field name, so a validation error points at `user_id`, not `userID`."""
    by_alias = MessageSearchUser(  # pylint: disable=unexpected-keyword-arg,missing-kwoa  # ty: ignore[missing-argument]  # the API aliases
        userID=1,  # ty: ignore[unknown-argument]
        value="v",
        ssID=2,  # ty: ignore[unknown-argument]
    )
    assert MessageSearchUser(user_id=1, value="v", ss_id=2) == by_alias

    with pytest.raises(ValidationError) as by_field_name:
        MessageSearchUser(user_id="nope", value="v", ss_id=2)  # ty: ignore[invalid-argument-type]  # invalid on purpose
    with pytest.raises(ValidationError) as by_api_alias:
        MessageSearchUser(  # pylint: disable=unexpected-keyword-arg,missing-kwoa  # ty: ignore[missing-argument]  # idem
            userID="nope",  # ty: ignore[unknown-argument]
            value="v",
            ssID=2,  # ty: ignore[unknown-argument]
        )

    assert [error["loc"] for error in by_field_name.value.errors()] == [("user_id",)]
    assert [error["loc"] for error in by_api_alias.value.errors()] == [("userID",)]
