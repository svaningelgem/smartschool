from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date
from typing import Iterator, TypeVar
from xml.etree import ElementTree as ET
from xml.sax.saxutils import quoteattr

from .common import xml_to_dict
from .session import session

_T = TypeVar("_T")


class SmartschoolXML(ABC):
    __is_cached__ = True

    def _construct_command(self) -> str:
        txt = "<request><command>"
        txt += f"<subsystem>{self._subsystem}</subsystem>"
        txt += f"<action>{self._action}</action>"
        txt += "<params>"

        for k, v in self._params.items():
            txt += f'<param name="{quoteattr(k)}"><![CDATA[{v}]]></param>'

        txt += "</params></command></request>"
        return txt

    def __iter__(self) -> Iterator[_T]:
        yield from self._xml()

    def _xml(self, date_to_use: date | None = None):
        today = date_to_use or date.today()
        current_week = today.strftime("%Y-%U")
        if self.__is_cached__ and current_week in self.cache:
            return self.cache[current_week]

        response = session.post(
            "/?module=Agenda&file=dispatcher",
            data={"command": self._construct_command()},
            headers={
                "X-Requested-With": "XMLHttpRequest",
            },
        )

        root = ET.fromstring(response.text)

        all_entries = []
        as_obj = self._object_to_instantiate
        for el in root.findall(self._xpath):
            as_dict = xml_to_dict(el)
            self._post_process_element(as_dict)
            obj = as_obj(**as_dict)
            all_entries.append(obj)

        self.cache[current_week] = all_entries

        return all_entries

    @property
    def cache(self) -> dict:
        if self.__is_cached__:
            raise NotImplementedError("You should add a `cache: ClassVar[dict]` to your derived class.")
        return {}

    @property
    @abstractmethod
    def _subsystem(self) -> str:
        """Returns the subsystem to request the info from."""

    @property
    @abstractmethod
    def _action(self) -> str:
        """Returns the action to send."""

    @property
    @abstractmethod
    def _params(self) -> dict:
        """Returns the parameters to send."""

    @property
    @abstractmethod
    def _xpath(self) -> str:
        """Returns the xpath to investigate."""

    @property
    @abstractmethod
    def _object_to_instantiate(self) -> type[_T]:
        """Returns the object to instantiate."""

    def _post_process_element(self, element: dict) -> None:  # noqa: B027
        """By default, this doesn't do anything, but you can adjust it when needed."""
