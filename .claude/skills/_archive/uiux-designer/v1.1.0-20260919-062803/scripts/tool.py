#!/usr/bin/env python3
"""
UI/UX Designer Tool - real WCAG contrast-ratio math and design-token scale generation.
"""
import argparse
import re
import sys


class Colors:
    GREEN, RED, END = '\033[92m', '\033[91m', '\033[0m'


def print_success(msg): print(f"{Colors.GREEN}✓{Colors.END} {msg}")
def print_error(msg): print(f"{Colors.RED}✗{Colors.END} {msg}")


def hex_to_rgb(hex_str: str) -> tuple:
    hex_str = hex_str.lstrip("#")
    if len(hex_str) == 3:
        hex_str = "".join(c * 2 for c in hex_str)
    if not re.fullmatch(r"[0-9a-fA-F]{6}", hex_str):
        raise ValueError(f"invalid hex color: {hex_str}")
    return tuple(int(hex_str[i:i + 2], 16) for i in (0, 2, 4))


def _relative_luminance(rgb: tuple) -> float:
    def channel(c):
        c = c / 255.0
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (channel(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(hex1: str, hex2: str) -> float:
    """Compute the WCAG 2.x contrast ratio between two hex colors (1.0 to 21.0)."""
    l1 = _relative_luminance(hex_to_rgb(hex1))
    l2 = _relative_luminance(hex_to_rgb(hex2))
    lighter, darker = max(l1, l2), min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


def check_wcag_compliance(ratio: float, level: str = "AA", text_size: str = "normal") -> bool:
    """Check a contrast ratio against WCAG 2.x thresholds."""
    level = level.upper()
    text_size = text_size.lower()
    thresholds = {
        ("AA", "normal"): 4.5,
        ("AA", "large"): 3.0,
        ("AAA", "normal"): 7.0,
        ("AAA", "large"): 4.5,
    }
    key = (level, text_size)
    if key not in thresholds:
        raise ValueError(f"unknown WCAG level/text_size combination: {level}/{text_size}")
    return ratio >= thresholds[key]


def _clamp(value):
    return max(0, min(255, value))


def generate_color_scale(base_hex: str, steps: int = 5) -> list:
    """Generate a lighter-to-darker scale around a base color (simple linear blend to white/black)."""
    if steps < 1:
        raise ValueError("steps must be >= 1")
    r, g, b = hex_to_rgb(base_hex)
    scale = []
    mid = steps // 2
    for i in range(steps):
        if i < mid:
            # lighten toward white
            factor = (mid - i) / (mid + 1) if mid else 0
            nr, ng, nb = (int(c + (255 - c) * factor) for c in (r, g, b))
        elif i > mid:
            factor = (i - mid) / (steps - mid)
            nr, ng, nb = (int(c * (1 - factor)) for c in (r, g, b))
        else:
            nr, ng, nb = r, g, b
        scale.append("#{:02x}{:02x}{:02x}".format(_clamp(nr), _clamp(ng), _clamp(nb)))
    return scale


def spacing_scale(base: int = 4, steps: int = 6) -> list:
    """Generate a linear design-token spacing scale, e.g. base=4 -> [4, 8, 12, 16, ...]."""
    if base <= 0 or steps <= 0:
        raise ValueError("base and steps must be positive")
    return [base * (i + 1) for i in range(steps)]


def cmd_test(args):
    import subprocess
    from pathlib import Path
    tests_dir = Path(__file__).resolve().parent.parent / "tests"
    result = subprocess.run([sys.executable, "-m", "pytest", "--import-mode=importlib", str(tests_dir), "-q"])
    return result.returncode


def main():
    parser = argparse.ArgumentParser(description="UI/UX Designer Tool")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("test").set_defaults(func=cmd_test)
    args = parser.parse_args()
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
