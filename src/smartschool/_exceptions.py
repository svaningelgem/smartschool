__all__ = [
    "SmartSchoolAttachmentUploadError",
    "SmartSchoolAuthenticationError",
    "SmartSchoolCoAccountsUnavailableError",
    "SmartSchoolDownloadError",
    "SmartSchoolException",
    "SmartSchoolJsonError",
    "SmartSchoolParsingError",
]

from dataclasses import dataclass

from requests import Response


@dataclass
class SmartSchoolException(Exception):
    """Base exception class for smartschool API errors."""

    message: str

    def __str__(self) -> str:
        return self.message


class SmartSchoolAuthenticationError(SmartSchoolException):
    """Indicates an error during the authentication process."""


class SmartSchoolParsingError(SmartSchoolException):
    """Indicates an error occurred while parsing data from Smartschool."""


class SmartSchoolAttachmentUploadError(SmartSchoolException):
    """Indicates an error while uploading a message attachment."""


@dataclass
class SmartSchoolCoAccountsUnavailableError(SmartSchoolException):
    """Raised when co-accounts (parents) are used on an account that lacks that capability."""

    message: str = "This account cannot message co-accounts"


@dataclass
class SmartSchoolDownloadError(SmartSchoolException):
    """Indicates an error occurred during a file download operation."""

    response: Response

    def __post_init__(self):
        self.status_code: int = self.response.status_code


@dataclass
class SmartSchoolJsonError(SmartSchoolDownloadError):
    """The retrieved page is an invalid json."""
