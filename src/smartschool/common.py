from __future__ import annotations

import contextlib
import json
import operator
import platform
import re
import smtplib
import warnings
import xml.etree.ElementTree as ET
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from enum import Enum, auto
from typing import TYPE_CHECKING, Any, Callable, Literal

from bs4 import BeautifulSoup, FeatureNotFound, GuessedAtParserWarning
from logprise import logger
from pydantic import RootModel
from pydantic.dataclasses import is_pydantic_dataclass
from requests import Response

if TYPE_CHECKING:
    import bs4

__all__ = [
    "IsSaved",
    "as_float",
    "bs4_html",
    "get_all_values_from_form",
    "make_filesystem_safe",
    "save",
    "send_email",
    "xml_to_dict",
]

_used_bs4_option = None


class IsSaved(Enum):
    NEW = auto()
    UPDATED = auto()
    SAME = auto()


def save(
    type_: Literal["agenda", "punten", "todo"], course_name: str, id_: str, data: dict | str | Any, is_eq: Callable = operator.eq, extension: str = "json"
) -> IsSaved | dict | str:
    from .session import session  # Prevent circular import

    save_as = session.cache_path / f"_{type_}/{course_name}/{id_}.{extension}"

    save_as.parent.mkdir(exist_ok=True, parents=True)
    data_was_dict = isinstance(data, dict)
    data_was_object = is_pydantic_dataclass(data.__class__)

    if data_was_dict:
        to_write = json.dumps(data, indent=4)
    elif data_was_object:
        to_write = RootModel[data.__class__](data).model_dump_json(indent=4)
    else:
        to_write = data

    if not save_as.exists():
        save_as.write_text(to_write, encoding="utf8")
        return IsSaved.NEW

    old_data = save_as.read_text(encoding="utf8")
    if data_was_dict or data_was_object:
        old_data = json.loads(old_data)
    if data_was_object:
        old_data = data.__class__(**old_data)

    if is_eq(data, old_data):
        return IsSaved.SAME

    save_as.write_text(to_write, encoding="utf8")
    return old_data


def send_email(
    subject: str,
    text: str,
    email_to: list[str] | str,
    email_from: str,
):
    if isinstance(email_to, str):
        email_to = [email_to]

    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["From"] = email_from
    message["To"] = ", ".join(email_to)
    message.attach(MIMEText(text, "plain", "utf8"))

    logger.info(f"Sending email >> {subject}")

    if platform.system() == "Windows":
        logger.info("=================== On Linux we would have sent this: ===================")
        logger.info(f"Subject: {subject}")
        logger.info("")
        logger.info(text)
        logger.info("=========================================================================")
        return

    with smtplib.SMTP("localhost") as server:
        server.sendmail(
            from_addr=email_from,
            to_addrs=email_to,
            msg=message.as_string(),
        )


def bs4_html(html: str | bytes | Response) -> BeautifulSoup:
    global _used_bs4_option

    if isinstance(html, Response):
        html = html.text

    possible_options = [
        _used_bs4_option,
        {"parser": "html.parser", "features": "lxml"},
        {"features": "html5lib"},
        {"features": "html.parser"},
    ]

    for kw in possible_options:  # pragma: no branch
        if kw is None:
            continue

        with contextlib.suppress(FeatureNotFound):
            parsed = BeautifulSoup(html, **kw)
            _used_bs4_option = kw
            return parsed

    _used_bs4_option = {}
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=GuessedAtParserWarning)
        return BeautifulSoup(html)


def get_all_values_from_form(html: bs4.BeautifulSoup, form_selector: str):
    form = html.select(form_selector)
    assert len(form) == 1, f"We should have only 1 form. We got {len(form)}!"
    form = form[0]

    # action = form.attrs.get("action").lower()
    # method = form.attrs.get("method", "get").lower()
    all_inputs = form.find_all(["input", "button", "textarea", "select"])

    inputs = []
    for input_tag in all_inputs:
        tag_name = input_tag.name.lower()
        attrs = input_tag.attrs

        if "name" not in attrs:
            continue

        assert tag_name != "select", "Check if this code works. Possible issue with getting the value if the value tag isn't set"
        inputs.append(
            {
                "name": attrs.get("name"),
                "value": attrs.get("value", ""),
            }
        )
        #     select_options = []
        #     value = ""
        #     for select_option in input_tag.find_all("option"):
        #         option_value = select_option.attrs.get("value")
        #         if option_value:
        #             select_options.append(option_value)
        #             if "selected" in select_option.attrs:
        #                 value = option_value
        #     if not value and select_options:
        #         # if the default is not set, and there are options, take the first option as default
        #         value = select_options[0]
        #     # add the select to the inputs list
        #     inputs.append({"name": attrs.get("name"), "values": select_options, "value": value})

    return inputs


def fill_form(response: Response, form_selector, values: dict[str, str]) -> dict[str, str]:
    html = bs4_html(response)
    inputs = get_all_values_from_form(html, form_selector)

    data = {}
    values = values.copy()

    for input_ in inputs:
        name = input_["name"]
        for key, _value in values.items():
            if key in name:
                data[name] = values.pop(key)
                break
        else:
            data[name] = input_["value"]

    assert len(values) == 0, f"You didn't use: {sorted(values)}"
    return data


def make_filesystem_safe(name: str) -> str:
    name = re.sub("[^-_a-z0-9.]+", "_", name, flags=re.IGNORECASE)
    name = re.sub("_{2,}", "_", name)
    return name


def as_float(txt: str) -> float:
    return float(txt.replace(",", "."))


def xml_to_dict(element, *, depth: int = 0):
    if depth == 0 and isinstance(element, str):
        element = ET.XML(element.strip())

    result = {}

    for child in element:
        tag = child.tag
        if len(child) == 0:  # Leaf node?
            child_data = child.text
        else:
            child_data = xml_to_dict(child)

        if tag in result:
            if not isinstance(result[tag], list):
                # If the tag already exists, convert it to a list
                result[tag] = [result[tag]]
            result[tag].append(child_data)
        else:
            result[tag] = child_data

    return result
