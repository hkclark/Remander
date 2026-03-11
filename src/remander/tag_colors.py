"""Tag color palette and badge class helper for Jinja2 templates."""

_BADGE_CLASSES: dict[str, str] = {
    "blue":    "bg-blue-200 text-blue-800",
    "sky":     "bg-sky-200 text-sky-800",
    "cyan":    "bg-cyan-200 text-cyan-800",
    "teal":    "bg-teal-200 text-teal-800",
    "emerald": "bg-emerald-200 text-emerald-800",
    "green":   "bg-green-200 text-green-800",
    "lime":    "bg-lime-200 text-lime-800",
    "yellow":  "bg-yellow-200 text-yellow-800",
    "amber":   "bg-amber-200 text-amber-800",
    "orange":  "bg-orange-200 text-orange-800",
    "rose":    "bg-rose-200 text-rose-800",
    "red":     "bg-red-200 text-red-800",
    "pink":    "bg-pink-200 text-pink-800",
    "fuchsia": "bg-fuchsia-200 text-fuchsia-800",
    "purple":  "bg-purple-200 text-purple-800",
    "violet":  "bg-violet-200 text-violet-800",
    "indigo":  "bg-indigo-200 text-indigo-800",
    "slate":   "bg-slate-200 text-slate-800",
    "gray":    "bg-gray-200 text-gray-800",
    "zinc":    "bg-zinc-200 text-zinc-800",
}

_DEFAULT = "bg-gray-200 text-gray-800"

TAG_COLORS: list[str] = list(_BADGE_CLASSES.keys())

TAG_COLOR_LABELS: dict[str, str] = {
    "blue":    "Blue",
    "sky":     "Sky",
    "cyan":    "Cyan",
    "teal":    "Teal",
    "emerald": "Emerald",
    "green":   "Green",
    "lime":    "Lime",
    "yellow":  "Yellow",
    "amber":   "Amber",
    "orange":  "Orange",
    "rose":    "Rose",
    "red":     "Red",
    "pink":    "Pink",
    "fuchsia": "Fuchsia",
    "purple":  "Purple",
    "violet":  "Violet",
    "indigo":  "Indigo",
    "slate":   "Slate",
    "gray":    "Gray",
    "zinc":    "Zinc",
}


def tag_badge_classes(color: str | None) -> str:
    """Return Tailwind CSS classes for a tag badge given a color name."""
    if color is None:
        return _DEFAULT
    return _BADGE_CLASSES.get(color, _DEFAULT)
