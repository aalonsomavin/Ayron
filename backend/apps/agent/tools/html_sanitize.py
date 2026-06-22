import json
import re

import bleach
from bleach.css_sanitizer import CSSSanitizer

from apps.agent.tools.html_insight import normalize_insight_markup

MAX_HTML_BYTES = 512_000

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
        "script",
        "button",
        "input",
        "select",
        "option",
        "textarea",
        "label",
        "form",
    }
)

ALLOWED_ATTRIBUTES = {
    "*": [
        "class",
        "id",
        "title",
        "role",
        "aria-label",
        "aria-hidden",
        "lang",
        "data-page",
        "data-label",
        "data-region",
        "data-filter-id",
        "data-calc-output",
        "data-calc-input",
        "hidden",
    ],
    "div": [
        "data-chart-id",
        "data-ay-chart-script",
        "data-ay-json-script",
        "data-ay-preserved-script",
        "data-panels-target",
        "data-dimension",
        "data-measure",
        "data-cross-filter",
        "data-agg",
        "data-format",
    ],
    "canvas": ["class", "width", "height"],
    "a": ["href", "rel", "target"],
    "img": ["src", "alt", "width", "height", "loading"],
    "link": ["rel", "href"],
    "meta": ["charset", "name", "content"],
    "col": ["span"],
    "colgroup": ["span"],
    "td": ["colspan", "rowspan"],
    "th": ["colspan", "rowspan", "scope"],
    "tr": ["data-region", "data-year", "data-country", "data-genre"],
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
    "script": ["type", "src", "id", "defer", "async"],
    "button": ["type", "disabled"],
    "input": ["type", "name", "value", "min", "max", "step", "placeholder", "checked", "disabled"],
    "select": ["name", "disabled"],
    "option": ["value", "selected", "disabled"],
    "textarea": ["name", "rows", "cols", "placeholder", "disabled"],
    "label": ["for"],
    "form": ["action", "method"],
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


_SCRIPT_RE = re.compile(
    r"<script\b([^>]*)>(.*?)</script>|<script\b([^>]*)/>",
    re.IGNORECASE | re.DOTALL,
)

ALLOWED_SCRIPT_SRC_PREFIXES = (
    "https://cdn.jsdelivr.net/npm/chart.js",
)

_ALLOWED_INLINE_SCRIPT_TYPES = frozenset(
    {
        "text/javascript",
        "application/javascript",
        "module",
    }
)


def _script_is_allowed(attrs: str, body: str) -> bool:
    if re.search(r"\btype\s*=\s*[\"']application/json[\"']", attrs, re.IGNORECASE):
        try:
            json.loads(body.strip())
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON script: {exc}") from exc
        return True

    src_match = re.search(r"\bsrc\s*=\s*[\"']([^\"']+)[\"']", attrs, re.IGNORECASE)
    if src_match:
        src = src_match.group(1).strip()
        return any(src.startswith(prefix) for prefix in ALLOWED_SCRIPT_SRC_PREFIXES)

    type_match = re.search(r"\btype\s*=\s*[\"']([^\"']+)[\"']", attrs, re.IGNORECASE)
    if type_match:
        script_type = type_match.group(1).strip().lower()
        return script_type in _ALLOWED_INLINE_SCRIPT_TYPES

    return True


def _preserve_scripts(html: str) -> tuple[str, list[str]]:
    stored: list[str] = []

    def replace(match: re.Match) -> str:
        attrs = match.group(1) or match.group(3) or ""
        body = match.group(2) or ""
        if not _script_is_allowed(attrs, body):
            return ""
        token = f'<div data-ay-preserved-script="{len(stored)}"></div>'
        stored.append(match.group(0))
        return token

    preserved = _SCRIPT_RE.sub(replace, html)
    return preserved, stored


def _restore_scripts(html: str, stored: list[str]) -> str:
    for idx, script in enumerate(stored):
        html = html.replace(f'<div data-ay-preserved-script="{idx}"></div>', script, 1)
        html = html.replace(f'<div data-ay-json-script="{idx}"></div>', script, 1)
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

    raw, preserved_scripts = _preserve_scripts(raw)
    cleaned = bleach.clean(
        raw,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        css_sanitizer=CSS_SANITIZER,
        strip=True,
    )
    cleaned = _restore_scripts(cleaned, preserved_scripts)
    if not cleaned.strip():
        raise ValueError("html is empty after sanitization")
    return cleaned


def normalize_agent_html(html: str) -> dict:
    sanitized = sanitize_html_report(html)
    full_document = _is_full_document(sanitized)
    body_html = _extract_body_html(sanitized) if full_document else sanitized
    if not body_html.strip():
        raise ValueError("html body is empty after sanitization")
    body_html = normalize_insight_markup(body_html)
    if full_document:
        sanitized = re.sub(
            r"(<body[^>]*>)(.*?)(</body>)",
            lambda match: f"{match.group(1)}{body_html}{match.group(3)}",
            sanitized,
            count=1,
            flags=re.IGNORECASE | re.DOTALL,
        )
    else:
        sanitized = body_html
    return {
        "html": sanitized if full_document else body_html,
        "body_html": body_html,
        "full_document": full_document,
    }
