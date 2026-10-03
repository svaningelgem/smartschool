"""Must fail type checking against the built wheel: dev/check_public_api.sh expects every checker to reject `_xpath`."""

from smartschool import Smartschool, SmartschoolLessons


def peek(session: Smartschool) -> None:
    _ = SmartschoolLessons(session)._xpath  # pylint: disable=protected-access  # the access under test
