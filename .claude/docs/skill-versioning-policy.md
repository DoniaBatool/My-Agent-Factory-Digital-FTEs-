# Skill Versioning & Regression Testing Policy

**Added:** 2026-09-14
**Why:** External code review on the public LinkedIn post for this repo
(Ammar Zaky) pointed out: *"I'd version each skill and test changes
against a fixed set of cases before replacing the working version.
Letting the agent rewrite both its instructions and its tests makes it
too easy to mistake a weaker test for an improvement."*

An audit confirmed the concern was real, not theoretical:

- `live-skill-learner` / `skill-learner` updated a skill's code, its
  docs, and its "test coverage" notes in the same pass, with nothing
  independent checking whether the new version regressed.
- `grafana-expert/scripts/tool.py` had already been silently replaced:
  a 659-line version with real multi-path prerequisite checks was
  overwritten by a 106-line version whose `test` command prints
  `[Test 1/6]` and then only ever runs test 1 of 6. The good version
  survived only because someone happened to leave an untracked
  `.backup-20260211` folder next to it — it was never in git history.
- 35+ skills' `scripts/tool.py` were an unimplemented 8-command
  scaffold (`check-prerequisites / setup / configure / deploy / test /
  health-check / troubleshoot / cleanup`) whose bodies were all
  `# TODO: Implement ... print_success("... complete")` — including
  `qa-engineer` and `edge-case-tester`, the two skills this repo's own
  README names as the enforcers of Test-Driven Development.

## The rule, going forward

**No agent may overwrite a skill's live files directly.** A change is
always prepared in a staging copy and promoted through
`.claude/skills/_framework/skill_gate.py`, which:

1. Refuses the promotion outright if the staged version deletes or
   renames any existing test function (`tests/test_*.py`) — a shrinking
   test suite is rejected before it is even run.
2. Runs the live skill's tests to get the baseline, then runs the
   staged skill's tests.
3. Refuses the promotion if any baseline test that used to pass is
   now missing, erroring, or failing, or if the staged suite exits
   non-zero for any other reason.
4. On approval, archives the old version under
   `_archive/<skill>/v<old>-<timestamp>/`, replaces the live directory,
   bumps `version.json`, and appends a dated `CHANGELOG.md` entry
   naming exactly which baseline tests were re-verified.
5. On rejection, nothing about the live skill changes, and the
   rejection is logged to `_archive/<skill>/REJECTED.log` so a blocked
   attempt is still visible instead of silently disappearing.

`skill_gate.py` is a plain, independently-tested Python module (see its
own `tests/test_skill_gate.py`) — it is not prose inside an agent's
instructions, specifically so that a future weaker rewrite of an
agent's *instructions* cannot also weaken the gate that checks it.

## What every skill now carries

- `version.json` — `{"version": "x.y.z", "history": [...]}`.
- `tests/test_tool.py` — fixed regression cases for the deterministic
  parts of the skill (argument parsing, config/spec generation,
  validation logic), with external calls mocked so they run without
  live infrastructure.
- `CHANGELOG.md` — appended only by `skill_gate.py promote`, never
  hand-edited.

## Updated agent instructions

`live-skill-learner` and `skill-learner` (see their `.md` files) now
have an explicit gate phase between "update the skill" and "confirm":
stage the change, run
`python3 .claude/skills/_framework/skill_gate.py promote --skill <name> --staged-dir <path> --reason "<what changed>"`,
and only report success if it exits 0. A non-zero exit is reported to
the user as a rejected/regressed update, not silently retried or
hidden.

## Addendum: a near-miss during this rollout

While building the first batch of fixes, staged copies for a few skills
were hand-built by cherry-picking `SKILL.md` + `scripts/` into a fresh
`.staged/` directory instead of copying the whole live directory first.
This silently would have deleted `grafana-expert/README.md`,
`prometheus-monitoring/README.md`, and `prompt-analyzer/EXAMPLES.md` had
it gone unnoticed — a smaller instance of the exact "an update quietly
makes things worse" problem this whole policy exists to catch, just
happening at the file level instead of the test level.

It was caught by reviewing `git diff --stat` before pushing, then fixed
two ways: the missing files were restored from `_archive/`, and
`skill_gate.py promote` now refuses a promotion outright if the staged
directory is missing any top-level file/dir that exists in the live
skill, unless `--allow-file-removal` is passed explicitly (see
`test_gate_rejects_staged_copy_that_accidentally_drops_a_live_file` in
`_framework/tests/test_skill_gate.py`). The correct way to stage a change
is always to copy the live directory first (`skill-learner`'s own
`stage_skill()` helper does this), then edit — never reconstruct a skill
folder from a partial file list.
