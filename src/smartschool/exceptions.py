__all__ = ["SmartSchoolAuthenticationError", "SmartSchoolDownloadError", "SmartSchoolException", "SmartSchoolParsingError"]

from dataclasses import dataclass

from requests import Response


@dataclass
class SmartSchoolException(Exception):
    """Base exception class for smartschool API errors."""

    message: str


class SmartSchoolAuthenticationError(SmartSchoolException):
    """Indicates an error during the authentication process."""


class SmartSchoolParsingError(SmartSchoolException):
    """Indicates an error occurred while parsing data from Smartschool."""


@dataclass
class SmartSchoolDownloadError(SmartSchoolException):
    """Indicates an error occurred during a file download operation."""

    response: Response

    def __post_init__(self):
        self.status_code: int = self.response.status_code


@dataclass
class SmartSchoolJsonError(SmartSchoolDownloadError):
    """The retrieved page is an invalid json."""
