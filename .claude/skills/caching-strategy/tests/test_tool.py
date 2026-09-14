import importlib.util as _ilu
from pathlib import Path

_spec = _ilu.spec_from_file_location("caching_strategy_tool", Path(__file__).resolve().parent.parent / "scripts" / "tool.py")
tool = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(tool)


def test_build_cache_key_joins_parts_with_colon():
    assert tool.build_cache_key("user", 42, "profile") == "user:42:profile"


def test_build_cache_key_rejects_part_containing_colon():
    try:
        tool.build_cache_key("user", "42:evil")
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_suggest_ttl_matches_user_profile_pattern():
    assert tool.suggest_ttl("user_profile_v2") == 3600


def test_suggest_ttl_matches_price_pattern_with_short_ttl():
    assert tool.suggest_ttl("btc_price_feed") == 30


def test_suggest_ttl_falls_back_to_default_for_unknown_resource():
    assert tool.suggest_ttl("totally_unrelated_thing") == tool.DEFAULT_TTL


def test_keys_matching_invalidation_pattern_scopes_to_prefix():
    keys = ["user:42:profile", "user:42:tasks", "user:43:profile"]
    matches = tool.keys_matching_invalidation_pattern(keys, "user:42:*")
    assert matches == ["user:42:profile", "user:42:tasks"]


def test_keys_matching_invalidation_pattern_no_match_returns_empty():
    assert tool.keys_matching_invalidation_pattern(["a:1"], "b:*") == []
