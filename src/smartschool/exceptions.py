class SmartSchoolException(Exception): ...


class SmartSchoolDownloadError(SmartSchoolException): ...


class SmartSchoolAuthenticationError(SmartSchoolException):
    """Indicates an error during the authentication process."""


class SmartschoolParseError(SmartSchoolException):
    """Some parsing went wrong."""
