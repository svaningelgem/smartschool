import dataclasses

import pytest
from pydantic import AliasChoices, AliasPath, Field
from pydantic.dataclasses import dataclass

from smartschool import MessageHeaders, Smartschool
from smartschool._xml_interface import SmartschoolXmlNoCache, _build_alias_map


def test_build_alias_map_handles_every_alias_shape():
    @dataclass
    class _Model:
        aliased: str = Field(default="", validation_alias="theAlias")  # validation_alias is a plain str
        choices: str = Field(default="", validation_alias=AliasChoices("primary", AliasPath("nested", 0)))  # str + non-str choice
        plain: str = ""  # no validation_alias and no alias

    amap = _build_alias_map(_Model.__pydantic_fields__)  # pylint: disable=no-member  # ty: ignore[unresolved-attribute]  # set by the pydantic decorator

    assert amap == {"theAlias": "aliased", "primary": "choices"}


def test_no_cache_stores_by_keyword_and_never_returns_a_cached_value(session: Smartschool):
    """`_store_into_cache` takes its value as `obj`, drops it, and nothing is ever cached."""
    headers = MessageHeaders(session)

    assert headers._store_into_cache(obj=["anything"]) is None  # pylint: disable=protected-access  # white-box test

    with pytest.raises(KeyError):
        headers._get_from_cache()  # pylint: disable=protected-access  # white-box test


def test_no_cache_is_a_dataclass_with_a_generated_docstring():
    assert dataclasses.is_dataclass(SmartschoolXmlNoCache)
    assert SmartschoolXmlNoCache.__doc__ == "SmartschoolXmlNoCache(session: 'Smartschool', cache: 'dict' = <factory>)"
