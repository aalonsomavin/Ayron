COLORS = {
    "ink": "131316",
    "text": "18181B",
    "text_muted": "62626B",
    "text_subtle": "8A8A92",
    "text_inverse": "FFFFFF",
    "emphasis": "44444C",
    "heading": "2A2A30",
    "border": "E6E6E8",
    "border_subtle": "EDEDEE",
    "bg_subtle": "FAFAFA",
    "bg_muted": "F4F4F5",
    "accent": "3B6EF6",
    "info_bg": "EEF3FF",
    "info_border": "3B6EF6",
    "success_bg": "E9F7EF",
    "success_border": "16A34A",
    "warning_bg": "FDF3E7",
    "warning_border": "D97706",
    "danger_bg": "FDECEC",
    "danger_border": "DC2626",
}

VALID_CELL_FILLS = frozenset(
    {
        "default",
        "muted",
        "subtle",
        "accent_light",
        "success_light",
        "warning_light",
        "danger_light",
        "accent",
    }
)

DEFAULT_HEADER_FILL = "muted"
DEFAULT_SHEET_STRIPED = True

CELL_FILL_HEX = {
    "default": "FFFFFF",
    "muted": COLORS["bg_muted"],
    "subtle": COLORS["bg_subtle"],
    "accent_light": COLORS["info_bg"],
    "success_light": COLORS["success_bg"],
    "warning_light": COLORS["warning_bg"],
    "danger_light": COLORS["danger_bg"],
    "accent": COLORS["accent"],
}

CELL_TONE_COLORS = {
    "default": COLORS["text"],
    "success": COLORS["success_border"],
    "danger": COLORS["danger_border"],
    "warning": COLORS["warning_border"],
    "muted": COLORS["text_muted"],
}

ROW_STYLE_FILL_TOKENS = {
    "default": None,
    "subtotal": "subtle",
    "total": "muted",
}


def normalize_fill(fill: str) -> str:
    token = str(fill or "default").strip().lower()
    if token not in VALID_CELL_FILLS:
        raise ValueError(
            f"cell fill must be one of: {', '.join(sorted(VALID_CELL_FILLS))}"
        )
    return token


def normalize_sheet_style(style: dict | None) -> dict:
    if style is None:
        return {"striped": DEFAULT_SHEET_STRIPED, "header_fill": DEFAULT_HEADER_FILL}
    if not isinstance(style, dict):
        raise ValueError("sheet style must be an object")
    striped = style.get("striped", DEFAULT_SHEET_STRIPED)
    if not isinstance(striped, bool):
        raise ValueError("sheet style striped must be a boolean")
    header_fill = normalize_fill(style.get("header_fill", DEFAULT_HEADER_FILL))
    return {"striped": striped, "header_fill": header_fill}


def resolve_font_color(tone: str, *, header: bool = False, fill_token: str = "default") -> str:
    if fill_token == "accent":
        return COLORS["text_inverse"]
    if header:
        return COLORS["emphasis"]
    return CELL_TONE_COLORS.get(tone, COLORS["text"])


def resolve_fill_hex(fill_token: str) -> str:
    return CELL_FILL_HEX.get(fill_token, COLORS["bg_subtle"])


def resolve_row_fill_token(
    row_style: str,
    row_idx: int,
    *,
    sheet_striped: bool,
) -> str:
    row_token = ROW_STYLE_FILL_TOKENS.get(row_style)
    if row_token:
        return row_token
    if sheet_striped and row_idx % 2 == 0:
        return "subtle"
    return "default"


def resolve_cell_fill_token(
    cell_data: dict,
    *,
    row_style: str,
    row_idx: int,
    sheet_striped: bool,
) -> str:
    fill = cell_data.get("fill", "default")
    if fill != "default":
        return fill
    return resolve_row_fill_token(row_style, row_idx, sheet_striped=sheet_striped)


def resolve_border_color(row_style: str) -> str:
    if row_style == "total":
        return COLORS["border"]
    return COLORS["border_subtle"]


def fill_preview_class(fill_token: str) -> str | None:
    if fill_token == "default":
        return None
    return f"ay-sheet-preview__cell--fill-{fill_token}"


def cell_preview_fill_classes(
    cell_data: dict,
    *,
    row_style: str,
    row_idx: int,
    sheet_striped: bool,
) -> list[str]:
    explicit_fill = cell_data.get("fill", "default")
    if explicit_fill != "default":
        cls = fill_preview_class(explicit_fill)
        return [cls] if cls else []

    if row_style in ("total", "subtotal"):
        return [f"ay-sheet-preview__cell--{row_style}"]

    if sheet_striped and row_style == "default" and row_idx % 2 == 0:
        return ["ay-sheet-preview__cell--striped"]

    return []
