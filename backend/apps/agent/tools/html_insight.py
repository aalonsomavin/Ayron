import re

_INSIGHT_MARK_PATH_A = (
    "M6.05 17.33 L6.05 7.66 L6.06 7.43 L6.08 7.20 L6.13 6.99 L6.19 6.79 "
    "L6.27 6.59 L6.36 6.41 L6.47 6.23 L6.60 6.07 L6.75 5.92 L6.91 5.77 "
    "L7.10 5.64 L7.29 5.52 L7.77 5.25 L7.89 5.18 L8.02 5.13 L8.14 5.10 "
    "L8.25 5.08 L8.37 5.08 L8.48 5.09 L8.59 5.12 L8.69 5.17 L8.80 5.23 "
    "L8.90 5.31 L8.99 5.40 L9.08 5.51 L13.33 10.93"
)
_INSIGHT_MARK_PATH_B = (
    "M17.95 6.67 L17.95 16.34 L17.94 16.57 L17.92 16.80 L17.87 17.01 "
    "L17.81 17.21 L17.73 17.41 L17.64 17.59 L17.53 17.77 L17.40 17.93 "
    "L17.25 18.08 L17.09 18.23 L16.90 18.36 L16.71 18.48 L16.23 18.75 "
    "L16.11 18.82 L15.98 18.87 L15.86 18.90 L15.75 18.92 L15.63 18.92 "
    "L15.52 18.91 L15.41 18.88 L15.31 18.83 L15.20 18.77 L15.10 18.69 "
    "L15.01 18.60 L14.92 18.49 L10.67 13.07"
)

_INSIGHT_CARD_OPEN_RE = re.compile(
    r'<div\s+class="[^"]*\bay-dash-card--insight\b[^"]*"[^>]*>',
    re.IGNORECASE,
)

_INSIGHT_LOGO_DIV_RE = re.compile(
    r'<div\s+class="ay-dash-insight-logo"[^>]*>.*?</div>',
    re.DOTALL | re.IGNORECASE,
)

_INSIGHT_HEAD_OPEN_RE = re.compile(
    r'<div\s+class="[^"]*\bay-dash-insight-head\b[^"]*"[^>]*>',
    re.IGNORECASE,
)

_INSIGHT_ROGUE_ICON_RE = re.compile(
    r'^\s*<div[^>]*>\s*(?:<svg\b[^>]*>.*?</svg>|\$|€|£)\s*</div>',
    re.DOTALL | re.IGNORECASE,
)

_DIV_OPEN_RE = re.compile(r"<div\b", re.IGNORECASE)
_DIV_CLOSE_RE = re.compile(r"</div>", re.IGNORECASE)


def insight_logo_svg(gradient_id: str) -> str:
    return (
        f'<svg viewBox="0 0 24 24" fill="none" aria-hidden="true">'
        f'<defs><linearGradient id="{gradient_id}" x1="2.4" y1="2.4" '
        f'x2="21.6" y2="21.6" gradientUnits="userSpaceOnUse">'
        f'<stop offset="0" stop-color="#6fe6cf"></stop>'
        f'<stop offset="0.5" stop-color="#93ef66"></stop>'
        f'<stop offset="1" stop-color="#d9f23e"></stop>'
        f"</linearGradient></defs>"
        f'<path d="{_INSIGHT_MARK_PATH_A}" stroke="url(#{gradient_id})" '
        f'stroke-width="4.08" stroke-linecap="round" stroke-linejoin="round"></path>'
        f'<path d="{_INSIGHT_MARK_PATH_B}" stroke="url(#{gradient_id})" '
        f'stroke-width="4.08" stroke-linecap="round" stroke-linejoin="round"></path>'
        f"</svg>"
    )


def insight_head_html(gradient_id: str) -> str:
    return (
        '<div class="ay-dash-insight-head">'
        f'<div class="ay-dash-insight-logo">{insight_logo_svg(gradient_id)}</div>'
        '<span class="ay-dash-insight-brand">Ayron</span>'
        '<span class="ay-dash-insight-kind">insight</span>'
        "</div>"
    )


def _find_div_block_end(html: str, open_end: int) -> int:
    depth = 1
    pos = open_end
    while pos < len(html) and depth > 0:
        next_open = _DIV_OPEN_RE.search(html, pos)
        next_close = _DIV_CLOSE_RE.search(html, pos)
        if next_close is None:
            return len(html)
        if next_open and next_open.start() < next_close.start():
            depth += 1
            pos = next_open.end()
            continue
        depth -= 1
        pos = next_close.end()
    return pos


def _replace_insight_logos(html: str, next_gradient_id) -> str:
    def replace_logo(_match: re.Match) -> str:
        return f'<div class="ay-dash-insight-logo">{insight_logo_svg(next_gradient_id())}</div>'

    return _INSIGHT_LOGO_DIV_RE.sub(replace_logo, html)


def _find_insight_head_spans(html: str) -> list[tuple[int, int]]:
    spans: list[tuple[int, int]] = []
    for match in _INSIGHT_HEAD_OPEN_RE.finditer(html):
        spans.append((match.start(), _find_div_block_end(html, match.end())))
    return spans


def _dedupe_insight_heads(html: str) -> str:
    spans = _find_insight_head_spans(html)
    if len(spans) <= 1:
        return html
    for start, end in reversed(spans[1:]):
        html = html[:start] + html[end:]
    return html


def _has_insight_head(html: str) -> bool:
    return _INSIGHT_HEAD_OPEN_RE.search(html) is not None


def _process_insight_card_inner(inner_html: str, next_gradient_id) -> str:
    normalized = _replace_insight_logos(inner_html, next_gradient_id)
    normalized = _dedupe_insight_heads(normalized)
    if _has_insight_head(normalized):
        return normalized
    normalized = _INSIGHT_ROGUE_ICON_RE.sub("", normalized, count=1)
    return insight_head_html(next_gradient_id()) + normalized


def normalize_insight_markup(body_html: str) -> str:
    if "ay-dash-card--insight" not in body_html:
        return body_html

    gradient_counter = 0

    def next_gradient_id() -> str:
        nonlocal gradient_counter
        gradient_counter += 1
        return f"ayron-insight-grad-{gradient_counter}"

    result: list[str] = []
    pos = 0
    for match in _INSIGHT_CARD_OPEN_RE.finditer(body_html):
        result.append(body_html[pos : match.start()])
        open_end = match.end()
        close_end = _find_div_block_end(body_html, open_end)
        inner_html = body_html[open_end : close_end - len("</div>")]
        result.append(match.group(0))
        result.append(_process_insight_card_inner(inner_html, next_gradient_id))
        result.append("</div>")
        pos = close_end
    result.append(body_html[pos:])
    return "".join(result)
