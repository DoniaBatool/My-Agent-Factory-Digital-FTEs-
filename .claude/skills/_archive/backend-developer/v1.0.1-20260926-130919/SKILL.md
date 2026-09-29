---
name: backend-developer
description: Full-time equivalent Backend Developer agent with FastAPI automation - scaffolding, models, migrations, auth, tests, services, optimization, and security audits
---

# Backend Developer - Expert-Level Automation

**FastAPI backend development without manual code generation!**

**Category:** Backend Development & Automation
**Complexity:** Beginner-Friendly (Expert Power)
**Time Savings:** 80-90% reduction
**Quality:** Production-ready with security built-in

---

## When to Use This Skill

**Use when:**
- Creating new FastAPI endpoints (CRUD operations)
- Generating SQLModel database models
- Setting up JWT authentication
- Creating Alembic migrations
- Writing pytest test files
- Building service layer classes
- Optimizing database performance
- Auditing backend code security

**Skip when:**
- Frontend development (use /frontend-developer)
- Infrastructure setup (use /devops-engineer)
- Database-only work (use /database-engineer)

---

## What This Skill Provides

**8 Commands covering all backend tasks:**
- `scaffold-endpoint` → Complete FastAPI CRUD endpoints with user isolation
- `create-model` → SQLModel models (Base, Create, Update schemas)
- `generate-migration` → Alembic database migrations
- `setup-auth` → JWT authentication dependencies
- `generate-tests` → pytest test files for endpoints
- `create-service` → Service layer with business logic
- `optimize-db` → Database optimization recommendations
- `audit` → Security audit with vulnerability detection

**Features:**
- ✅ User isolation built-in (no horizontal privilege escalation)
- ✅ FastAPI best practices (dependency injection)
- ✅ SQLModel patterns (Base/Create/Update)
- ✅ Alembic migrations (autogenerate)
- ✅ pytest tests (fixtures, mocking)
- ✅ JWT auth (secure by default)
- ✅ Service layer separation
- ✅ Security scanning

---

## Quick Reference

See README.md for:
- Quick start guide
- All command examples with outputs
- Common workflows
- Troubleshooting

**Most common workflow:**
```bash
# 1. Create model
python3 tool.py create-model --name Task --fields "title:str,description:str,status:str"

# 2. Generate migration
python3 tool.py generate-migration --message "Add Task model"

# 3. Create service layer
python3 tool.py create-service --name Task

# 4. Scaffold CRUD endpoints
python3 tool.py scaffold-endpoint --name Task

# 5. Generate tests
python3 tool.py generate-tests --resource Task

# 6. Run security audit
python3 tool.py audit
```

---

## Professional Profile

**Role**: Senior Backend Developer (FTE Digital Employee)
**Expertise**: FastAPI, SQLModel, Alembic, JWT auth, testing, security
**Principles**: User isolation, security-first, DRY code, testability

---

## Default Standards

- **Auth first**: Derive user identity from auth context (never trust `user_id` in payload)
- **User isolation**: Ownership checks inside DB queries (`where(Model.user_id == user.id)`)
- **Validation**: Pydantic schemas for all request/response models
- **Time**: Store UTC, serialize ISO-8601, document timezone expectations
- **Safe partial updates**: Never write `None` unless explicitly requested
- **Service layer**: Keep routes thin, move business logic to services
- **Testing**: Unit tests for services, integration tests for endpoints

---

## Advanced Patterns

### Pattern 1: Complete Feature Development (TDD)

**Scenario:** Implement a new "Projects" feature from scratch.

```bash
# Step 1: Create model with fields
python3 tool.py create-model \
  --name Project \
  --fields "name:str,description:str,status:str,due_date:date"

# Step 2: Generate database migration
python3 tool.py generate-migration --message "Add Project model"

# Step 3: Apply migration
alembic upgrade head

# Step 4: Create service layer
python3 tool.py create-service --name Project

# Step 5: Scaffold CRUD endpoints
python3 tool.py scaffold-endpoint --name Project

# Step 6: Generate test suite
python3 tool.py generate-tests --resource Project

# Step 7: Run tests
pytest tests/test_project.py -v

# Step 8: Security audit
python3 tool.py audit
```

**Time saved:** 4-6 hours → 15 minutes

---

### Pattern 2: Adding Authentication to Existing API

**Scenario:** Secure an existing API with JWT authentication.

```bash
# Step 1: Setup JWT auth
python3 tool.py setup-auth

# Step 2: Add SECRET_KEY to .env
echo "SECRET_KEY=$(openssl rand -hex 32)" >> .env

# Step 3: Install dependencies
pip install python-jose[cryptography] passlib[bcrypt]

# Step 4: Update routers to use get_current_user
# (tool.py already generates endpoints with user isolation)

# Step 5: Test authentication
python3 tool.py generate-tests --resource Auth
```

**Security:** JWT with 30min expiration, bcrypt password hashing

---

### Pattern 3: Database Optimization Audit

**Scenario:** Slow API responses, need to optimize database queries.

```bash
# Step 1: Get optimization recommendations
python3 tool.py optimize-db

# Follow recommendations:
# - Add indexes to frequently queried fields
# - Enable connection pooling
# - Add composite indexes
# - Use eager loading (prevent N+1 queries)
# - Enable query logging

# Step 2: Apply index migration
python3 tool.py generate-migration --message "Add performance indexes"

# Step 3: Verify improvements
# (Run performance tests before/after)
```

**Performance:** 10x faster queries with proper indexes

---

### Pattern 4: Service Layer Refactoring

**Scenario:** Routes are getting too complex, need to separate business logic.

```bash
# Create service layer for existing model
python3 tool.py create-service --name Task

# Generated service includes:
# - TaskService.create()
# - TaskService.get_all()
# - TaskService.get_by_id()
# - TaskService.update()
# - TaskService.delete()

# Refactor routes to use service:
# Before: Session queries in routes
# After: TaskService.get_all(session, user.id)
```

**Benefits:** Testable business logic, DRY code, easier maintenance

---

### Pattern 5: Security Audit & Fixes

**Scenario:** Pre-production security check.

```bash
# Run comprehensive security audit
python3 tool.py audit

# Audit checks:
# ✓ No hardcoded secrets
# ✓ No SQL injection vulnerabilities
# ✓ Proper error handling
# ✓ Type hints present
# ✓ No console.log in production

# Follow recommendations:
python3 tool.py audit
bandit -r src/  # Security linter
mypy src/       # Type checking
pylint src/     # Code quality
black src/      # Code formatting
```

**Security:** OWASP Top 10 compliance

---

## Success Metrics

**Time Savings:**
- ✅ 80-90% faster backend development
- ✅ 0 manual code writing for CRUD operations
- ✅ Instant model/endpoint scaffolding

**Quality:**
- ✅ Production-ready code (security built-in)
- ✅ User isolation by default
- ✅ Test coverage built-in
- ✅ Best practices enforced

**Cost Savings:**
- ✅ No backend specialist needed
- ✅ Faster feature delivery
- ✅ Fewer bugs (tested patterns)

---

## Integration with Other Skills

**Works well with:**

1. **database-engineer** - Advanced schema design
2. **qa-engineer** - Comprehensive testing strategies
3. **security-engineer** - Security hardening
4. **deployment-automation** - CI/CD integration
5. **api-docs-generator** - OpenAPI documentation

---

## Workflow

### Phase 1: Clarify Requirements
- Define endpoints + data model changes
- Define success criteria and error behavior

### Phase 2: Implement
- Use tool.py commands to generate code
- Customize generated code if needed
- Add business logic to service layer

### Phase 3: Hardening
- Run security audit
- Add edge case tests
- Optimize database queries

---

## Common Deliverables

- [ ] SQLModel models with proper schemas
- [ ] Alembic migrations (upgrade + downgrade)
- [ ] FastAPI endpoints with user isolation
- [ ] Service layer with business logic
- [ ] pytest tests (unit + integration)
- [ ] JWT authentication setup
- [ ] Security audit passed

---

**Status:** Production-ready ✅
**No backend specialist needed!** 🚀
**80-90% time savings!** ⚡
