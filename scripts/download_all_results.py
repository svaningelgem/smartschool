from smartschool import PathCredentials, SmartSchool, logger
from smartschool.periods import Periods

SmartSchool.start(PathCredentials())
for result in Periods():
    logger.info("Processing %s", result.name)

    # target = Path(__file__).parent / '../cache' / make_filesystem_safe(course.name)
    # target.mkdir(parents=True, exist_ok=True)
