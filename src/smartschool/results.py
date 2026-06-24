from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from functools import cached_property
from itertools import count
from typing import TYPE_CHECKING

from . import _objects as objects
from .session import SessionMixin

if TYPE_CHECKING:
    from collections.abc import Iterator

__all__ = ["Results"]

RESULTS_PER_PAGE = 50


@dataclass
class Result(objects.Result, SessionMixin):
    def __post_init__(self) -> None:
        # Drop an unset `details` so the cached_property below can lazy-load it on first
        # access; a value supplied at construction is left untouched.
        if self.__dict__.get("details") is None:
            self.__dict__.pop("details", None)

    @cached_property
    def details(self) -> objects.ResultDetails | None:
        return objects.Result(**self.session.json(f"/results/api/v1/evaluations/{self.identifier}")).details


@dataclass
class Results(SessionMixin, Iterable[Result]):
    """
    Interfaces with the evaluations of smartschool.

    To reproduce: "Ga naar" > "Resultaten", it'll be one of the XHR calls then.

    Example:
    -------
    >>> for result in Results():
    >>>     print(result.name)
    Repetitie hoofdstuk 1

    """

    def __iter__(self) -> Iterator[Result]:
        for page_nr in count(start=1):  # pragma: no branch
            data = self.session.json(f"/results/api/v1/evaluations/?pageNumber={page_nr}&itemsOnPage={RESULTS_PER_PAGE}")
            for result in data:
                pyd = objects.Result(**result)
                yield Result(session=self.session, **pyd.__dict__)

            if len(data) < RESULTS_PER_PAGE:
                break
