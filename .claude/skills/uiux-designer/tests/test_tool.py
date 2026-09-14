import importlib.util
import sys
from pathlib import Path

_MODULE_PATH = Path(__file__).resolve().parent.parent / "scripts" / "tool.py"
_spec = importlib.util.spec_from_file_location("uiux_designer_tool", _MODULE_PATH)
tool = importlib.util.module_from_spec(_spec)
sys.modules["uiux_designer_tool"] = tool
_spec.loader.exec_module(tool)

import pytest


def test_hex_to_rgb_full_form():
    assert tool.hex_to_rgb("#ffffff") == (255, 255, 255)


def test_hex_to_rgb_short_form():
    assert tool.hex_to_rgb("#fff") == (255, 255, 255)


def test_hex_to_rgb_rejects_invalid():
    with pytest.raises(ValueError):
        tool.hex_to_rgb("not-a-color")


def test_contrast_ratio_black_on_white_is_max():
    ratio = tool.contrast_ratio("#000000", "#ffffff")
    assert round(ratio, 2) == 21.0


def test_contrast_ratio_same_color_is_one():
    ratio = tool.contrast_ratio("#336699", "#336699")
    assert round(ratio, 2) == 1.0


def test_contrast_ratio_is_symmetric():
    a = tool.contrast_ratio("#333333", "#eeeeee")
    b = tool.contrast_ratio("#eeeeee", "#333333")
    assert round(a, 4) == round(b, 4)


def test_check_wcag_compliance_passes_high_contrast():
    assert tool.check_wcag_compliance(21.0, level="AAA", text_size="normal") is True


def test_check_wcag_compliance_fails_low_contrast_normal_text():
    assert tool.check_wcag_compliance(2.0, level="AA", text_size="normal") is False


def test_check_wcag_compliance_large_text_lower_threshold():
    assert tool.check_wcag_compliance(3.5, level="AA", text_size="large") is True
    assert tool.check_wcag_compliance(3.5, level="AA", text_size="normal") is False


def test_check_wcag_compliance_rejects_unknown_combo():
    with pytest.raises(ValueError):
        tool.check_wcag_compliance(5.0, level="A", text_size="normal")


def test_generate_color_scale_length_and_midpoint():
    scale = tool.generate_color_scale("#336699", steps=5)
    assert len(scale) == 5
    assert scale[2] == "#336699"


def test_spacing_scale_linear_progression():
    assert tool.spacing_scale(base=4, steps=6) == [4, 8, 12, 16, 20, 24]
