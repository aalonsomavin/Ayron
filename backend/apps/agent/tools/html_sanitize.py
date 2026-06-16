import json
import re

import bleach
from bleach.css_sanitizer import CSSSanitizer

MAX_HTML_BYTES = 512_000

_JSON_SCRIPT_RE = re.compile(
    r"<script\b([^>]*\btype\s*=\s*[\"']application/json[\"'][^>]*)>(.*?)</script>",
    re.IGNORECASE | re.DOTALL,
)

ALLOWED_TAGS = frozenset(
    {
        "html",
        "head",
        "body",
        "title",
        "meta",
        "link",
        "style",
        "div",
        "span",
        "p",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "ul",
        "ol",
        "li",
        "a",
        "img",
        "table",
        "thead",
        "tbody",
        "tfoot",
        "tr",
        "th",
        "td",
        "caption",
        "colgroup",
        "col",
        "pre",
        "code",
        "blockquote",
        "hr",
        "br",
        "strong",
        "em",
        "b",
        "i",
        "small",
        "sub",
        "sup",
        "header",
        "footer",
        "main",
        "section",
        "article",
        "nav",
        "aside",
        "figure",
        "figcaption",
        "canvas",
        "details",
        "summary",
        "svg",
        "g",
        "path",
        "circle",
        "rect",
        "line",
        "polyline",
        "polygon",
        "text",
        "tspan",
        "defs",
        "lineargradient",
        "radialgradient",
        "stop",
        "clippath",
        "mask",
        "use",
        "marker",
    }
)

ALLOWED_ATTRIBUTES = {
    "*": ["class", "id", "title", "role", "aria-label", "aria-hidden", "lang"],
    "div": ["data-chart-id", "data-ay-chart-script"],
    "canvas": ["class", "width", "height"],
    "a": ["href", "rel", "target"],
    "img": ["src", "alt", "width", "height", "loading"],
    "link": ["rel", "href"],
    "meta": ["charset", "name", "content"],
    "col": ["span"],
    "colgroup": ["span"],
    "td": ["colspan", "rowspan"],
    "th": ["colspan", "rowspan", "scope"],
    "svg": ["viewBox", "width", "height", "xmlns", "fill", "stroke", "role"],
    "g": ["fill", "stroke", "transform", "opacity"],
    "path": ["d", "fill", "stroke", "stroke-width", "opacity"],
    "circle": ["cx", "cy", "r", "fill", "stroke", "stroke-width"],
    "rect": ["x", "y", "width", "height", "rx", "ry", "fill", "stroke"],
    "line": ["x1", "y1", "x2", "y2", "stroke", "stroke-width"],
    "polyline": ["points", "fill", "stroke", "stroke-width"],
    "polygon": ["points", "fill", "stroke"],
    "text": ["x", "y", "fill", "font-size", "text-anchor", "font-family"],
    "tspan": ["x", "y", "fill"],
    "lineargradient": ["id", "x1", "y1", "x2", "y2", "gradientUnits"],
    "radialgradient": ["id", "cx", "cy", "r"],
    "stop": ["offset", "stop-color", "stop-opacity"],
    "use": ["href", "x", "y", "width", "height"],
}

CSS_SANITIZER = CSSSanitizer(
    allowed_css_properties=[
        "color",
        "background",
        "background-color",
        "background-image",
        "border",
        "border-radius",
        "border-collapse",
        "border-color",
        "border-width",
        "border-style",
        "margin",
        "margin-top",
        "margin-bottom",
        "margin-left",
        "margin-right",
        "padding",
        "padding-top",
        "padding-bottom",
        "padding-left",
        "padding-right",
        "width",
        "max-width",
        "min-width",
        "height",
        "max-height",
        "min-height",
        "display",
        "grid-template-columns",
        "grid-column",
        "gap",
        "column-gap",
        "row-gap",
        "flex",
        "flex-direction",
        "align-items",
        "justify-content",
        "font-family",
        "font-size",
        "font-weight",
        "line-height",
        "letter-spacing",
        "text-align",
        "text-transform",
        "text-decoration",
        "white-space",
        "overflow",
        "overflow-x",
        "overflow-y",
        "box-sizing",
        "box-shadow",
        "opacity",
        "fill",
        "stroke",
        "stroke-width",
        "list-style",
        "vertical-align",
        "page-break-inside",
        "break-inside",
    ]
)


def _preserve_json_scripts(html: str) -> tuple[str, list[str]]:
    stored: list[str] = []

    def replace(match: re.Match) -> str:
        body = match.group(2).strip()
        try:
            json.loads(body)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid chart JSON script: {exc}") from exc
        token = f'<div data-ay-chart-script="{len(stored)}"></div>'
        stored.append(match.group(0))
        return token

    preserved = _JSON_SCRIPT_RE.sub(replace, html)
    preserved = re.sub(
        r"<script\b[^>]*>.*?</script>",
        "",
        preserved,
        flags=re.IGNORECASE | re.DOTALL,
    )
    return preserved, stored


def _restore_json_scripts(html: str, stored: list[str]) -> str:
    for idx, script in enumerate(stored):
        html = html.replace(f'<div data-ay-chart-script="{idx}"></div>', script, 1)
    return html


def _is_full_document(html: str) -> bool:
    return bool(re.search(r"<!DOCTYPE|<html", html, re.IGNORECASE))


def _extract_body_html(html: str) -> str:
    body_match = re.search(r"<body[^>]*>(.*?)</body>", html, re.IGNORECASE | re.DOTALL)
    if body_match:
        return body_match.group(1).strip()
    if _is_full_document(html):
        without_doctype = re.sub(r"<!DOCTYPE[^>]*>", "", html, flags=re.IGNORECASE)
        without_head = re.sub(r"<head[^>]*>.*?</head>", "", without_doctype, flags=re.IGNORECASE | re.DOTALL)
        without_html_tags = re.sub(r"</?html[^>]*>", "", without_head, flags=re.IGNORECASE)
        return without_html_tags.strip()
    return html.strip()


def sanitize_html_report(html: str) -> str:
    if not html or not str(html).strip():
        raise ValueError("html is required")
    raw = str(html).strip()
    if len(raw.encode("utf-8")) > MAX_HTML_BYTES:
        raise ValueError(f"html exceeds maximum of {MAX_HTML_BYTES} bytes")

    raw, json_scripts = _preserve_json_scripts(raw)
    cleaned = bleach.clean(
        raw,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        css_sanitizer=CSS_SANITIZER,
        strip=True,
    )
    cleaned = _restore_json_scripts(cleaned, json_scripts)
    if not cleaned.strip():
        raise ValueError("html is empty after sanitization")
    return cleaned


def normalize_agent_html(html: str) -> dict:
    sanitized = sanitize_html_report(html)
    full_document = _is_full_document(sanitized)
    body_html = _extract_body_html(sanitized) if full_document else sanitized
    if not body_html.strip():
        raise ValueError("html body is empty after sanitization")
    return {
        "html": sanitized if full_document else body_html,
        "body_html": body_html,
        "full_document": full_document,
    }
