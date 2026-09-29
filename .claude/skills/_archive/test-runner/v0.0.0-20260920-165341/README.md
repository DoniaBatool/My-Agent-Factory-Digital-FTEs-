---
name: test-runner
description: Automated pytest test execution tool for Python projects with support for unit, integration, E2E tests, coverage reports, and parallel execution
---

# Test Runner - Quick Start

**One-command test execution - No testing expertise needed!**

Automated pytest test runner for Python projects. Run unit tests, integration tests, E2E tests, generate coverage reports, and execute tests in parallel - all with simple commands.

## 🚀 Quick Usage

### 1. Check Prerequisites
```bash
python3 .claude/skills/test-runner/scripts/tool.py check-prerequisites
```
**Output:** Checks for pytest, pytest-cov, pytest-xdist installation and tests/ directory

### 2. Run All Tests
```bash
python3 .claude/skills/test-runner/scripts/tool.py run-all
```
**Output:** Executes all tests in tests/ directory with verbose output

### 3. Run Tests with Coverage
```bash
python3 .claude/skills/test-runner/scripts/tool.py run-coverage
```
**Output:** Generates terminal + HTML coverage reports

### 4. Run Tests in Parallel (Faster!)
```bash
python3 .claude/skills/test-runner/scripts/tool.py run-parallel
```
**Output:** Runs tests using multiple CPU cores (requires pytest-xdist)

---

## 💡 Common Workflows

### Workflow 1: Quick Test Run (Unit Tests Only)
```bash
# Run unit tests only (fastest)
python3 tool.py run-unit

# With verbose output
python3 tool.py run-unit --verbose

# Show print statements
python3 tool.py run-unit --show-output
```

### Workflow 2: Full Test Suite with Coverage
```bash
# Run all tests with coverage report
python3 tool.py run-coverage

# Require minimum 80% coverage
python3 tool.py run-coverage --min-coverage 80
```

### Workflow 3: Test Specific File or Function
```bash
# Run specific test file
python3 tool.py run-specific tests/unit/test_recurrence_engine.py

# Run specific test function
python3 tool.py run-specific tests/unit/test_recurrence_engine.py::TestCalculateNextDueDate::test_daily_recurrence

# With verbose output
python3 tool.py run-specific tests/unit/test_auth.py --verbose
```

### Workflow 4: Fast Parallel Execution
```bash
# Run tests in parallel (auto workers)
python3 tool.py run-parallel

# Specify number of workers
python3 tool.py run-parallel --workers 4
```

### Workflow 5: Watch Mode (Development)
```bash
# Re-run tests on file changes
python3 tool.py watch
```

### Workflow 6: CI/CD Pipeline
```bash
# Comprehensive testing for CI/CD
python3 tool.py test

# This runs:
# 1. check-prerequisites
# 2. run-all tests
```

---

## 🎯 All Available Commands

### Test Execution Commands

| Command | Description | Example |
|---------|-------------|---------|
| `run-all` | Run all tests (unit + integration + e2e) | `python3 tool.py run-all` |
| `run-unit` | Run unit tests only (tests/unit/) | `python3 tool.py run-unit` |
| `run-integration` | Run integration tests only (tests/integration/) | `python3 tool.py run-integration` |
| `run-e2e` | Run E2E tests only (tests/e2e/) | `python3 tool.py run-e2e` |
| `run-coverage` | Run tests with coverage report | `python3 tool.py run-coverage` |
| `run-specific` | Run specific test file/function | `python3 tool.py run-specific tests/unit/test_auth.py` |
| `run-parallel` | Run tests in parallel (faster) | `python3 tool.py run-parallel` |
| `watch` | Run tests in watch mode | `python3 tool.py watch` |

### Utility Commands

| Command | Description |
|---------|-------------|
| `check-prerequisites` | Check pytest installation |
| `test` | Comprehensive testing (prerequisites + all tests) |

### Command Options

**run-all, run-unit, run-integration, run-e2e, run-specific:**
- `--verbose`: Extra verbose output (-vv)
- `--show-output`: Show print statements (-s)
- `--stop-on-first`: Stop on first failure (-x)

**run-coverage:**
- `--min-coverage N`: Fail if coverage below N%

**run-parallel:**
- `--workers N`: Number of parallel workers (default: auto)

---

## 🆘 Troubleshooting

### Issue 1: "pytest: command not found"
**Fix:**
```bash
pip install pytest
```

### Issue 2: "pytest-cov not installed" (coverage reports)
**Fix:**
```bash
pip install pytest-cov
```

### Issue 3: "pytest-xdist not installed" (parallel execution)
**Fix:**
```bash
pip install pytest-xdist
```

### Issue 4: Tests fail with database errors
**Fix:**
```bash
# Check if database is running
# Run migrations
alembic upgrade head

# Use SQLite for tests
export DATABASE_URL=sqlite:///./test.db
```

### Issue 5: Tests timeout
**Fix:** Increase timeout in tool.py or split long-running tests:
```python
# In tool.py, increase timeout parameter
run_command(cmd, timeout=1200)  # 20 minutes
```

### Issue 6: Import errors in tests
**Fix:** Ensure src/ is in Python path:
```bash
# Add to conftest.py or run from project root
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

---

## ✨ Features

- ✅ No pytest expertise required - just run commands
- ✅ 10 commands covering all test scenarios
- ✅ **Unit tests** - Fast isolated testing
- ✅ **Integration tests** - Database/API testing
- ✅ **E2E tests** - Full workflow testing
- ✅ **Coverage reports** - HTML + terminal output
- ✅ **Parallel execution** - 2-4x faster (pytest-xdist)
- ✅ **Watch mode** - Auto re-run on changes
- ✅ **Specific test runner** - File or function level
- ✅ **Colored output** - Easy to read results
- ✅ **Token-efficient** - Single command execution
- ✅ **CI/CD ready** - Perfect for pipelines

---

## 📊 Performance Benefits

**Without test-runner:**
- Manual pytest commands each time
- Remember all flags and options
- No organized test execution
- No parallel execution setup

**With test-runner:**
- ✅ One command: `python3 tool.py run-all`
- ✅ Pre-configured options
- ✅ Organized by test type (unit/integration/e2e)
- ✅ Parallel execution: `python3 tool.py run-parallel` (2-4x faster)

**Time Savings:**
- Unit tests: `run-unit` (fastest, ~10s)
- Integration tests: `run-integration` (medium, ~30s)
- All tests serial: `run-all` (~60s)
- All tests parallel: `run-parallel` (~15-20s) - **3-4x faster!**

---

## 🔧 Integration with CI/CD

### GitHub Actions Example
```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.12'
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run tests with coverage
        run: python3 .claude/skills/test-runner/scripts/tool.py run-coverage --min-coverage 80
```

### GitLab CI Example
```yaml
test:
  image: python:3.12
  script:
    - pip install -r requirements.txt
    - python3 .claude/skills/test-runner/scripts/tool.py test
  coverage: '/TOTAL.*\s+(\d+%)$/'
```

---

## 📈 Coverage Report Example

**Terminal Output:**
```
Name                                    Stmts   Miss  Cover   Missing
---------------------------------------------------------------------
src/services/recurrence_engine.py        50      2    96%     45-46
src/mcp_tools/set_recurring.py           80      5    94%     120-124
src/mcp_tools/complete_task.py          120      8    93%     95-102
---------------------------------------------------------------------
TOTAL                                   250     15    94%
```

**HTML Report:** Opens `htmlcov/index.html` in browser

---

**Last Updated:** 2026-02-09
**Status:** Production-ready ✅
**No testing expertise needed!** 🚀
