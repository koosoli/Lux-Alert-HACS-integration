"""Small helpers shared by the modules."""
from __future__ import annotations

import html
import re
from typing import Any

_TAG = re.compile(r"<[^>]*>")
# the feed writes links in Markdown: [www.example.lu/page](https://www.example.lu/page)
_MARKDOWN_LINK = re.compile(r"\[([^\[\]]+)\]\((https?://[^)\s]+)\)")
# the end of a block element or a <br>, with or without a namespace prefix (ElementTree writes <ns0:p> for <p>)
_BREAKS = re.compile(r"(?i)<\s*(?:/\s*(?:[\w.-]+:)?(?:p|li|tr|td|th|div|ul|ol|table|h[1-6])|(?:[\w.-]+:)?br)\b[^>]*>")


def shorten(text: Any, limit: int) -> str:
    """One line of at most ``limit`` characters: white space collapsed, a cut text ends in '...'."""
    text = " ".join(str(text).split())
    return text if len(text) <= limit else text[: max(0, limit - 3)] + "..."


def _bare(address: str) -> str:
    """'https://www.example.lu/page/' -> 'example.lu/page', to tell whether a link text only repeats its address."""
    address = address.strip().lower().split("://", 1)[-1]
    return (address[4:] if address.startswith("www.") else address).rstrip("/")


def _link(match: "re.Match[str]") -> str:
    label, address = match.group(1).strip(), match.group(2)
    return label if _bare(label) == _bare(address) else "%s (%s)" % (label, address)


def plain_text(markup: str | None) -> str:
    """Text of a CAP description for people: tags removed, line breaks kept as spaces, entities decoded.

    The XML parser has decoded the entities of the file once. The live feed escapes some of them twice (the text
    holds a literal ``&quot;``), so they are decoded once more, after the tags are gone, so that a decoded ``<`` is
    never taken for a tag. A Markdown link ``[label](address)`` becomes the label, plus the address when the label
    does not say it already.
    """
    if not markup:
        return ""
    text = _BREAKS.sub(" ", markup)
    text = html.unescape(_TAG.sub("", text))
    text = _MARKDOWN_LINK.sub(_link, text)
    return " ".join(text.split())


def split_list(text: Any) -> list[str]:
    """'a, b;c' -> ['a', 'b', 'c'] (comma, semicolon and line break separate; empty items are dropped)."""
    if text is None:
        return []
    return [part.strip() for part in re.split(r"[,;\n]", str(text)) if part.strip()]
