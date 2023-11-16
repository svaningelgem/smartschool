from __future__ import annotations

import pytest

from smartschool._xml_interface import SmartschoolXML


def test_no_cache_defined_for_xml_interface():
    class Test(SmartschoolXML):
        @property
        def _subsystem(self) -> str:
            pass

        @property
        def _action(self) -> str:
            pass

        @property
        def _params(self) -> dict:
            pass

        @property
        def _xpath(self) -> str:
            pass

        @property
        def _object_to_instantiate(self) -> type:
            pass

    with pytest.raises(NotImplementedError, match=r"You should add a `cache: ClassVar\[dict]` to your derived class"):
        list(Test())
