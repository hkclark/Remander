"""Tag color palette and badge class helper for Jinja2 templates."""

_BADGE_CLASSES: dict[str, str] = {
    # — Standard palette (vibrant background, very dark text) —
    "blue":    "bg-blue-300 text-blue-900",
    "sky":     "bg-sky-300 text-sky-900",
    "cyan":    "bg-cyan-300 text-cyan-900",
    "teal":    "bg-teal-300 text-teal-900",
    "emerald": "bg-emerald-300 text-emerald-900",
    "green":   "bg-green-300 text-green-900",
    "lime":    "bg-lime-300 text-lime-900",
    "yellow":  "bg-yellow-300 text-yellow-900",
    "amber":   "bg-amber-300 text-amber-900",
    "orange":  "bg-orange-300 text-orange-900",
    "rose":    "bg-rose-300 text-rose-900",
    "red":     "bg-red-300 text-red-900",
    "pink":    "bg-pink-300 text-pink-900",
    "fuchsia": "bg-fuchsia-300 text-fuchsia-900",
    "purple":  "bg-purple-300 text-purple-900",
    "violet":  "bg-violet-300 text-violet-900",
    "indigo":  "bg-indigo-300 text-indigo-900",
    # — Neutral shades —
    "slate":   "bg-slate-300 text-slate-900",
    "gray":    "bg-gray-300 text-gray-900",
    "zinc":    "bg-zinc-300 text-zinc-900",
    "stone":   "bg-stone-300 text-stone-900",
    "neutral": "bg-neutral-300 text-neutral-900",
    # — Deep/solid bold (saturated background, white text) —
    "cobalt":  "bg-blue-600 text-white",
    "navy":    "bg-indigo-800 text-white",
    "plum":    "bg-purple-700 text-white",
    "grape":   "bg-violet-700 text-white",
    "crimson": "bg-red-700 text-white",
    "forest":  "bg-green-800 text-white",
    "jade":    "bg-teal-600 text-white",
    "russet":  "bg-orange-700 text-white",
}

_DEFAULT = "bg-gray-300 text-gray-900"

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
    "stone":   "Stone",
    "neutral": "Neutral",
    "cobalt":  "Cobalt",
    "navy":    "Navy",
    "plum":    "Plum",
    "grape":   "Grape",
    "crimson": "Crimson",
    "forest":  "Forest",
    "jade":    "Jade",
    "russet":  "Russet",
}


def tag_badge_classes(color: str | None) -> str:
    """Return Tailwind CSS classes for a tag badge given a color name."""
    if color is None:
        return _DEFAULT
    return _BADGE_CLASSES.get(color, _DEFAULT)
