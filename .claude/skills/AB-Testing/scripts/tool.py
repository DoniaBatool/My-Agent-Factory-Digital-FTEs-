#!/usr/bin/env python3
"""
AB Testing Tool - real deterministic bucketing + significance check

Commands: assign-variant, check-significance, test
"""
import argparse
import hashlib
import sys


def assign_variant(user_id: str, test_name: str, traffic_split: dict) -> str:
    """Deterministic hash-based bucketing: same user_id + test_name always
    gets the same variant (no random.random() re-roll on every call), and
    the split proportions are respected in aggregate. traffic_split e.g.
    {"control": 0.5, "variant_a": 0.5}."""
    if abs(sum(traffic_split.values()) - 1.0) > 1e-6:
        raise ValueError(f"traffic_split must sum to 1.0, got {sum(traffic_split.values())}")
    digest = hashlib.sha256(f"{test_name}:{user_id}".encode()).hexdigest()
    bucket = (int(digest, 16) % 10000) / 10000.0
    cumulative = 0.0
    for variant, share in traffic_split.items():
        cumulative += share
        if bucket < cumulative:
            return variant
    return list(traffic_split)[-1]


def check_significance(control_conversions, control_total, variant_conversions, variant_total, z_threshold=1.96):
    """Real two-proportion z-test (no scipy dependency). Returns
    {significant, z_score, p_control, p_variant}. z_threshold=1.96 is the
    standard 95% confidence cutoff."""
    p_control = control_conversions / control_total
    p_variant = variant_conversions / variant_total
    p_pool = (control_conversions + variant_conversions) / (control_total + variant_total)
    se = (p_pool * (1 - p_pool) * (1 / control_total + 1 / variant_total)) ** 0.5
    z = (p_variant - p_control) / se if se > 0 else 0.0
    return {
        "significant": abs(z) >= z_threshold,
        "z_score": round(z, 4),
        "p_control": round(p_control, 4),
        "p_variant": round(p_variant, 4),
    }


# ---------------------------------------------------------------------------
# CLI ------------------------------------------------------------------
# ---------------------------------------------------------------------------

def cmd_assign_variant(args):
    import json
    split = json.loads(args.split)
    print(assign_variant(args.user_id, args.test_name, split))
    return 0


def cmd_check_significance(args):
    import json
    result = check_significance(args.control_conversions, args.control_total, args.variant_conversions, args.variant_total)
    print(json.dumps(result, indent=2))
    return 0


def cmd_test(args):
    v1 = assign_variant("user-1", "checkout-redesign", {"control": 0.5, "variant_a": 0.5})
    v2 = assign_variant("user-1", "checkout-redesign", {"control": 0.5, "variant_a": 0.5})
    ok = v1 == v2  # deterministic

    try:
        assign_variant("u", "t", {"control": 0.6, "variant_a": 0.6})
        ok = False
    except ValueError:
        pass

    result = check_significance(100, 1000, 150, 1000)
    ok = ok and result["significant"] is True
    weak = check_significance(100, 1000, 105, 1000)
    ok = ok and weak["significant"] is False
    print("SELF-TEST PASS" if ok else "SELF-TEST FAIL")
    return 0 if ok else 1


def main():
    parser = argparse.ArgumentParser(description="AB Testing Tool")
    sub = parser.add_subparsers(dest="command")

    assign_p = sub.add_parser("assign-variant")
    assign_p.add_argument("--user-id", required=True)
    assign_p.add_argument("--test-name", required=True)
    assign_p.add_argument("--split", required=True, help='JSON {"control": 0.5, "variant_a": 0.5}')

    sig_p = sub.add_parser("check-significance")
    sig_p.add_argument("--control-conversions", type=int, required=True)
    sig_p.add_argument("--control-total", type=int, required=True)
    sig_p.add_argument("--variant-conversions", type=int, required=True)
    sig_p.add_argument("--variant-total", type=int, required=True)

    sub.add_parser("test")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return 1

    commands = {
        "assign-variant": cmd_assign_variant,
        "check-significance": cmd_check_significance,
        "test": cmd_test,
    }
    return commands[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
