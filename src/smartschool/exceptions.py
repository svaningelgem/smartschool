class SmartSchoolException(Exception): ...


class DownloadError(SmartSchoolException): ...


class SmartSchoolAuthenticationError(SmartSchoolException):
    """Indicates an error during the authentication process."""

