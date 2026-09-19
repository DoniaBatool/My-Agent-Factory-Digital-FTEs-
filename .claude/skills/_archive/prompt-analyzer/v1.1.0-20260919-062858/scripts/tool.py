#!/usr/bin/env python3
"""
Prompt Analyzer Tool - real intent detection + skill/agent mapping

Commands: analyze, detect-intent, extract-keywords, map-skills, test

Replaces the previous 8-command placeholder (check-prerequisites / setup /
configure / deploy / test / health-check / troubleshoot / cleanup, all
`# TODO: Implement` + unconditional print_success) with the actual keyword
-> intent -> skill mapping this skill's own SKILL.md describes.
"""
import argparse
import json
import re
import sys

INTENT_PATTERNS = {
    "create": [r"\bcreate\b", r"\bbuild\b", r"\bnew\b", r"\badd\b", r"\bscaffold\b", r"\bimplement\b"],
    "modify": [r"\bupdate\b", r"\bmodify\b", r"\bchange\b", r"\brefactor\b", r"\brename\b"],
    "test": [r"\btests?\b", r"\btesting\b", r"\bqa\b", r"\bedge case\b", r"\bcoverage\b"],
    "deploy": [r"\bdeploy\b", r"\bproduction\b", r"\bvercel\b", r"\bkubernetes\b", r"\bdocker\b"],
    "debug": [r"\bfix\b", r"\bdebug\b", r"\berror\b", r"\bbug\b", r"\bnot working\b", r"\bissue\b"],
    "optimize": [r"\boptimi[sz]e\b", r"\bperformance\b", r"\bspeed up\b", r"\bfaster\b", r"\bcache\b"],
    "document": [r"\bdocument\b", r"\breadme\b", r"\bdocs\b", r"\bguide\b"],
    "analyze": [r"\banaly[sz]e\b", r"\breview\b", r"\baudit\b", r"\bexplain\b"],
}

# keyword -> skills, taken from this skill's own SKILL.md "Keyword Extraction" section
KEYWORD_TO_SKILLS = {
    "chatbot": ["chatbot-endpoint", "conversation-manager"],
    "ai": ["mcp-tool-builder", "prompt-analyzer"],
    "agent": ["mcp-tool-builder", "prompt-analyzer"],
    "auth": ["jwt-authentication", "password-security", "user-isolation"],
    "login": ["jwt-authentication", "password-security"],
    "jwt": ["jwt-authentication"],
    "password": ["password-security"],
    "database": ["database-engineer", "database-schema-expander"],
    "table": ["database-schema-expander"],
    "migration": ["database-schema-expander"],
    "test": ["edge-case-tester", "qa-engineer", "test-runner"],
    "edge case": ["edge-case-tester"],
    "qa": ["qa-engineer"],
    "deploy": ["deployment-automation", "vercel-deployer"],
    "production": ["production-checklist"],
    "vercel": ["vercel-deployer"],
    "git": ["github-specialist", "change-management"],
    "merge": ["github-specialist"],
    "pr": ["github-specialist"],
    "security": ["security-engineer"],
    "cache": ["caching-strategy"],
    "kubernetes": ["kubernetes-deployment", "container-orchestration"],
    "docker": ["docker-expert"],
    "graphql": ["graphql-api"],
    "websocket": ["websocket-realtime"],
    "logging": ["structured-logging"],
    "monitoring": ["observability-apm", "prometheus-monitoring", "grafana-expert"],
}


def detect_intent(prompt: str):
    """Return every intent whose pattern matches, in INTENT_PATTERNS order,
    or ['unknown'] if nothing matches. Multiple intents can legitimately
    apply to one prompt (e.g. "fix and add tests" is debug + test)."""
    prompt_lower = prompt.lower()
    matched = [
        intent for intent, patterns in INTENT_PATTERNS.items()
        if any(re.search(p, prompt_lower) for p in patterns)
    ]
    return matched or ["unknown"]


def extract_keywords(prompt: str):
    """Return every known keyword (from KEYWORD_TO_SKILLS) present in the
    prompt, longest keywords first so 'edge case' matches before 'test'
    would otherwise swallow part of it."""
    prompt_lower = prompt.lower()
    found = [kw for kw in sorted(KEYWORD_TO_SKILLS, key=len, reverse=True) if kw in prompt_lower]
    return found


def map_to_skills(keywords):
    """Union of skills for a list of keywords, de-duplicated, order-preserving."""
    seen = []
    for kw in keywords:
        for skill in KEYWORD_TO_SKILLS.get(kw, []):
            if skill not in seen:
                seen.append(skill)
    return seen


def build_execution_plan(prompt: str):
    intents = detect_intent(prompt)
    keywords = extract_keywords(prompt)
    skills = map_to_skills(keywords)
    return {"prompt": prompt, "intents": intents, "keywords": keywords, "skills": skills}


# ---------------------------------------------------------------------------
# CLI ------------------------------------------------------------------
# ---------------------------------------------------------------------------

def cmd_analyze(args):
    plan = build_execution_plan(args.prompt)
    print(json.dumps(plan, indent=2))
    return 0 if plan["skills"] or plan["intents"] != ["unknown"] else 1


def cmd_detect_intent(args):
    intents = detect_intent(args.prompt)
    print(", ".join(intents))
    return 0


def cmd_extract_keywords(args):
    keywords = extract_keywords(args.prompt)
    print(", ".join(keywords) if keywords else "(none)")
    return 0


def cmd_map_skills(args):
    keywords = args.keywords.split(",") if args.keywords else extract_keywords(args.prompt or "")
    skills = map_to_skills([k.strip() for k in keywords])
    print(", ".join(skills) if skills else "(no mapped skills)")
    return 0


def cmd_test(args):
    plan = build_execution_plan("Fix this JWT login error and add tests before deploying to Vercel")
    ok = "debug" in plan["intents"] and "jwt-authentication" in plan["skills"]
    print(json.dumps(plan, indent=2))
    print("SELF-TEST PASS" if ok else "SELF-TEST FAIL")
    return 0 if ok else 1


def main():
    parser = argparse.ArgumentParser(description="Prompt Analyzer Tool")
    sub = parser.add_subparsers(dest="command")

    analyze_p = sub.add_parser("analyze")
    analyze_p.add_argument("prompt")

    intent_p = sub.add_parser("detect-intent")
    intent_p.add_argument("prompt")

    kw_p = sub.add_parser("extract-keywords")
    kw_p.add_argument("prompt")

    map_p = sub.add_parser("map-skills")
    map_p.add_argument("prompt", nargs="?", default="")
    map_p.add_argument("--keywords", default=None)

    sub.add_parser("test")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return 1

    commands = {
        "analyze": cmd_analyze,
        "detect-intent": cmd_detect_intent,
        "extract-keywords": cmd_extract_keywords,
        "map-skills": cmd_map_skills,
        "test": cmd_test,
    }
    return commands[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
