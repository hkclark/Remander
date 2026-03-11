"""Tests for the tag_colors module."""

import pytest

from remander.tag_colors import TAG_COLOR_LABELS, TAG_COLORS, tag_badge_classes


class TestTagBadgeClasses:
    def test_none_returns_default_gray(self) -> None:
        classes = tag_badge_classes(None)
        assert "gray" in classes

    def test_known_color_returns_matching_classes(self) -> None:
        classes = tag_badge_classes("sky")
        assert "sky" in classes

    def test_unknown_color_falls_back_to_default(self) -> None:
        classes = tag_badge_classes("notacolor")
        assert "gray" in classes

    def test_each_color_has_bg_and_text_class(self) -> None:
        for color in TAG_COLORS:
            classes = tag_badge_classes(color)
            assert "bg-" in classes
            assert "text-" in classes

    def test_palette_has_at_least_fifteen_colors(self) -> None:
        assert len(TAG_COLORS) >= 15

    def test_color_labels_covers_every_palette_color(self) -> None:
        for color in TAG_COLORS:
            assert color in TAG_COLOR_LABELS, f"Missing label for {color!r}"

    def test_blue_returns_blue_classes(self) -> None:
        classes = tag_badge_classes("blue")
        assert "blue" in classes
