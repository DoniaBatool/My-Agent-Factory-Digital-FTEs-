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


# --- edge cases + CLI layer (added for bulletproofing pass) ---

import subprocess as _subprocess_module
from pathlib import Path


class _Args:
    def __init__(self, **kw):
        self.__dict__.update(kw)


def test_hex_to_rgb_accepts_mixed_case_and_no_hash_prefix():
    assert tool.hex_to_rgb("AbCdEf") == (0xAB, 0xCD, 0xEF)


def test_hex_to_rgb_rejects_wrong_length():
    with pytest.raises(ValueError):
        tool.hex_to_rgb("#abcd")  # 4 hex digits, not 3 or 6
    with pytest.raises(ValueError):
        tool.hex_to_rgb("#abcdefa")  # 7 hex digits


def test_clamp_bounds_values_to_0_255():
    assert tool._clamp(-10) == 0
    assert tool._clamp(300) == 255
    assert tool._clamp(100) == 100


def test_check_wcag_compliance_exact_threshold_is_pass():
    # >= threshold, so exactly 4.5 for AA/normal must pass
    assert tool.check_wcag_compliance(4.5, level="AA", text_size="normal") is True


def test_check_wcag_compliance_just_below_threshold_fails():
    assert tool.check_wcag_compliance(4.499, level="AA", text_size="normal") is False


def test_check_wcag_compliance_aaa_large_exact_threshold():
    assert tool.check_wcag_compliance(4.5, level="AAA", text_size="large") is True
    assert tool.check_wcag_compliance(4.499, level="AAA", text_size="large") is False


def test_generate_color_scale_rejects_zero_steps():
    with pytest.raises(ValueError):
        tool.generate_color_scale("#336699", steps=0)


def test_generate_color_scale_single_step_returns_base_color_unchanged():
    scale = tool.generate_color_scale("#336699", steps=1)
    assert scale == ["#336699"]


def test_generate_color_scale_lightens_before_midpoint_and_darkens_after():
    scale = tool.generate_color_scale("#336699", steps=5)
    # step 0 should be lighter than the base (higher combined channel value)
    base_sum = sum(tool.hex_to_rgb("#336699"))
    first_sum = sum(tool.hex_to_rgb(scale[0]))
    last_sum = sum(tool.hex_to_rgb(scale[-1]))
    assert first_sum > base_sum
    assert last_sum < base_sum


def test_generate_color_scale_extreme_colors_stay_in_bounds():
    white_scale = tool.generate_color_scale("#ffffff", steps=5)
    black_scale = tool.generate_color_scale("#000000", steps=5)
    for hexval in white_scale + black_scale:
        r, g, b = tool.hex_to_rgb(hexval)
        assert 0 <= r <= 255 and 0 <= g <= 255 and 0 <= b <= 255


def test_spacing_scale_rejects_zero_or_negative_base():
    with pytest.raises(ValueError):
        tool.spacing_scale(base=0, steps=3)
    with pytest.raises(ValueError):
        tool.spacing_scale(base=-4, steps=3)


def test_spacing_scale_rejects_zero_or_negative_steps():
    with pytest.raises(ValueError):
        tool.spacing_scale(base=4, steps=0)
    with pytest.raises(ValueError):
        tool.spacing_scale(base=4, steps=-1)


def test_print_success_outputs_checkmark_and_message(capsys):
    tool.print_success("all good")
    out = capsys.readouterr().out
    assert "✓" in out
    assert "all good" in out


def test_print_error_outputs_cross_and_message(capsys):
    tool.print_error("broken")
    out = capsys.readouterr().out
    assert "✗" in out
    assert "broken" in out


def test_cmd_test_invokes_pytest_with_expected_args_and_returns_its_code(monkeypatch):
    captured = {}

    class _FakeCompletedProcess:
        returncode = 7

    def fake_run(cmd, *a, **kw):
        captured["cmd"] = cmd
        return _FakeCompletedProcess()

    monkeypatch.setattr(_subprocess_module, "run", fake_run)
    rc = tool.cmd_test(_Args())
    assert rc == 7
    cmd = captured["cmd"]
    assert cmd[0] == sys.executable
    assert "-m" in cmd and "pytest" in cmd
    assert cmd[-1] == "-q"
    expected_tests_dir = str(Path(tool.__file__).resolve().parent.parent / "tests")
    assert expected_tests_dir in cmd


def test_main_test_command_dispatches_via_func_and_exits_with_code(monkeypatch):
    class _FakeCompletedProcess:
        returncode = 5

    monkeypatch.setattr(_subprocess_module, "run", lambda *a, **kw: _FakeCompletedProcess())
    monkeypatch.setattr(sys, "argv", ["tool.py", "test"])
    with pytest.raises(SystemExit) as excinfo:
        tool.main()
    assert excinfo.value.code == 5


def test_main_missing_command_is_required_and_exits(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["tool.py"])
    with pytest.raises(SystemExit):
        tool.main()


def test_subprocess_no_args_hits_main_guard_and_exits_nonzero():
    script = Path(tool.__file__).resolve()
    result = _subprocess_module.run(
        [sys.executable, str(script)],
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode != 0
    assert "command" in result.stderr.lower() or "required" in result.stderr.lower()
