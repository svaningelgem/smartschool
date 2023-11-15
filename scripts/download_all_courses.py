from smartschool import Courses, PathCredentials, SmartSchool, logger

SmartSchool.start(PathCredentials())
for course in Courses():
    logger.info("Processing %s", course.name)

    # target = Path(__file__).parent / '../cache' / make_filesystem_safe(course.name)
    # target.mkdir(parents=True, exist_ok=True)
