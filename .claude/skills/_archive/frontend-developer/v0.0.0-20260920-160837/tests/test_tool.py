import importlib.util as _ilu
import subprocess
import sys as _sys
from pathlib import Path

import pytest

_spec = _ilu.spec_from_file_location(
    "frontend_developer_tool", Path(__file__).resolve().parent.parent / "scripts" / "tool.py"
)
tool = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(tool)


class _Args:
    def __init__(self, **kw):
        for k, v in kw.items():
            setattr(self, k, v)


# ---------------------------------------------------------------------------
# print helpers
# ---------------------------------------------------------------------------

def test_print_success_shows_message(capsys):
    tool.print_success("done")
    assert "done" in capsys.readouterr().out


def test_print_error_shows_message(capsys):
    tool.print_error("oops")
    assert "oops" in capsys.readouterr().out


def test_print_warning_shows_message(capsys):
    tool.print_warning("careful")
    assert "careful" in capsys.readouterr().out


def test_print_info_shows_message(capsys):
    tool.print_info("fyi")
    assert "fyi" in capsys.readouterr().out


def test_print_header_shows_arrow_and_message(capsys):
    tool.print_header("Section")
    out = capsys.readouterr().out
    assert "==>" in out
    assert "Section" in out


# ---------------------------------------------------------------------------
# run_command
# ---------------------------------------------------------------------------

def test_run_command_success_returns_real_stdout():
    code, out, err = tool.run_command("echo hello-frontend")
    assert code == 0
    assert "hello-frontend" in out


def test_run_command_nonzero_exit_returns_real_code():
    code, out, err = tool.run_command("exit 9")
    assert code == 9


def test_run_command_exception_returns_default_error_tuple(monkeypatch):
    def boom(*a, **kw):
        raise RuntimeError("boom")

    monkeypatch.setattr(tool.subprocess, "run", boom)
    assert tool.run_command("anything") == (1, "", "Error")


# ---------------------------------------------------------------------------
# create_component
# ---------------------------------------------------------------------------

def test_create_component_client_default_has_use_client_directive(tmp_path):
    args = _Args(name="Widget", type=None, output=str(tmp_path))
    rc = tool.create_component(args)
    assert rc == 0
    content = (tmp_path / "Widget.tsx").read_text()
    assert content.startswith('"use client";')
    assert "interface WidgetProps {" in content
    assert "export function Widget({ }: WidgetProps) {" in content


def test_create_component_server_type_has_no_use_client_directive(tmp_path, capsys):
    args = _Args(name="Widget", type="server", output=str(tmp_path))
    tool.create_component(args)
    content = (tmp_path / "Widget.tsx").read_text()
    assert "use client" not in content
    assert content.startswith("import React")
    out = capsys.readouterr().out
    assert "SERVER Component" in out


def test_create_component_uses_default_output_dir_when_none(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    tool.create_component(_Args(name="Widget", type=None, output=None))
    assert (tmp_path / "src" / "components" / "Widget.tsx").exists()


def test_create_component_creates_nested_output_dirs_that_do_not_exist(tmp_path):
    nested = tmp_path / "a" / "b"
    tool.create_component(_Args(name="Widget", type=None, output=str(nested)))
    assert (nested / "Widget.tsx").exists()


# ---------------------------------------------------------------------------
# create_page
# ---------------------------------------------------------------------------

def test_create_page_strips_leading_and_trailing_slashes(tmp_path):
    args = _Args(route="/about/", output=str(tmp_path))
    rc = tool.create_page(args)
    assert rc == 0
    content = (tmp_path / "about" / "page.tsx").read_text()
    assert "About" in content
    assert 'title: "About"' in content


def test_create_page_uses_last_segment_of_nested_route(tmp_path):
    args = _Args(route="docs/getting-started", output=str(tmp_path))
    tool.create_page(args)
    content = (tmp_path / "docs" / "getting-started" / "page.tsx").read_text()
    assert "Getting-started" in content


def test_create_page_prints_route_info(tmp_path, capsys):
    tool.create_page(_Args(route="/about", output=str(tmp_path)))
    out = capsys.readouterr().out
    assert "Route: /about" in out
    assert "localhost:3000/about" in out


def test_create_page_uses_default_output_dir_when_none(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    tool.create_page(_Args(route="about", output=None))
    assert (tmp_path / "src" / "app" / "about" / "page.tsx").exists()


def test_create_page_can_be_regenerated_into_the_same_existing_route(tmp_path):
    # exercises mkdir(exist_ok=True): the output directory already exists on
    # the second call, so this must not raise FileExistsError.
    args = _Args(route="/about/", output=str(tmp_path))
    tool.create_page(args)
    rc = tool.create_page(args)
    assert rc == 0
    assert (tmp_path / "about" / "page.tsx").exists()


# ---------------------------------------------------------------------------
# create_hook
# ---------------------------------------------------------------------------

def test_create_hook_keeps_name_already_prefixed_with_use(tmp_path):
    args = _Args(name="useAuth", output=str(tmp_path))
    rc = tool.create_hook(args)
    assert rc == 0
    assert (tmp_path / "useAuth.ts").exists()
    content = (tmp_path / "useAuth.ts").read_text()
    assert "export function useAuth() {" in content


def test_create_hook_prefixes_and_capitalizes_name_without_use(tmp_path):
    args = _Args(name="auth", output=str(tmp_path))
    tool.create_hook(args)
    assert (tmp_path / "useAuth.ts").exists()


def test_create_hook_prefix_check_is_case_sensitive(tmp_path):
    # "Use" does not match the lowercase "use" prefix check, so it is
    # capitalized and re-prefixed rather than kept as-is.
    args = _Args(name="Use", output=str(tmp_path))
    tool.create_hook(args)
    assert (tmp_path / "useUse.ts").exists()


def test_create_hook_uses_default_output_dir_when_none(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    tool.create_hook(_Args(name="auth", output=None))
    assert (tmp_path / "src" / "hooks" / "useAuth.ts").exists()


# ---------------------------------------------------------------------------
# setup_shadcn
# ---------------------------------------------------------------------------

def test_setup_shadcn_default_components_all_succeed(monkeypatch, capsys):
    monkeypatch.setattr(tool, "run_command", lambda cmd, timeout=300: (0, "installed", ""))
    rc = tool.setup_shadcn(_Args(components=None))
    assert rc == 0
    out = capsys.readouterr().out
    assert "Installed: button" in out
    assert "Installed: input" in out
    assert "Installed: card" in out


def test_setup_shadcn_custom_components_strips_whitespace(monkeypatch, capsys):
    seen = []

    def fake(cmd, timeout=300):
        seen.append(cmd)
        return 0, "", ""

    monkeypatch.setattr(tool, "run_command", fake)
    tool.setup_shadcn(_Args(components=" dialog , tooltip "))
    assert any("add dialog -y" in c for c in seen)
    assert any("add tooltip -y" in c for c in seen)


def test_setup_shadcn_reports_failure_for_a_component(monkeypatch, capsys):
    def fake(cmd, timeout=300):
        if "button" in cmd:
            return 1, "", "network error"
        return 0, "", ""

    monkeypatch.setattr(tool, "run_command", fake)
    tool.setup_shadcn(_Args(components="button,input"))
    out = capsys.readouterr().out
    assert "Failed: button" in out
    assert "network error" in out
    assert "Installed: input" in out


# ---------------------------------------------------------------------------
# generate_api_client
# ---------------------------------------------------------------------------

def test_generate_api_client_default_base_url(tmp_path, capsys):
    args = _Args(base_url=None, output=str(tmp_path))
    rc = tool.generate_api_client(args)
    assert rc == 0
    content = (tmp_path / "api-client.ts").read_text()
    assert 'process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api"' in content
    assert "static async get<T>" in content
    assert "static async post<T>" in content
    assert "static async put<T>" in content
    assert "static async delete<T>" in content
    out = capsys.readouterr().out
    assert "http://localhost:8000/api" in out


def test_generate_api_client_custom_base_url(tmp_path):
    args = _Args(base_url="https://api.example.com", output=str(tmp_path))
    tool.generate_api_client(args)
    content = (tmp_path / "api-client.ts").read_text()
    assert 'process.env.NEXT_PUBLIC_API_URL || "https://api.example.com"' in content


def test_generate_api_client_uses_default_output_dir_when_none(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    tool.generate_api_client(_Args(base_url=None, output=None))
    assert (tmp_path / "src" / "lib" / "api-client.ts").exists()


# ---------------------------------------------------------------------------
# create_form
# ---------------------------------------------------------------------------

def test_create_form_default_fields(tmp_path):
    args = _Args(name="Signup", fields=None, output=str(tmp_path))
    rc = tool.create_form(args)
    assert rc == 0
    content = (tmp_path / "Signup.tsx").read_text()
    assert "name: string;" in content
    assert "email: string;" in content
    assert 'id="name"' in content
    assert 'type="text"' in content
    assert 'id="email"' in content
    assert 'type="email"' in content
    assert "useForm<SignupData>()" in content


def test_create_form_default_fields_when_empty_string(tmp_path):
    args = _Args(name="Signup", fields="", output=str(tmp_path))
    tool.create_form(args)
    content = (tmp_path / "Signup.tsx").read_text()
    assert "name: string;" in content
    assert "email: string;" in content


def test_create_form_custom_fields_and_label_capitalization(tmp_path):
    args = _Args(name="Contact", fields="phone:tel,message:textarea", output=str(tmp_path))
    tool.create_form(args)
    content = (tmp_path / "Contact.tsx").read_text()
    assert "phone: string;" in content
    assert "message: string;" in content
    assert '<Label htmlFor="phone">Phone</Label>' in content
    assert 'type="tel"' in content
    assert 'register("phone", { required: true })' in content


def test_create_form_skips_malformed_field_without_colon(tmp_path):
    args = _Args(name="Contact", fields="phone:tel,badfield", output=str(tmp_path))
    tool.create_form(args)
    content = (tmp_path / "Contact.tsx").read_text()
    assert "badfield" not in content
    assert "phone: string;" in content


def test_create_form_uses_default_output_dir_when_none(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    tool.create_form(_Args(name="Signup", fields=None, output=None))
    assert (tmp_path / "src" / "components" / "forms" / "Signup.tsx").exists()


# ---------------------------------------------------------------------------
# optimize_bundle
# ---------------------------------------------------------------------------

def test_optimize_bundle_prints_recommendations(capsys):
    rc = tool.optimize_bundle(_Args())
    assert rc == 0
    out = capsys.readouterr().out
    assert "bundle-analyzer" in out
    assert "React.lazy()" in out
    assert "Optimization guide complete" in out


# ---------------------------------------------------------------------------
# audit
# ---------------------------------------------------------------------------

def _fake_run_command_for(pattern_to_result):
    def fake(cmd, timeout=300):
        for substr, result in pattern_to_result.items():
            if substr in cmd:
                return result
        return 1, "", ""

    return fake


def test_audit_no_issues_when_all_counts_zero(monkeypatch, capsys):
    monkeypatch.setattr(
        tool,
        "run_command",
        _fake_run_command_for(
            {
                ': any"': (0, "0", ""),
                "<img": (0, "0", ""),
                "console.log": (0, "0", ""),
            }
        ),
    )
    rc = tool.audit(_Args())
    assert rc == 0
    assert "No critical issues found" in capsys.readouterr().out


def test_audit_flags_any_types_when_count_positive(monkeypatch, capsys):
    monkeypatch.setattr(
        tool,
        "run_command",
        _fake_run_command_for(
            {
                ': any"': (0, "4", ""),
                "<img": (0, "0", ""),
                "console.log": (0, "0", ""),
            }
        ),
    )
    tool.audit(_Args())
    out = capsys.readouterr().out
    assert "Found 4 'any' types" in out


def test_audit_flags_missing_alt_tags_when_count_positive(monkeypatch, capsys):
    monkeypatch.setattr(
        tool,
        "run_command",
        _fake_run_command_for(
            {
                ': any"': (0, "0", ""),
                "<img": (0, "2", ""),
                "console.log": (0, "0", ""),
            }
        ),
    )
    tool.audit(_Args())
    out = capsys.readouterr().out
    assert "Found 2 images without alt tags" in out


def test_audit_flags_console_log_when_count_positive(monkeypatch, capsys):
    monkeypatch.setattr(
        tool,
        "run_command",
        _fake_run_command_for(
            {
                ': any"': (0, "0", ""),
                "<img": (0, "0", ""),
                "console.log": (0, "7", ""),
            }
        ),
    )
    tool.audit(_Args())
    out = capsys.readouterr().out
    assert "Found 7 console.log statements" in out


def test_audit_skips_checks_when_run_command_reports_nonzero_exit(monkeypatch, capsys):
    # code != 0 must short-circuit the whole check, regardless of stdout.
    monkeypatch.setattr(
        tool,
        "run_command",
        _fake_run_command_for(
            {
                ': any"': (1, "99", ""),
                "<img": (1, "99", ""),
                "console.log": (1, "99", ""),
            }
        ),
    )
    tool.audit(_Args())
    out = capsys.readouterr().out
    assert "No critical issues found" in out


def test_audit_prints_recommendations_footer(capsys, monkeypatch):
    monkeypatch.setattr(tool, "run_command", lambda cmd, timeout=300: (0, "0", ""))
    tool.audit(_Args())
    out = capsys.readouterr().out
    assert "npm run lint" in out
    assert "lighthouse" in out


# ---------------------------------------------------------------------------
# main() / CLI dispatch
# ---------------------------------------------------------------------------

def test_main_with_no_command_prints_help_and_returns_1(monkeypatch, capsys):
    monkeypatch.setattr(_sys, "argv", ["tool.py"])
    rc = tool.main()
    out = capsys.readouterr().out
    assert rc == 1
    assert "usage" in out.lower()


def test_main_create_component_end_to_end(monkeypatch, tmp_path):
    monkeypatch.setattr(
        _sys, "argv", ["tool.py", "create-component", "--name", "Card", "--output", str(tmp_path)]
    )
    rc = tool.main()
    assert rc == 0
    assert (tmp_path / "Card.tsx").exists()


def test_main_create_page_end_to_end(monkeypatch, tmp_path):
    monkeypatch.setattr(
        _sys, "argv", ["tool.py", "create-page", "--route", "/pricing", "--output", str(tmp_path)]
    )
    rc = tool.main()
    assert rc == 0
    assert (tmp_path / "pricing" / "page.tsx").exists()


def test_main_create_hook_end_to_end(monkeypatch, tmp_path):
    monkeypatch.setattr(_sys, "argv", ["tool.py", "create-hook", "--name", "cart", "--output", str(tmp_path)])
    rc = tool.main()
    assert rc == 0
    assert (tmp_path / "useCart.ts").exists()


def test_main_setup_shadcn_end_to_end(monkeypatch, capsys):
    monkeypatch.setattr(tool, "run_command", lambda cmd, timeout=300: (0, "", ""))
    monkeypatch.setattr(_sys, "argv", ["tool.py", "setup-shadcn", "--components", "button"])
    rc = tool.main()
    assert rc == 0
    assert "Installed: button" in capsys.readouterr().out


def test_main_generate_api_client_end_to_end(monkeypatch, tmp_path):
    monkeypatch.setattr(
        _sys, "argv", ["tool.py", "generate-api-client", "--output", str(tmp_path)]
    )
    rc = tool.main()
    assert rc == 0
    assert (tmp_path / "api-client.ts").exists()


def test_main_create_form_end_to_end(monkeypatch, tmp_path):
    monkeypatch.setattr(
        _sys, "argv", ["tool.py", "create-form", "--name", "Login", "--output", str(tmp_path)]
    )
    rc = tool.main()
    assert rc == 0
    assert (tmp_path / "Login.tsx").exists()


def test_main_optimize_bundle_end_to_end(monkeypatch, capsys):
    monkeypatch.setattr(_sys, "argv", ["tool.py", "optimize-bundle"])
    rc = tool.main()
    assert rc == 0
    assert "Optimization guide complete" in capsys.readouterr().out


def test_main_audit_end_to_end(monkeypatch, capsys):
    monkeypatch.setattr(tool, "run_command", lambda cmd, timeout=300: (0, "0", ""))
    monkeypatch.setattr(_sys, "argv", ["tool.py", "audit"])
    rc = tool.main()
    assert rc == 0
    assert "No critical issues found" in capsys.readouterr().out


def test_main_create_component_missing_required_name_exits(monkeypatch):
    monkeypatch.setattr(_sys, "argv", ["tool.py", "create-component"])
    with pytest.raises(SystemExit):
        tool.main()


def test_main_create_page_missing_required_route_exits(monkeypatch):
    monkeypatch.setattr(_sys, "argv", ["tool.py", "create-page"])
    with pytest.raises(SystemExit):
        tool.main()


def test_main_create_hook_missing_required_name_exits(monkeypatch):
    monkeypatch.setattr(_sys, "argv", ["tool.py", "create-hook"])
    with pytest.raises(SystemExit):
        tool.main()


def test_main_create_form_missing_required_name_exits(monkeypatch):
    monkeypatch.setattr(_sys, "argv", ["tool.py", "create-form"])
    with pytest.raises(SystemExit):
        tool.main()


def test_main_create_component_rejects_invalid_type_choice(monkeypatch):
    monkeypatch.setattr(
        _sys, "argv", ["tool.py", "create-component", "--name", "X", "--type", "bogus"]
    )
    with pytest.raises(SystemExit):
        tool.main()


def test_main_unknown_command_exits(monkeypatch):
    monkeypatch.setattr(_sys, "argv", ["tool.py", "not-a-real-command"])
    with pytest.raises(SystemExit):
        tool.main()


# ---------------------------------------------------------------------------
# subprocess smoke tests (real __main__ entrypoint end to end)
# ---------------------------------------------------------------------------

def test_cli_subprocess_smoke_test_optimize_bundle():
    script = Path(__file__).resolve().parent.parent / "scripts" / "tool.py"
    proc = subprocess.run(
        [_sys.executable, str(script), "optimize-bundle"], capture_output=True, text=True, timeout=30
    )
    assert proc.returncode == 0
    assert "Optimization guide complete" in proc.stdout


def test_cli_subprocess_smoke_test_no_command_returns_nonzero():
    script = Path(__file__).resolve().parent.parent / "scripts" / "tool.py"
    proc = subprocess.run([_sys.executable, str(script)], capture_output=True, text=True, timeout=30)
    assert proc.returncode == 1
    assert "usage" in proc.stdout.lower()


def test_cli_subprocess_smoke_test_create_component_writes_real_file(tmp_path):
    script = Path(__file__).resolve().parent.parent / "scripts" / "tool.py"
    proc = subprocess.run(
        [_sys.executable, str(script), "create-component", "--name", "Widget", "--output", str(tmp_path)],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert proc.returncode == 0
    assert (tmp_path / "Widget.tsx").exists()
