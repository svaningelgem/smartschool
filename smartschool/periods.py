from typing import Iterator

from .objects import Period
from .session import session

__all__ = ["Periods"]


class Periods:
    def __iter__(self) -> Iterator["Period"]:
        for period in session.json("/results/api/v1/periods/"):
            yield Period(**period)
