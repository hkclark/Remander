"""Tests for the app_colors module."""

import pytest

from remander.app_colors import (
    DEFAULT_BUTTON_COLOR,
    DEFAULT_TAG_COLOR,
    NAME_TO_HEX,
    PALETTE,
    hex_color_style,
    text_color_for_bg,
)


class TestPalette:
    def test_palette_has_at_least_twenty_colors(self) -> None:
        assert len(PALETTE) >= 20

    def test_all_palette_entries_are_valid_hex(self) -> None:
        for color in PALETTE:
            assert color.startswith("#"), f"{color!r} missing #"
            assert len(color) == 7, f"{color!r} not 7 chars"
            int(color[1:], 16)  # raises ValueError if not valid hex

    def test_palette_has_no_duplicates(self) -> None:
        assert len(PALETTE) == len(set(PALETTE))

    def test_defaults_are_valid_hex(self) -> None:
        assert DEFAULT_TAG_COLOR.startswith("#")
        assert DEFAULT_BUTTON_COLOR.startswith("#")


class TestTextColorForBg:
    def test_white_bg_gets_black_text(self) -> None:
        assert text_color_for_bg("#ffffff") == "#000000"

    def test_black_bg_gets_white_text(self) -> None:
        assert text_color_for_bg("#000000") == "#ffffff"

    def test_light_color_gets_dark_text(self) -> None:
        # Yellow is very light
        assert text_color_for_bg("#EAB308") == "#000000"

    def test_dark_color_gets_light_text(self) -> None:
        # Navy is very dark
        assert text_color_for_bg("#1E3A8A") == "#ffffff"

    def test_dark_blue_gets_white_text(self) -> None:
        # #2563EB = Tailwind blue-600; dark enough for white text
        assert text_color_for_bg("#2563EB") == "#ffffff"

    def test_dark_red_gets_white_text(self) -> None:
        # #B91C1C = Tailwind red-700; dark enough for white text
        assert text_color_for_bg("#B91C1C") == "#ffffff"


class TestHexColorStyle:
    def test_returns_background_and_color_styles(self) -> None:
        # #1E3A8A = navy, dark enough to get white text
        style = hex_color_style("#1E3A8A")
        assert "background-color: #1E3A8A" in style
        assert "color: #ffffff" in style

    def test_none_uses_default(self) -> None:
        style = hex_color_style(None)
        assert "background-color:" in style

    def test_empty_string_uses_default(self) -> None:
        style = hex_color_style("")
        assert "background-color:" in style

    def test_custom_default(self) -> None:
        style = hex_color_style(None, default="#EF4444")
        assert "#EF4444" in style


class TestNameToHex:
    def test_blue_maps_to_hex(self) -> None:
        assert NAME_TO_HEX["blue"].startswith("#")

    def test_all_values_are_valid_hex(self) -> None:
        for name, hex_val in NAME_TO_HEX.items():
            assert hex_val.startswith("#"), f"{name!r} → {hex_val!r} missing #"
            assert len(hex_val) == 7, f"{name!r} → {hex_val!r} not 7 chars"
