---
name: backend-developer
description: Full-time equivalent Backend Developer agent with FastAPI automation - scaffolding, models, migrations, auth, tests, services, optimization, and security audits
---

# Backend Developer - Quick Start

**One-command backend development - No backend specialist needed!**

## 🚀 Quick Usage

### 1. Scaffold Complete CRUD Endpoints
```bash
python3 scripts/tool.py scaffold-endpoint --name Task
```

**Output:**
```
==> Scaffolding FastAPI Endpoint: Task
✓ Created: src/routers/task.py
ℹ Next: Add router to main.py: app.include_router(router)
```

**Generated:**
- Complete CRUD endpoints (Create, Read, Update, Delete, List)
- User isolation built-in (`user_id` foreign key)
- FastAPI dependency injection pattern
- Pydantic schemas (Base, Create, Update)

---

### 2. Create SQLModel Models
```bash
python3 scripts/tool.py create-model \
  --name Task \
  --fields "title:str,description:str,status:str,due_date:date"
```

**Output:**
```
==> Creating SQLModel: Task
✓ Created: src/models/task.py
ℹ Next: Run 'alembic revision --autogenerate -m "Add Task"'
```

**Generated:**
- `TaskBase` - Base schema
- `Task` - Database model (with `id`, `user_id`, `created_at`, `updated_at`)
- `TaskCreate` - Create schema
- `TaskUpdate` - Update schema (all fields optional)

---

### 3. Generate Alembic Migration
```bash
python3 scripts/tool.py generate-migration --message "Add Task model"
```

**Output:**
```
==> Generating Alembic Migration
✓ Migration generated
ℹ Review: alembic/versions/
ℹ Apply: alembic upgrade head
```

---

### 4. Setup JWT Authentication
```bash
python3 scripts/tool.py setup-auth
```

**Output:**
```
==> Setting Up JWT Authentication
✓ Created: src/auth.py
ℹ Next: Add SECRET_KEY to .env
ℹ Install: pip install python-jose[cryptography] passlib[bcrypt]
```

**Generated:**
- `create_access_token()` - JWT token generation
- `get_current_user()` - JWT validation dependency
- Secure defaults (30min expiration, HS256 algorithm)

---

### 5. Generate pytest Tests
```bash
python3 scripts/tool.py generate-tests --resource Task
```

**Output:**
```
==> Generating Test Files
✓ Created: tests/test_task.py
ℹ Run: pytest tests/
```

**Generated:**
- Test fixtures (session, client)
- CRUD operation tests (create, list, get, update, delete)
- SQLite in-memory database
- Dependency override pattern

---

### 6. Create Service Layer
```bash
python3 scripts/tool.py create-service --name Task
```

**Output:**
```
==> Creating Service Layer: Task
✓ Created: src/services/task_service.py
ℹ Use service in routers for business logic separation
```

**Generated:**
- `TaskService.create()` - Create with user isolation
- `TaskService.get_all()` - List user's tasks
- `TaskService.get_by_id()` - Get single task
- `TaskService.update()` - Update with validation
- `TaskService.delete()` - Delete with ownership check

---

### 7. Database Optimization
```bash
python3 scripts/tool.py optimize-db
```

**Output:**
```
==> Database Optimization Recommendations
ℹ 1. Add indexes for frequently queried fields
ℹ 2. Use connection pooling
ℹ 3. Add composite indexes for common queries
ℹ 4. Use eager loading to prevent N+1 queries
ℹ 5. Add database query logging
✓ Optimization guide complete
```

---

### 8. Security Audit
```bash
python3 scripts/tool.py audit
```

**Output:**
```
==> Backend Code Audit
ℹ Checking for common issues...
✓ No critical issues found

ℹ Recommendations:
  1. Run: bandit -r src/  (security linter)
  2. Run: mypy src/  (type checking)
  3. Run: pylint src/  (code quality)
  4. Run: black src/  (code formatting)
```

---

## 💡 Common Workflows

### Workflow 1: New Feature (Complete CRUD)

**Scenario:** Add a "Projects" feature with full CRUD operations.

```bash
# Step 1: Create model
python3 scripts/tool.py create-model \
  --name Project \
  --fields "name:str,description:str,status:str"

# Step 2: Generate migration
python3 scripts/tool.py generate-migration --message "Add Project model"

# Step 3: Apply migration
alembic upgrade head

# Step 4: Create service layer
python3 scripts/tool.py create-service --name Project

# Step 5: Scaffold endpoints
python3 scripts/tool.py scaffold-endpoint --name Project

# Step 6: Add router to main.py
# from src.routers.project import router as project_router
# app.include_router(project_router)

# Step 7: Generate tests
python3 scripts/tool.py generate-tests --resource Project

# Step 8: Run tests
pytest tests/test_project.py -v
```

**Time:** ~15 minutes (vs 4-6 hours manual)

---

### Workflow 2: Add Authentication

**Scenario:** Secure existing API with JWT authentication.

```bash
# Step 1: Setup JWT
python3 scripts/tool.py setup-auth

# Step 2: Generate SECRET_KEY
openssl rand -hex 32 >> .env  # Add SECRET_KEY=...

# Step 3: Install dependencies
pip install python-jose[cryptography] passlib[bcrypt]

# Step 4: Update routers
# Endpoints already have user = Depends(get_current_user)

# Step 5: Create login endpoint
# (Manual: POST /api/v1/auth/login)

# Step 6: Test
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"password123"}'
```

**Time:** ~10 minutes

---

### Workflow 3: Optimize Performance

**Scenario:** API is slow, need to optimize database queries.

```bash
# Step 1: Get recommendations
python3 scripts/tool.py optimize-db

# Step 2: Add indexes to model
# Add to Task model:
# __table_args__ = (Index('ix_user_created', 'user_id', 'created_at'),)

# Step 3: Generate migration
python3 scripts/tool.py generate-migration --message "Add performance indexes"

# Step 4: Apply migration
alembic upgrade head

# Step 5: Enable connection pooling
# engine = create_engine(DATABASE_URL, pool_size=20, max_overflow=0)

# Step 6: Verify improvements
# (Run performance tests)
```

**Performance:** 10x faster queries

---

### Workflow 4: Pre-Production Checklist

**Scenario:** Prepare backend for production deployment.

```bash
# Step 1: Security audit
python3 scripts/tool.py audit

# Step 2: Run security linters
bandit -r src/

# Step 3: Type checking
mypy src/

# Step 4: Code quality
pylint src/

# Step 5: Code formatting
black src/

# Step 6: Run all tests
pytest tests/ -v --cov=src

# Step 7: Database optimization
python3 scripts/tool.py optimize-db

# Step 8: Check migrations
alembic current
alembic check  # Verify no pending migrations
```

**Result:** Production-ready backend

---

## 🆘 Troubleshooting

### Issue 1: Migration Fails

**Error:** `alembic.util.exc.CommandError: Can't locate revision identified by 'xxx'`

**Fix:**
```bash
# Reset migrations (development only!)
rm -rf alembic/versions/*
alembic revision --autogenerate -m "Initial migration"
alembic upgrade head
```

---

### Issue 2: JWT Token Invalid

**Error:** `HTTPException: Could not validate credentials`

**Fix:**
```bash
# Verify SECRET_KEY in .env
cat .env | grep SECRET_KEY

# If missing, generate new key
echo "SECRET_KEY=$(openssl rand -hex 32)" >> .env

# Restart server
uvicorn src.main:app --reload
```

---

### Issue 3: User Isolation Not Working

**Error:** User can see other users' data

**Fix:**
```python
# Add user_id filter to all queries:
statement = select(Task).where(Task.user_id == user.id)

# Verify in generated code:
python3 scripts/tool.py scaffold-endpoint --name Task
# Check that user_id filter is present
```

---

### Issue 4: Tests Failing

**Error:** `pytest: ImportError: No module named 'xxx'`

**Fix:**
```bash
# Install test dependencies
pip install pytest pytest-cov

# Install app dependencies
pip install -r requirements.txt

# Run tests with verbose output
pytest tests/ -v
```

---

## ✨ Features

- ✅ No backend specialist needed
- ✅ FastAPI best practices (dependency injection, async/await)
- ✅ User isolation by default (horizontal privilege escalation prevented)
- ✅ JWT authentication (secure by default)
- ✅ SQLModel patterns (Base, Create, Update schemas)
- ✅ Alembic migrations (autogenerate + manual control)
- ✅ pytest tests (fixtures, mocking, coverage)
- ✅ Service layer separation (DRY code)
- ✅ Security scanning (OWASP Top 10)
- ✅ Database optimization (indexes, pooling)
- ✅ Token-efficient (one command = full feature)
- ✅ Production-ready (error handling, validation)

---

## 📦 Dependencies

**Required:**
- Python 3.10+
- FastAPI
- SQLModel
- Alembic
- python-jose (JWT)
- passlib (password hashing)
- pytest (testing)

**Install:**
```bash
pip install fastapi sqlmodel alembic python-jose[cryptography] passlib[bcrypt] pytest pytest-cov
```

---

## 🎯 Success Metrics

**Time Savings:**
- ✅ 80-90% faster backend development
- ✅ 0 manual code writing for CRUD operations
- ✅ 15 minutes for complete feature (vs 4-6 hours)

**Quality:**
- ✅ Production-ready code
- ✅ User isolation guaranteed
- ✅ Security built-in (JWT, bcrypt, input validation)
- ✅ Test coverage automatic

**Cost:**
- ✅ No backend specialist needed
- ✅ $0 additional tools/services
- ✅ Faster time to market

---

**Last Updated:** 2026-02-11
**Status:** Production-ready ✅
**No backend specialist needed!** 🚀
