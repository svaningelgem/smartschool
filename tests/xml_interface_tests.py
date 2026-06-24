from pydantic import AliasChoices, AliasPath, Field
from pydantic.dataclasses import dataclass

from smartschool._xml_interface import _build_alias_map


def test_build_alias_map_handles_every_alias_shape():
    @dataclass
    class _Model:
        aliased: str = Field(default="", validation_alias="theAlias")  # validation_alias is a plain str
        choices: str = Field(default="", validation_alias=AliasChoices("primary", AliasPath("nested", 0)))  # str + non-str choice
        plain: str = ""  # no validation_alias and no alias

    amap = _build_alias_map(_Model.__pydantic_fields__)

    assert amap == {"theAlias": "aliased", "primary": "choices"}
