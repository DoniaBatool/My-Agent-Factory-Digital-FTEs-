#!/usr/bin/env python3
"""
Connection Pooling Tool - real pool-size calculation + config generation

Commands: calculate-pool-size, generate-config, test
"""
import argparse
import json
import sys


def calculate_pool_size(num_instances: int, db_max_connections: int, reserved_for_admin: int = 5):
    """Real formula: distribute the DB's max connections across app
    instances, minus a reserved slice for admin/migrations, minimum 1 per
    instance. Returns per-instance pool_size and max_overflow."""
    if num_instances <= 0:
        raise ValueError("num_instances must be positive")
    available = max(db_max_connections - reserved_for_admin, num_instances)
    per_instance_total = available // num_instances
    pool_size = max(1, int(per_instance_total * 0.7))
    max_overflow = max(0, per_instance_total - pool_size)
    return {"pool_size": pool_size, "max_overflow": max_overflow, "per_instance_total": per_instance_total}


def generate_sqlalchemy_config(pool_size: int, max_overflow: int, pool_recycle=1800, pool_pre_ping=True):
    return {
        "pool_size": pool_size,
        "max_overflow": max_overflow,
        "pool_recycle": pool_recycle,
        "pool_pre_ping": pool_pre_ping,
    }


# ---------------------------------------------------------------------------
# CLI ------------------------------------------------------------------
# ---------------------------------------------------------------------------

def cmd_calculate_pool_size(args):
    try:
        result = calculate_pool_size(args.instances, args.db_max_connections, args.reserved)
    except ValueError as e:
        print(str(e))
        return 1
    print(json.dumps(result, indent=2))
    return 0


def cmd_generate_config(args):
    config = generate_sqlalchemy_config(args.pool_size, args.max_overflow, args.pool_recycle, not args.no_pre_ping)
    print(json.dumps(config, indent=2))
    return 0


def cmd_test(args):
    result = calculate_pool_size(num_instances=4, db_max_connections=100, reserved_for_admin=10)
    ok = result["per_instance_total"] == 22
    ok = ok and result["pool_size"] + result["max_overflow"] <= result["per_instance_total"]
    total_across_instances = (result["pool_size"] + result["max_overflow"]) * 4
    ok = ok and total_across_instances <= 90  # never exceeds available budget
    try:
        calculate_pool_size(0, 100)
        ok = False
    except ValueError:
        pass
    config = generate_sqlalchemy_config(10, 5)
    ok = ok and config["pool_pre_ping"] is True
    print("SELF-TEST PASS" if ok else "SELF-TEST FAIL")
    return 0 if ok else 1


def main():
    parser = argparse.ArgumentParser(description="Connection Pooling Tool")
    sub = parser.add_subparsers(dest="command")

    calc_p = sub.add_parser("calculate-pool-size")
    calc_p.add_argument("--instances", type=int, required=True)
    calc_p.add_argument("--db-max-connections", type=int, required=True)
    calc_p.add_argument("--reserved", type=int, default=5)

    cfg_p = sub.add_parser("generate-config")
    cfg_p.add_argument("--pool-size", type=int, required=True)
    cfg_p.add_argument("--max-overflow", type=int, required=True)
    cfg_p.add_argument("--pool-recycle", type=int, default=1800)
    cfg_p.add_argument("--no-pre-ping", action="store_true")

    sub.add_parser("test")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return 1

    commands = {
        "calculate-pool-size": cmd_calculate_pool_size,
        "generate-config": cmd_generate_config,
        "test": cmd_test,
    }
    return commands[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
