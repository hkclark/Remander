"""Centralized color palette and helpers for tags, dashboard buttons, and the color picker UI."""

# Full-spectrum palette of hex colors — 28 entries, clearly differentiated.
# Ordered: warm → cool → deep → neutrals.
PALETTE: list[str] = [
    # Reds / Pinks
    "#EF4444",  # red
    "#FCA5A5",  # pale red
    "#F43F5E",  # rose
    "#EC4899",  # pink
    # Oranges / Yellows
    "#F97316",  # orange
    "#FED7AA",  # pale orange
    "#F59E0B",  # amber
    "#EAB308",  # yellow
    "#FEF08A",  # pale yellow
    # Greens
    "#84CC16",  # lime
    "#22C55E",  # green
    "#86EFAC",  # pale green
    "#10B981",  # emerald
    "#14B8A6",  # teal
    # Blues / Purples
    "#06B6D4",  # cyan
    "#0EA5E9",  # sky
    "#3B82F6",  # blue
    "#93C5FD",  # pale blue
    "#6366F1",  # indigo
    "#8B5CF6",  # violet
    "#A855F7",  # purple
    # Deep / bold
    "#1E3A8A",  # navy
    "#14532D",  # forest green
    "#7F1D1D",  # crimson
    "#4C1D95",  # plum
    # Neutrals (well-differentiated steps)
    "#94A3B8",  # slate-400
    "#64748B",  # slate-500
    "#334155",  # slate-700
    "#1E293B",  # slate-800
    "#0F172A",  # near-black
]

DEFAULT_TAG_COLOR: str = "#64748B"  # slate-500
DEFAULT_BUTTON_COLOR: str = "#3B82F6"  # blue

# Mapping of legacy name-based color values → hex.
# Used for data migrations and as a fallback in tag_badge_classes().
NAME_TO_HEX: dict[str, str] = {
    "blue":    "#3B82F6",
    "sky":     "#0EA5E9",
    "cyan":    "#06B6D4",
    "teal":    "#14B8A6",
    "emerald": "#10B981",
    "green":   "#22C55E",
    "lime":    "#84CC16",
    "yellow":  "#EAB308",
    "amber":   "#F59E0B",
    "orange":  "#F97316",
    "rose":    "#F43F5E",
    "red":     "#EF4444",
    "pink":    "#EC4899",
    "fuchsia": "#D946EF",
    "purple":  "#A855F7",
    "violet":  "#8B5CF6",
    "indigo":  "#6366F1",
    "slate":   "#64748B",
    "gray":    "#6B7280",
    "zinc":    "#71717A",
    "stone":   "#78716C",
    "neutral": "#737373",
    "cobalt":  "#1E3A8A",
    "navy":    "#1E3A8A",
    "plum":    "#4C1D95",
    "grape":   "#7C3AED",
    "crimson": "#7F1D1D",
    "forest":  "#14532D",
    "jade":    "#059669",
    "russet":  "#92400E",
}


def text_color_for_bg(hex_color: str) -> str:
    """Return #ffffff or #000000 based on WCAG relative luminance of the background.

    Uses the WCAG 2.1 relative luminance formula to choose between black and white
    text to achieve sufficient contrast (threshold at L=0.179 ≈ 4.5:1 ratio).
    """
    h = hex_color.lstrip("#")
    r_raw = int(h[0:2], 16) / 255
    g_raw = int(h[2:4], 16) / 255
    b_raw = int(h[4:6], 16) / 255

    def linearize(c: float) -> float:
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    r = linearize(r_raw)
    g = linearize(g_raw)
    b = linearize(b_raw)
    luminance = 0.2126 * r + 0.7152 * g + 0.0722 * b
    return "#000000" if luminance > 0.179 else "#ffffff"


def hex_color_style(bg_hex: str | None, default: str = DEFAULT_TAG_COLOR) -> str:
    """Return an inline CSS style string for a colored element.

    Automatically picks black or white text based on background luminance.
    Falls back to `default` when bg_hex is None or empty.

    Example output: 'background-color: #3B82F6; color: #ffffff'
    """
    color = bg_hex if bg_hex else default
    # Normalize legacy name-based values (e.g. "blue" → "#3B82F6")
    if not color.startswith("#"):
        color = NAME_TO_HEX.get(color, default)
    text = text_color_for_bg(color)
    return f"background-color: {color}; color: {text}"
