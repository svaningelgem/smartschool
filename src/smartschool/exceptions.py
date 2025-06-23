class SmartSchoolException(Exception): ...


class SmartSchoolDownloadError(SmartSchoolException): ...


class SmartSchoolAuthenticationError(SmartSchoolException):
    """Indicates an error during the authentication process."""
