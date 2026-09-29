import importlib.util as _ilu
import json
import subprocess
import sys as _sys
from pathlib import Path

import pytest

_spec = _ilu.spec_from_file_location(
    "backend_developer_tool", Path(__file__).resolve().parent.parent / "scripts" / "tool.py"
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

def test_print_success_shows_check_and_message(capsys):
    tool.print_success("all good")
    out = capsys.readouterr().out
    assert "all good" in out


def test_print_error_shows_x_and_message(capsys):
    tool.print_error("bad thing")
    out = capsys.readouterr().out
    assert "bad thing" in out


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
    code, out, err = tool.run_command("echo hello-backend")
    assert code == 0
    assert "hello-backend" in out


def test_run_command_nonzero_exit_returns_real_code():
    code, out, err = tool.run_command("exit 7")
    assert code == 7


def test_run_command_exception_returns_default_error_tuple(monkeypatch):
    def boom(*a, **kw):
        raise RuntimeError("subprocess exploded")

    monkeypatch.setattr(tool.subprocess, "run", boom)
    code, out, err = tool.run_command("anything")
    assert (code, out, err) == (1, "", "Error")


# ---------------------------------------------------------------------------
# scaffold_endpoint
# ---------------------------------------------------------------------------

def test_scaffold_endpoint_writes_expected_crud_routes(tmp_path, capsys):
    args = _Args(name="order", output=str(tmp_path))
    rc = tool.scaffold_endpoint(args)
    assert rc == 0
    content = (tmp_path / "order.py").read_text()
    assert 'router = APIRouter(prefix="/orders", tags=["orders"])' in content
    assert "async def create_order(" in content
    assert "db_order = Order(**order.dict(), user_id=user.id)" in content
    assert "async def list_orders(" in content
    assert "async def get_order(" in content
    assert '@router.get("/{id}", response_model=Order)' in content
    assert "async def update_order(" in content
    assert "async def delete_order(" in content
    out = capsys.readouterr().out
    assert "Created:" in out


def test_scaffold_endpoint_capitalizes_all_caps_name(tmp_path):
    # "TASK".capitalize() == "Task" -- verifies real Python capitalize() semantics
    args = _Args(name="TASK", output=str(tmp_path))
    tool.scaffold_endpoint(args)
    content = (tmp_path / "task.py").read_text()
    assert "class Task" not in content  # model file, not model class def -- sanity
    assert "Task(**task.dict()" in content


def test_scaffold_endpoint_uses_default_output_dir_when_none(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    args = _Args(name="widget", output=None)
    tool.scaffold_endpoint(args)
    assert (tmp_path / "src" / "routers" / "widget.py").exists()


# ---------------------------------------------------------------------------
# create_model
# ---------------------------------------------------------------------------

def test_create_model_default_fields_when_none(tmp_path):
    args = _Args(name="widget", fields=None, output=str(tmp_path))
    tool.create_model(args)
    content = (tmp_path / "widget.py").read_text()
    assert "    name: str" in content
    assert "    description: str" in content
    assert "name: Optional[str] = None" in content
    assert "description: Optional[str] = None" in content


def test_create_model_default_fields_when_empty_string(tmp_path):
    # empty string is falsy -> should fall back to the same defaults as None
    args = _Args(name="widget", fields="", output=str(tmp_path))
    tool.create_model(args)
    content = (tmp_path / "widget.py").read_text()
    assert "    name: str" in content
    assert "    description: str" in content


def test_create_model_custom_fields_produce_exact_class_bodies(tmp_path):
    args = _Args(name="widget", fields="title:str,count:int", output=str(tmp_path))
    rc = tool.create_model(args)
    assert rc == 0
    content = (tmp_path / "widget.py").read_text()
    assert "class WidgetBase(SQLModel):" in content
    assert "    title: str\n    count: int" in content
    # the DB model must reference the base class actually defined above it,
    # with no stray leading underscore (regression: this used to generate
    # `class Widget(_WidgetBase, table=True):`, which references a class
    # that was never defined and would raise NameError if run).
    assert "class Widget(WidgetBase, table=True):" in content
    assert "class Widget(_WidgetBase, table=True):" not in content
    assert "class WidgetCreate(WidgetBase):" in content
    assert "class WidgetUpdate(SQLModel):" in content
    assert "title: Optional[str] = None" in content
    assert "count: Optional[int] = None" in content


def test_create_model_base_class_reference_has_no_stray_underscore(tmp_path):
    """Regression test for a real bug: the generated DB model class used to
    reference `_{Model}Base` (leading underscore) instead of the actual
    `{Model}Base` class defined one line above it, which would raise
    NameError if the generated code were ever executed. Checked across
    multiple model names to guard against the bug regressing."""
    for name in ("widget", "order", "invoice"):
        model_name = name.capitalize()
        args = _Args(name=name, fields="foo:str", output=str(tmp_path / name))
        rc = tool.create_model(args)
        assert rc == 0
        content = (tmp_path / name / f"{model_name.lower()}.py").read_text()

        # the base class must be defined...
        assert f"class {model_name}Base(SQLModel):" in content
        # ...and the table model must reference exactly that class name.
        assert f"class {model_name}({model_name}Base, table=True):" in content
        # explicitly guard against the old buggy underscore-prefixed form.
        assert f"class {model_name}(_{model_name}Base, table=True):" not in content


def test_create_model_generated_code_is_syntactically_valid_and_defines_expected_classes(tmp_path):
    """Regression test: compile the generated model source and exec it in an
    isolated namespace (with a minimal SQLModel-like stub) to prove the
    class hierarchy actually resolves at runtime -- this is exactly the
    scenario that used to raise NameError before the underscore bug was
    fixed."""
    args = _Args(name="gadget", fields="label:str", output=str(tmp_path))
    tool.create_model(args)
    content = (tmp_path / "gadget.py").read_text()

    # sanity: source must at least compile.
    compile(content, "gadget.py", "exec")

    # strip the generated file's real `from sqlmodel import ...` / stdlib
    # import lines (sqlmodel is not a test dependency) and exec only the
    # class-definition body against a minimal SQLModel-like stub, so the
    # class hierarchy resolution is exercised for real.
    body_lines = [
        line for line in content.splitlines()
        if not line.startswith("from ") and not line.startswith("import ")
    ]
    body = "\n".join(body_lines)
    compiled = compile(body, "gadget.py", "exec")

    class _FakeField:
        def __call__(self, *a, **kw):
            return None

    class _FakeSQLModel:
        def __init_subclass__(cls, **kwargs):
            pass

    namespace = {
        "Field": _FakeField(),
        "SQLModel": _FakeSQLModel,
        "Optional": __import__("typing").Optional,
        "datetime": __import__("datetime").datetime,
    }
    exec(compiled, namespace)

    assert "GadgetBase" in namespace
    assert "Gadget" in namespace
    # the real regression check: Gadget must actually subclass GadgetBase
    # (before the fix, this line would have raised NameError at exec time
    # because `_GadgetBase` was never defined).
    assert namespace["GadgetBase"] in namespace["Gadget"].__bases__
    assert "GadgetCreate" in namespace
    assert "GadgetUpdate" in namespace


def test_create_model_skips_malformed_field_without_colon(tmp_path):
    args = _Args(name="widget", fields="name:str,badfield", output=str(tmp_path))
    tool.create_model(args)
    content = (tmp_path / "widget.py").read_text()
    assert "badfield" not in content
    assert "    name: str" in content


def test_create_model_uses_default_output_dir_when_none(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    args = _Args(name="widget", fields=None, output=None)
    tool.create_model(args)
    assert (tmp_path / "src" / "models" / "widget.py").exists()


# ---------------------------------------------------------------------------
# generate_migration
# ---------------------------------------------------------------------------

def test_generate_migration_success_prints_success(monkeypatch, capsys):
    seen = {}

    def fake_run_command(cmd, timeout=300):
        seen["cmd"] = cmd
        return 0, "Generating...", ""

    monkeypatch.setattr(tool, "run_command", fake_run_command)
    args = _Args(message=None)
    rc = tool.generate_migration(args)
    assert rc == 0
    assert "Auto-generated migration" in seen["cmd"]
    out = capsys.readouterr().out
    assert "Migration generated" in out


def test_generate_migration_uses_custom_message(monkeypatch):
    seen = {}

    def fake_run_command(cmd, timeout=300):
        seen["cmd"] = cmd
        return 0, "", ""

    monkeypatch.setattr(tool, "run_command", fake_run_command)
    tool.generate_migration(_Args(message="Add widgets table"))
    assert "Add widgets table" in seen["cmd"]


def test_generate_migration_failure_prints_error_and_stderr(monkeypatch, capsys):
    def fake_run_command(cmd, timeout=300):
        return 1, "", "no alembic.ini found"

    monkeypatch.setattr(tool, "run_command", fake_run_command)
    rc = tool.generate_migration(_Args(message=None))
    assert rc == 1
    out = capsys.readouterr().out
    assert "Migration failed" in out
    assert "no alembic.ini found" in out


# ---------------------------------------------------------------------------
# setup_auth
# ---------------------------------------------------------------------------

def test_setup_auth_writes_jwt_dependencies(tmp_path, capsys):
    args = _Args(output=str(tmp_path))
    rc = tool.setup_auth(args)
    assert rc == 0
    content = (tmp_path / "auth.py").read_text()
    assert "def create_access_token(data: dict" in content
    assert "async def get_current_user(" in content
    assert 'SECRET_KEY = os.getenv("SECRET_KEY"' in content
    assert 'ALGORITHM = "HS256"' in content
    out = capsys.readouterr().out
    assert "Created:" in out


def test_setup_auth_uses_default_output_dir_when_none(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    tool.setup_auth(_Args(output=None))
    assert (tmp_path / "src" / "auth.py").exists()


def test_setup_auth_creates_nested_output_dirs_that_do_not_exist(tmp_path):
    # exercises mkdir(parents=True) specifically: "a" does not exist yet, so
    # "a/b" cannot be created unless parent creation is actually enabled.
    nested = tmp_path / "a" / "b"
    tool.setup_auth(_Args(output=str(nested)))
    assert (nested / "auth.py").exists()


# ---------------------------------------------------------------------------
# generate_tests
# ---------------------------------------------------------------------------

def test_generate_tests_writes_expected_pytest_functions(tmp_path):
    args = _Args(resource="order", output=str(tmp_path))
    rc = tool.generate_tests(args)
    assert rc == 0
    content = (tmp_path / "test_order.py").read_text()
    assert "def test_create_order(client: TestClient):" in content
    assert "def test_list_orders(client: TestClient):" in content
    assert "def test_get_order(client: TestClient):" in content
    assert "def test_update_order(client: TestClient):" in content
    assert "def test_delete_order(client: TestClient):" in content
    assert 'from ..models.order import Order' in content


def test_generate_tests_uses_default_output_dir_when_none(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    tool.generate_tests(_Args(resource="order", output=None))
    assert (tmp_path / "tests" / "test_order.py").exists()


def test_generate_tests_creates_nested_output_dirs_that_do_not_exist(tmp_path):
    nested = tmp_path / "a" / "b"
    tool.generate_tests(_Args(resource="order", output=str(nested)))
    assert (nested / "test_order.py").exists()


# ---------------------------------------------------------------------------
# create_service
# ---------------------------------------------------------------------------

def test_create_service_writes_expected_static_methods(tmp_path):
    args = _Args(name="order", output=str(tmp_path))
    rc = tool.create_service(args)
    assert rc == 0
    content = (tmp_path / "order_service.py").read_text()
    assert "class OrderService:" in content
    assert "def create(session: Session, order: OrderCreate, user_id: int) -> Order:" in content
    assert "def get_all(session: Session, user_id: int) -> List[Order]:" in content
    assert "def get_by_id(session: Session, order_id: int, user_id: int) -> Optional[Order]:" in content
    assert "def update(session: Session, order_id: int" in content
    assert "def delete(session: Session, order_id: int, user_id: int) -> bool:" in content


def test_create_service_uses_default_output_dir_when_none(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    tool.create_service(_Args(name="order", output=None))
    assert (tmp_path / "src" / "services" / "order_service.py").exists()


# ---------------------------------------------------------------------------
# optimize_db
# ---------------------------------------------------------------------------

def test_optimize_db_prints_recommendations(capsys):
    rc = tool.optimize_db(_Args())
    assert rc == 0
    out = capsys.readouterr().out
    assert "pool_size=20" in out
    assert "selectinload" in out
    assert "Optimization guide complete" in out


# ---------------------------------------------------------------------------
# audit
# ---------------------------------------------------------------------------

def _audit_fake_run_command(rules):
    """rules: dict substring-in-cmd -> (code, stdout, stderr)."""

    def fake(cmd, timeout=300):
        for substr, result in rules.items():
            if substr in cmd:
                return result
        return 1, "", ""

    return fake


def test_audit_reports_no_issues_when_all_checks_clean(monkeypatch, capsys):
    monkeypatch.setattr(
        tool,
        "run_command",
        _audit_fake_run_command(
            {
                "SECRET_KEY": (1, "", ""),
                "password": (1, "", ""),
                "execute": (1, "", ""),
                "try:": (0, "3", ""),
                "->.*:": (0, "5", ""),
            }
        ),
    )
    rc = tool.audit(_Args())
    assert rc == 0
    out = capsys.readouterr().out
    assert "No critical issues found" in out


def test_audit_flags_secret_key_in_code(monkeypatch, capsys):
    monkeypatch.setattr(
        tool,
        "run_command",
        _audit_fake_run_command(
            {
                "SECRET_KEY": (0, "src/config.py:SECRET_KEY = 'abc'", ""),
                "password": (1, "", ""),
                "execute": (1, "", ""),
                "try:": (0, "3", ""),
                "->.*:": (0, "5", ""),
            }
        ),
    )
    rc = tool.audit(_Args())
    assert rc == 0
    out = capsys.readouterr().out
    assert "SECRET_KEY found in code" in out
    assert "Found 1 issues" in out


def test_audit_flags_hardcoded_password(monkeypatch, capsys):
    monkeypatch.setattr(
        tool,
        "run_command",
        _audit_fake_run_command(
            {
                "SECRET_KEY": (1, "", ""),
                "password": (0, "src/x.py:password = 'hunter2'", ""),
                "execute": (1, "", ""),
                "try:": (0, "3", ""),
                "->.*:": (0, "5", ""),
            }
        ),
    )
    tool.audit(_Args())
    out = capsys.readouterr().out
    assert "Hardcoded password found" in out


def test_audit_flags_sql_injection_risk(monkeypatch, capsys):
    monkeypatch.setattr(
        tool,
        "run_command",
        _audit_fake_run_command(
            {
                "SECRET_KEY": (1, "", ""),
                "password": (1, "", ""),
                "execute": (0, "src/x.py:cursor.execute('%s' % q)", ""),
                "try:": (0, "3", ""),
                "->.*:": (0, "5", ""),
            }
        ),
    )
    tool.audit(_Args())
    out = capsys.readouterr().out
    assert "Potential SQL injection vulnerability" in out


def test_audit_flags_missing_error_handling_when_grep_c_nonzero(monkeypatch, capsys):
    monkeypatch.setattr(
        tool,
        "run_command",
        _audit_fake_run_command(
            {
                "SECRET_KEY": (1, "", ""),
                "password": (1, "", ""),
                "execute": (1, "", ""),
                "try:": (1, "", ""),
                "->.*:": (0, "5", ""),
            }
        ),
    )
    tool.audit(_Args())
    out = capsys.readouterr().out
    assert "Limited error handling" in out


def test_audit_flags_missing_type_hints_when_grep_c_nonzero(monkeypatch, capsys):
    monkeypatch.setattr(
        tool,
        "run_command",
        _audit_fake_run_command(
            {
                "SECRET_KEY": (1, "", ""),
                "password": (1, "", ""),
                "execute": (1, "", ""),
                "try:": (0, "3", ""),
                "->.*:": (1, "", ""),
            }
        ),
    )
    tool.audit(_Args())
    out = capsys.readouterr().out
    assert "Missing return type hints" in out


# ---------------------------------------------------------------------------
# main() / CLI dispatch
# ---------------------------------------------------------------------------

def test_main_with_no_command_prints_help_and_returns_1(monkeypatch, capsys):
    monkeypatch.setattr(_sys, "argv", ["tool.py"])
    rc = tool.main()
    out = capsys.readouterr().out
    assert rc == 1
    assert "usage" in out.lower()


def test_main_scaffold_endpoint_end_to_end(monkeypatch, tmp_path):
    monkeypatch.setattr(
        _sys, "argv", ["tool.py", "scaffold-endpoint", "--name", "Item", "--output", str(tmp_path)]
    )
    rc = tool.main()
    assert rc == 0
    assert (tmp_path / "item.py").exists()


def test_main_create_model_end_to_end(monkeypatch, tmp_path):
    monkeypatch.setattr(
        _sys,
        "argv",
        ["tool.py", "create-model", "--name", "Item", "--fields", "sku:str", "--output", str(tmp_path)],
    )
    rc = tool.main()
    assert rc == 0
    content = (tmp_path / "item.py").read_text()
    assert "sku: str" in content


def test_main_generate_migration_end_to_end(monkeypatch, capsys):
    monkeypatch.setattr(tool, "run_command", lambda cmd, timeout=300: (0, "ok", ""))
    monkeypatch.setattr(_sys, "argv", ["tool.py", "generate-migration", "--message", "init"])
    rc = tool.main()
    assert rc == 0
    assert "Migration generated" in capsys.readouterr().out


def test_main_setup_auth_end_to_end(monkeypatch, tmp_path):
    monkeypatch.setattr(_sys, "argv", ["tool.py", "setup-auth", "--output", str(tmp_path)])
    rc = tool.main()
    assert rc == 0
    assert (tmp_path / "auth.py").exists()


def test_main_generate_tests_end_to_end(monkeypatch, tmp_path):
    monkeypatch.setattr(
        _sys, "argv", ["tool.py", "generate-tests", "--resource", "Item", "--output", str(tmp_path)]
    )
    rc = tool.main()
    assert rc == 0
    assert (tmp_path / "test_item.py").exists()


def test_main_create_service_end_to_end(monkeypatch, tmp_path):
    monkeypatch.setattr(
        _sys, "argv", ["tool.py", "create-service", "--name", "Item", "--output", str(tmp_path)]
    )
    rc = tool.main()
    assert rc == 0
    assert (tmp_path / "item_service.py").exists()


def test_main_optimize_db_end_to_end(monkeypatch, capsys):
    monkeypatch.setattr(_sys, "argv", ["tool.py", "optimize-db"])
    rc = tool.main()
    assert rc == 0
    assert "Optimization guide complete" in capsys.readouterr().out


def test_main_audit_end_to_end(monkeypatch, capsys):
    def fake_run_command(cmd, timeout=300):
        if "try:" in cmd or "->.*:" in cmd:
            return 0, "3", ""
        return 1, "", ""

    monkeypatch.setattr(tool, "run_command", fake_run_command)
    monkeypatch.setattr(_sys, "argv", ["tool.py", "audit"])
    rc = tool.main()
    assert rc == 0
    assert "No critical issues found" in capsys.readouterr().out


def test_main_scaffold_endpoint_missing_required_name_exits(monkeypatch):
    monkeypatch.setattr(_sys, "argv", ["tool.py", "scaffold-endpoint"])
    with pytest.raises(SystemExit):
        tool.main()


def test_main_create_model_missing_required_name_exits(monkeypatch):
    monkeypatch.setattr(_sys, "argv", ["tool.py", "create-model"])
    with pytest.raises(SystemExit):
        tool.main()


def test_main_generate_tests_missing_required_resource_exits(monkeypatch):
    monkeypatch.setattr(_sys, "argv", ["tool.py", "generate-tests"])
    with pytest.raises(SystemExit):
        tool.main()


def test_main_create_service_missing_required_name_exits(monkeypatch):
    monkeypatch.setattr(_sys, "argv", ["tool.py", "create-service"])
    with pytest.raises(SystemExit):
        tool.main()


def test_main_unknown_command_returns_1_via_argparse_choices(monkeypatch):
    # argparse subparsers reject unknown commands outright -> SystemExit(2)
    monkeypatch.setattr(_sys, "argv", ["tool.py", "not-a-real-command"])
    with pytest.raises(SystemExit):
        tool.main()


# ---------------------------------------------------------------------------
# subprocess smoke tests (real __main__ entrypoint end to end)
# ---------------------------------------------------------------------------

def test_cli_subprocess_smoke_test_optimize_db():
    script = Path(__file__).resolve().parent.parent / "scripts" / "tool.py"
    proc = subprocess.run(
        [_sys.executable, str(script), "optimize-db"], capture_output=True, text=True, timeout=30
    )
    assert proc.returncode == 0
    assert "Optimization guide complete" in proc.stdout


def test_cli_subprocess_smoke_test_no_command_returns_nonzero():
    script = Path(__file__).resolve().parent.parent / "scripts" / "tool.py"
    proc = subprocess.run([_sys.executable, str(script)], capture_output=True, text=True, timeout=30)
    assert proc.returncode == 1
    assert "usage" in proc.stdout.lower()


def test_cli_subprocess_smoke_test_scaffold_endpoint_writes_real_file(tmp_path):
    script = Path(__file__).resolve().parent.parent / "scripts" / "tool.py"
    proc = subprocess.run(
        [_sys.executable, str(script), "scaffold-endpoint", "--name", "Widget", "--output", str(tmp_path)],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert proc.returncode == 0
    assert (tmp_path / "widget.py").exists()
