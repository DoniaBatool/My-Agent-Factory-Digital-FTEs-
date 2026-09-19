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


# --- edge cases + CLI layer (added for bulletproofing pass) ---
import subprocess
import sys
from types import SimpleNamespace
import pytest


def test_build_cache_key_with_no_extra_parts_returns_bare_namespace():
    assert tool.build_cache_key("ns") == "ns"


def test_build_cache_key_rejects_colon_in_any_part_position():
    with pytest.raises(ValueError):
        tool.build_cache_key("user", "42", "evil:part")


def test_suggest_ttl_matches_session_pattern():
    assert tool.suggest_ttl("session_token") == 1800


def test_suggest_ttl_matches_static_pattern():
    assert tool.suggest_ttl("static_bundle") == 86400


def test_suggest_ttl_matches_asset_pattern():
    assert tool.suggest_ttl("cdn_asset_manifest") == 86400


def test_suggest_ttl_matches_quote_and_rate_patterns():
    assert tool.suggest_ttl("fx_quote") == 30
    assert tool.suggest_ttl("interest_rate") == 30


def test_suggest_ttl_matches_search_pattern():
    assert tool.suggest_ttl("search_results") == 60


def test_suggest_ttl_is_case_insensitive():
    assert tool.suggest_ttl("USER_PROFILE") == 3600


def test_suggest_ttl_first_matching_pattern_wins_by_policy_order():
    # "session" appears earlier than "price" in TTL_POLICY, so a name
    # matching both patterns must resolve via the session rule (1800), not
    # the price rule (30).
    assert tool.suggest_ttl("session_price_cache") == 1800


def test_keys_matching_invalidation_pattern_supports_question_mark_wildcard():
    keys = ["user:1:tasks", "user:12:tasks"]
    matches = tool.keys_matching_invalidation_pattern(keys, "user:?:tasks")
    assert matches == ["user:1:tasks"]


def test_keys_matching_invalidation_pattern_is_case_sensitive():
    matches = tool.keys_matching_invalidation_pattern(["User:1"], "user:1")
    assert matches == []


def test_keys_matching_invalidation_pattern_returns_sorted_order():
    keys = ["user:9:tasks", "user:2:tasks", "user:5:tasks"]
    matches = tool.keys_matching_invalidation_pattern(keys, "user:*:tasks")
    assert matches == sorted(keys)


def test_cmd_build_key_prints_key_and_returns_zero(capsys):
    args = SimpleNamespace(namespace="user", parts="42,profile")
    rc = tool.cmd_build_key(args)
    out = capsys.readouterr().out.strip()
    assert rc == 0
    assert out == "user:42:profile"


def test_cmd_build_key_error_prints_message_and_returns_one(capsys):
    args = SimpleNamespace(namespace="user", parts="42:evil")
    rc = tool.cmd_build_key(args)
    out = capsys.readouterr().out
    assert rc == 1
    assert "contains ':'" in out


def test_cmd_suggest_ttl_prints_ttl(capsys):
    args = SimpleNamespace(resource="user_profile")
    rc = tool.cmd_suggest_ttl(args)
    out = capsys.readouterr().out.strip()
    assert rc == 0
    assert out == "3600"


def test_cmd_match_invalidation_prints_matches(capsys):
    args = SimpleNamespace(keys="user:42:profile,user:42:tasks,user:43:profile", pattern="user:42:*")
    rc = tool.cmd_match_invalidation(args)
    out = capsys.readouterr().out.strip()
    assert rc == 0
    assert out == "user:42:profile, user:42:tasks"


def test_cmd_match_invalidation_no_matches_prints_placeholder(capsys):
    args = SimpleNamespace(keys="a:1", pattern="b:*")
    rc = tool.cmd_match_invalidation(args)
    out = capsys.readouterr().out.strip()
    assert rc == 0
    assert out == "(no matches)"


def test_cmd_test_returns_zero_and_prints_pass(capsys):
    rc = tool.cmd_test(SimpleNamespace())
    out = capsys.readouterr().out
    assert rc == 0
    assert "SELF-TEST PASS" in out


def test_main_dispatches_build_key_end_to_end(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["tool.py", "build-key", "--namespace", "user", "--parts", "42,profile"])
    rc = tool.main()
    out = capsys.readouterr().out.strip()
    assert rc == 0
    assert out == "user:42:profile"


def test_main_dispatches_suggest_ttl_end_to_end(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["tool.py", "suggest-ttl", "user_profile"])
    rc = tool.main()
    out = capsys.readouterr().out.strip()
    assert rc == 0
    assert out == "3600"


def test_main_dispatches_match_invalidation_end_to_end(monkeypatch, capsys):
    monkeypatch.setattr(
        sys, "argv",
        ["tool.py", "match-invalidation", "--keys", "user:42:profile,user:43:profile", "--pattern", "user:42:*"],
    )
    rc = tool.main()
    out = capsys.readouterr().out.strip()
    assert rc == 0
    assert out == "user:42:profile"


def test_main_dispatches_test_subcommand_end_to_end(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["tool.py", "test"])
    rc = tool.main()
    out = capsys.readouterr().out
    assert rc == 0
    assert "SELF-TEST PASS" in out


def test_main_with_no_command_prints_help_and_returns_one(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["tool.py"])
    rc = tool.main()
    captured = capsys.readouterr()
    assert rc == 1
    assert "usage" in captured.out.lower()


def test_main_build_key_missing_required_namespace_exits(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["tool.py", "build-key", "--parts", "42,profile"])
    with pytest.raises(SystemExit):
        tool.main()


def test_main_build_key_missing_required_parts_exits(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["tool.py", "build-key", "--namespace", "user"])
    with pytest.raises(SystemExit):
        tool.main()


def test_main_suggest_ttl_missing_positional_resource_exits(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["tool.py", "suggest-ttl"])
    with pytest.raises(SystemExit):
        tool.main()


def test_main_match_invalidation_missing_required_keys_exits(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["tool.py", "match-invalidation", "--pattern", "user:*"])
    with pytest.raises(SystemExit):
        tool.main()


def test_main_match_invalidation_missing_required_pattern_exits(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["tool.py", "match-invalidation", "--keys", "a:1"])
    with pytest.raises(SystemExit):
        tool.main()


def test_subprocess_smoke_runs_as_script_and_exercises_main_guard():
    from pathlib import Path as _Path
    script = _Path(__file__).resolve().parent.parent / "scripts" / "tool.py"
    proc = subprocess.run([sys.executable, str(script), "test"], capture_output=True, text=True)
    assert proc.returncode == 0
    assert "SELF-TEST PASS" in proc.stdout
