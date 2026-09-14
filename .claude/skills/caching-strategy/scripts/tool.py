#!/usr/bin/env python3
"""
Caching Strategy Tool - real cache-key building, TTL policy, invalidation matching

Commands: build-key, suggest-ttl, match-invalidation, test
"""
import argparse
import fnmatch
import re
import sys

TTL_POLICY = [
    (r"session", 1800),
    (r"user[_-]?profile", 3600),
    (r"static|asset", 86400),
    (r"price|quote|rate", 30),
    (r"search|query", 60),
]
DEFAULT_TTL = 300


def build_cache_key(namespace: str, *parts) -> str:
    """Deterministic, collision-resistant cache key. Rejects unsanitized
    ':' in parts (would silently create key collisions)."""
    for p in parts:
        if ":" in str(p):
            raise ValueError(f"cache key part {p!r} contains ':' -- would break key parsing/collide")
    return ":".join([namespace, *[str(p) for p in parts]])


def suggest_ttl(resource_name: str) -> int:
    """Suggest a TTL in seconds based on the resource name, using the
    first matching policy pattern; falls back to DEFAULT_TTL."""
    name = resource_name.lower()
    for pattern, ttl in TTL_POLICY:
        if re.search(pattern, name):
            return ttl
    return DEFAULT_TTL


def keys_matching_invalidation_pattern(all_keys, pattern: str):
    """Real glob-style matching (fnmatch), e.g. pattern 'user:42:*' should
    match 'user:42:profile' and 'user:42:tasks' but not 'user:43:profile'."""
    return sorted(k for k in all_keys if fnmatch.fnmatch(k, pattern))


# ---------------------------------------------------------------------------
# CLI ------------------------------------------------------------------
# ---------------------------------------------------------------------------

def cmd_build_key(args):
    try:
        print(build_cache_key(args.namespace, *args.parts.split(",")))
    except ValueError as e:
        print(str(e))
        return 1
    return 0


def cmd_suggest_ttl(args):
    print(suggest_ttl(args.resource))
    return 0


def cmd_match_invalidation(args):
    keys = keys_matching_invalidation_pattern(args.keys.split(","), args.pattern)
    print(", ".join(keys) if keys else "(no matches)")
    return 0


def cmd_test(args):
    ok = build_cache_key("user", 42, "profile") == "user:42:profile"
    try:
        build_cache_key("user", "42:evil")
        ok = False
    except ValueError:
        pass
    ok = ok and suggest_ttl("user_profile_v2") == 3600
    ok = ok and suggest_ttl("btc_price_feed") == 30
    ok = ok and suggest_ttl("totally_unrelated_thing") == DEFAULT_TTL
    matches = keys_matching_invalidation_pattern(["user:42:profile", "user:42:tasks", "user:43:profile"], "user:42:*")
    ok = ok and matches == ["user:42:profile", "user:42:tasks"]
    print("SELF-TEST PASS" if ok else "SELF-TEST FAIL")
    return 0 if ok else 1


def main():
    parser = argparse.ArgumentParser(description="Caching Strategy Tool")
    sub = parser.add_subparsers(dest="command")

    key_p = sub.add_parser("build-key")
    key_p.add_argument("--namespace", required=True)
    key_p.add_argument("--parts", required=True, help="comma-separated key parts")

    ttl_p = sub.add_parser("suggest-ttl")
    ttl_p.add_argument("resource")

    inv_p = sub.add_parser("match-invalidation")
    inv_p.add_argument("--keys", required=True, help="comma-separated existing keys")
    inv_p.add_argument("--pattern", required=True)

    sub.add_parser("test")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return 1

    commands = {
        "build-key": cmd_build_key,
        "suggest-ttl": cmd_suggest_ttl,
        "match-invalidation": cmd_match_invalidation,
        "test": cmd_test,
    }
    return commands[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
