#!/usr/bin/env python3
"""
DevOps Engineer Tool - real pipeline audit + runbook generation

Commands: audit-pipeline, generate-runbook, test
"""
import argparse
import json
import sys
from pathlib import Path

PIPELINE_EXPECTATIONS = {
    "ci_workflow": (".github/workflows", "*.yml"),
    "dockerfile": (".", "Dockerfile"),
    "healthcheck_in_dockerfile": (".", "Dockerfile"),  # content check, see audit_pipeline
}

RUNBOOKS = {
    "high_error_rate": [
        "Check recent deploys -- roll back if a deploy correlates with the spike",
        "Check DB connection pool exhaustion (see connection-pooling skill)",
        "Check third-party dependency status pages",
    ],
    "deploy_failed": [
        "Check build logs for the failing step",
        "Verify all required env vars are set (see deployment-automation check-env-vars)",
        "Re-run the pipeline once; if it fails twice, treat as a real regression, not flakiness",
    ],
    "database_connection_exhausted": [
        "Check current connection count vs pool_size + max_overflow",
        "Look for a connection leak (missing session.close() / context manager)",
        "Temporarily lower per-instance pool size if running many instances",
    ],
}


def audit_pipeline(project_root: Path):
    project_root = Path(project_root)
    findings = {}
    ci_dir = project_root / ".github" / "workflows"
    findings["ci_workflow"] = {"present": ci_dir.exists() and any(ci_dir.glob("*.yml"))}
    dockerfile = project_root / "Dockerfile"
    findings["dockerfile"] = {"present": dockerfile.exists()}
    if dockerfile.exists():
        text = dockerfile.read_text(errors="ignore")
        findings["healthcheck_in_dockerfile"] = {"present": "HEALTHCHECK" in text}
    else:
        findings["healthcheck_in_dockerfile"] = {"present": False}
    return findings


def generate_runbook(incident_type: str):
    if incident_type not in RUNBOOKS:
        raise ValueError(f"Unknown incident type '{incident_type}'. Known: {sorted(RUNBOOKS)}")
    return RUNBOOKS[incident_type]


# ---------------------------------------------------------------------------
# CLI ------------------------------------------------------------------
# ---------------------------------------------------------------------------

def cmd_audit_pipeline(args):
    findings = audit_pipeline(Path(args.project_root))
    print(json.dumps(findings, indent=2))
    missing = [k for k, v in findings.items() if not v["present"]]
    return 0 if not missing else 1


def cmd_generate_runbook(args):
    try:
        steps = generate_runbook(args.incident_type)
    except ValueError as e:
        print(str(e))
        return 1
    for i, s in enumerate(steps, 1):
        print(f"{i}. {s}")
    return 0


def cmd_test(args):
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / ".github" / "workflows").mkdir(parents=True)
        (root / ".github" / "workflows" / "ci.yml").write_text("name: CI\n")
        (root / "Dockerfile").write_text("FROM python:3.11\nHEALTHCHECK CMD curl -f http://localhost/health\n")
        findings = audit_pipeline(root)
        ok = findings["ci_workflow"]["present"] and findings["dockerfile"]["present"] and findings["healthcheck_in_dockerfile"]["present"]

    steps = generate_runbook("deploy_failed")
    ok = ok and len(steps) >= 1
    print("SELF-TEST PASS" if ok else "SELF-TEST FAIL")
    return 0 if ok else 1


def main():
    parser = argparse.ArgumentParser(description="DevOps Engineer Tool")
    sub = parser.add_subparsers(dest="command")

    audit_p = sub.add_parser("audit-pipeline")
    audit_p.add_argument("project_root")

    runbook_p = sub.add_parser("generate-runbook")
    runbook_p.add_argument("incident_type", choices=sorted(RUNBOOKS))

    sub.add_parser("test")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return 1

    commands = {
        "audit-pipeline": cmd_audit_pipeline,
        "generate-runbook": cmd_generate_runbook,
        "test": cmd_test,
    }
    return commands[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
