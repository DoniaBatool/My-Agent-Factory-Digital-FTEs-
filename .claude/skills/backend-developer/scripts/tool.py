#!/usr/bin/env python3
"""
Backend Developer Expert Tool - FastAPI automation

Commands: scaffold-endpoint, create-model, generate-migration,
         setup-auth, generate-tests, create-service, optimize-db, audit

Based on FastAPI, SQLModel, and Alembic best practices
"""
import argparse, subprocess, sys, os
from pathlib import Path

class Colors:
    GREEN, RED, YELLOW, BLUE, BOLD, END = '\033[92m', '\033[91m', '\033[93m', '\033[94m', '\033[1m', '\033[0m'

def print_success(msg): print(f"{Colors.GREEN}✓{Colors.END} {msg}")
def print_error(msg): print(f"{Colors.RED}✗{Colors.END} {msg}")
def print_info(msg): print(f"{Colors.BLUE}ℹ{Colors.END} {msg}")
def print_header(msg): print(f"\n{Colors.BOLD}==> {msg}{Colors.END}")

def run_command(cmd: str, timeout: int = 300):
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return result.returncode, result.stdout, result.stderr
    except: return 1, "", "Error"

def scaffold_endpoint(args):
    print_header(f"Scaffolding FastAPI Endpoint: {args.name}")

    resource = args.name.lower()
    model_name = args.name.capitalize()

    # Create endpoint file
    endpoint_code = f'''"""
{model_name} API Endpoints
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from typing import List
from ..database import get_session
from ..models.{resource} import {model_name}, {model_name}Create, {model_name}Update
from ..auth import get_current_user

router = APIRouter(prefix="/{resource}s", tags=["{resource}s"])

@router.post("/", response_model={model_name})
async def create_{resource}(
    {resource}: {model_name}Create,
    session: Session = Depends(get_session),
    user = Depends(get_current_user)
):
    """Create new {resource}"""
    db_{resource} = {model_name}(**{resource}.dict(), user_id=user.id)
    session.add(db_{resource})
    session.commit()
    session.refresh(db_{resource})
    return db_{resource}

@router.get("/", response_model=List[{model_name}])
async def list_{resource}s(
    session: Session = Depends(get_session),
    user = Depends(get_current_user)
):
    """List user's {resource}s"""
    statement = select({model_name}).where({model_name}.user_id == user.id)
    results = session.exec(statement).all()
    return results

@router.get("/{{id}}", response_model={model_name})
async def get_{resource}(
    id: int,
    session: Session = Depends(get_session),
    user = Depends(get_current_user)
):
    """Get {resource} by ID"""
    {resource} = session.get({model_name}, id)
    if not {resource} or {resource}.user_id != user.id:
        raise HTTPException(status_code=404, detail="{model_name} not found")
    return {resource}

@router.patch("/{{id}}", response_model={model_name})
async def update_{resource}(
    id: int,
    {resource}_update: {model_name}Update,
    session: Session = Depends(get_session),
    user = Depends(get_current_user)
):
    """Update {resource}"""
    {resource} = session.get({model_name}, id)
    if not {resource} or {resource}.user_id != user.id:
        raise HTTPException(status_code=404, detail="{model_name} not found")

    update_data = {resource}_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr({resource}, key, value)

    session.add({resource})
    session.commit()
    session.refresh({resource})
    return {resource}

@router.delete("/{{id}}")
async def delete_{resource}(
    id: int,
    session: Session = Depends(get_session),
    user = Depends(get_current_user)
):
    """Delete {resource}"""
    {resource} = session.get({model_name}, id)
    if not {resource} or {resource}.user_id != user.id:
        raise HTTPException(status_code=404, detail="{model_name} not found")

    session.delete({resource})
    session.commit()
    return {{"message": "{model_name} deleted"}}
'''

    # Write file
    output_dir = Path(args.output or f"src/routers")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"{resource}.py"

    with open(output_file, 'w') as f:
        f.write(endpoint_code)

    print_success(f"Created: {output_file}")
    print_info("Next: Add router to main.py: app.include_router(router)")
    return 0

def create_model(args):
    print_header(f"Creating SQLModel: {args.name}")

    model_name = args.name.capitalize()
    fields = args.fields.split(",") if args.fields else ["name:str", "description:str"]

    # Parse fields
    field_definitions = []
    for field in fields:
        if ":" in field:
            field_name, field_type = field.split(":")
            field_definitions.append(f"    {field_name}: {field_type}")

    model_code = f'''"""
{model_name} Model
"""
from sqlmodel import Field, SQLModel
from typing import Optional
from datetime import datetime

class {model_name}Base(SQLModel):
    """Base {model_name} schema"""
{chr(10).join(field_definitions)}

class {model_name}(_{model_name}Base, table=True):
    """DB {model_name} model"""
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class {model_name}Create({model_name}Base):
    """Create {model_name} schema"""
    pass

class {model_name}Update(SQLModel):
    """Update {model_name} schema"""
{chr(10).join([f"    {field.split(':')[0]}: Optional[{field.split(':')[1]}] = None" for field in fields if ':' in field])}
'''

    output_dir = Path(args.output or "src/models")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"{model_name.lower()}.py"

    with open(output_file, 'w') as f:
        f.write(model_code)

    print_success(f"Created: {output_file}")
    print_info("Next: Run 'alembic revision --autogenerate -m \"Add {model_name}\"'")
    return 0

def generate_migration(args):
    print_header("Generating Alembic Migration")

    message = args.message or "Auto-generated migration"

    cmd = f'alembic revision --autogenerate -m "{message}"'
    code, stdout, stderr = run_command(cmd)

    if code == 0:
        print_success("Migration generated")
        print_info("Review: alembic/versions/")
        print_info("Apply: alembic upgrade head")
    else:
        print_error("Migration failed")
        print_error(stderr)

    return code

def setup_auth(args):
    print_header("Setting Up JWT Authentication")

    # Create auth.py with JWT dependencies
    auth_code = '''"""
JWT Authentication Dependencies
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from datetime import datetime, timedelta
from sqlmodel import Session, select
from .database import get_session
from .models.user import User
import os

SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

security = HTTPBearer()

def create_access_token(data: dict, expires_delta: timedelta = None):
    """Create JWT access token"""
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: Session = Depends(get_session)
) -> User:
    """Get current authenticated user from JWT token"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = session.get(User, user_id)
    if user is None:
        raise credentials_exception

    return user
'''

    output_dir = Path(args.output or "src")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "auth.py"

    with open(output_file, 'w') as f:
        f.write(auth_code)

    print_success(f"Created: {output_file}")
    print_info("Next: Add SECRET_KEY to .env")
    print_info("Install: pip install python-jose[cryptography] passlib[bcrypt]")
    return 0

def generate_tests(args):
    print_header("Generating Test Files")

    resource = args.resource.lower()
    model_name = args.resource.capitalize()

    test_code = f'''"""
{model_name} API Tests
"""
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, create_engine, SQLModel
from sqlmodel.pool import StaticPool
from ..main import app
from ..database import get_session
from ..models.{resource} import {model_name}

@pytest.fixture(name="session")
def session_fixture():
    """Create test database session"""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={{"check_same_thread": False}},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session

@pytest.fixture(name="client")
def client_fixture(session: Session):
    """Create test client"""
    def get_session_override():
        return session

    app.dependency_overrides[get_session] = get_session_override
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()

def test_create_{resource}(client: TestClient):
    """Test creating {resource}"""
    response = client.post(
        "/{resource}s/",
        json={{
            "name": "Test {model_name}",
            "description": "Test description"
        }},
        headers={{"Authorization": "Bearer test-token"}}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Test {model_name}"

def test_list_{resource}s(client: TestClient):
    """Test listing {resource}s"""
    response = client.get(
        "/{resource}s/",
        headers={{"Authorization": "Bearer test-token"}}
    )
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_get_{resource}(client: TestClient):
    """Test getting specific {resource}"""
    # Create first
    create_response = client.post(
        "/{resource}s/",
        json={{"name": "Test", "description": "Test"}},
        headers={{"Authorization": "Bearer test-token"}}
    )
    {resource}_id = create_response.json()["id"]

    # Get
    response = client.get(
        f"/{resource}s/{{{resource}_id}}",
        headers={{"Authorization": "Bearer test-token"}}
    )
    assert response.status_code == 200

def test_update_{resource}(client: TestClient):
    """Test updating {resource}"""
    # Create first
    create_response = client.post(
        "/{resource}s/",
        json={{"name": "Test", "description": "Test"}},
        headers={{"Authorization": "Bearer test-token"}}
    )
    {resource}_id = create_response.json()["id"]

    # Update
    response = client.patch(
        f"/{resource}s/{{{resource}_id}}",
        json={{"name": "Updated"}},
        headers={{"Authorization": "Bearer test-token"}}
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Updated"

def test_delete_{resource}(client: TestClient):
    """Test deleting {resource}"""
    # Create first
    create_response = client.post(
        "/{resource}s/",
        json={{"name": "Test", "description": "Test"}},
        headers={{"Authorization": "Bearer test-token"}}
    )
    {resource}_id = create_response.json()["id"]

    # Delete
    response = client.delete(
        f"/{resource}s/{{{resource}_id}}",
        headers={{"Authorization": "Bearer test-token"}}
    )
    assert response.status_code == 200
'''

    output_dir = Path(args.output or "tests")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"test_{resource}.py"

    with open(output_file, 'w') as f:
        f.write(test_code)

    print_success(f"Created: {output_file}")
    print_info("Run: pytest tests/")
    return 0

def create_service(args):
    print_header(f"Creating Service Layer: {args.name}")

    service_name = args.name.capitalize()
    resource = args.name.lower()

    service_code = f'''"""
{service_name} Service Layer - Business Logic
"""
from sqlmodel import Session, select
from typing import List, Optional
from ..models.{resource} import {service_name}, {service_name}Create, {service_name}Update

class {service_name}Service:
    """Service for {service_name} business logic"""

    @staticmethod
    def create(session: Session, {resource}: {service_name}Create, user_id: int) -> {service_name}:
        """Create new {resource}"""
        db_{resource} = {service_name}(**{resource}.dict(), user_id=user_id)
        session.add(db_{resource})
        session.commit()
        session.refresh(db_{resource})
        return db_{resource}

    @staticmethod
    def get_all(session: Session, user_id: int) -> List[{service_name}]:
        """Get all {resource}s for user"""
        statement = select({service_name}).where({service_name}.user_id == user_id)
        return session.exec(statement).all()

    @staticmethod
    def get_by_id(session: Session, {resource}_id: int, user_id: int) -> Optional[{service_name}]:
        """Get {resource} by ID"""
        {resource} = session.get({service_name}, {resource}_id)
        if {resource} and {resource}.user_id == user_id:
            return {resource}
        return None

    @staticmethod
    def update(session: Session, {resource}_id: int, {resource}_update: {service_name}Update, user_id: int) -> Optional[{service_name}]:
        """Update {resource}"""
        {resource} = {service_name}Service.get_by_id(session, {resource}_id, user_id)
        if not {resource}:
            return None

        update_data = {resource}_update.dict(exclude_unset=True)
        for key, value in update_data.items():
            setattr({resource}, key, value)

        session.add({resource})
        session.commit()
        session.refresh({resource})
        return {resource}

    @staticmethod
    def delete(session: Session, {resource}_id: int, user_id: int) -> bool:
        """Delete {resource}"""
        {resource} = {service_name}Service.get_by_id(session, {resource}_id, user_id)
        if not {resource}:
            return False

        session.delete({resource})
        session.commit()
        return True
'''

    output_dir = Path(args.output or "src/services")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"{resource}_service.py"

    with open(output_file, 'w') as f:
        f.write(service_code)

    print_success(f"Created: {output_file}")
    print_info("Use service in routers for business logic separation")
    return 0

def optimize_db(args):
    print_header("Database Optimization Recommendations")

    print_info("1. Add indexes for frequently queried fields:")
    print("   user_id: Field(foreign_key='user.id', index=True)")
    print("   created_at: Field(default_factory=datetime.utcnow, index=True)")

    print_info("\n2. Use connection pooling:")
    print("   engine = create_engine(DATABASE_URL, pool_size=20, max_overflow=0)")

    print_info("\n3. Add composite indexes for common queries:")
    print("   __table_args__ = (Index('ix_user_created', 'user_id', 'created_at'),)")

    print_info("\n4. Use eager loading to prevent N+1 queries:")
    print("   statement = select(Task).options(selectinload(Task.user))")

    print_info("\n5. Add database query logging:")
    print("   engine = create_engine(DATABASE_URL, echo=True)")

    print_success("Optimization guide complete")
    return 0

def audit(args):
    print_header("Backend Code Audit")

    issues = []

    # Check for common issues
    print_info("Checking for common issues...")

    # Check 1: Secret key in code
    code, stdout, stderr = run_command('grep -r "SECRET_KEY.*=" src/ 2>/dev/null | grep -v ".env"')
    if code == 0 and stdout:
        issues.append("⚠️  SECRET_KEY found in code (should be in .env)")

    # Check 2: Hardcoded passwords
    code, stdout, stderr = run_command('grep -ri "password.*=.*[\'\"]" src/ 2>/dev/null')
    if code == 0 and stdout:
        issues.append("⚠️  Hardcoded password found")

    # Check 3: SQL injection vulnerabilities
    code, stdout, stderr = run_command('grep -r "execute.*format\\|execute.*%" src/ 2>/dev/null')
    if code == 0 and stdout:
        issues.append("⚠️  Potential SQL injection vulnerability (use parameterized queries)")

    # Check 4: Missing error handling
    code, stdout, stderr = run_command('grep -c "try:" src/**/*.py 2>/dev/null')
    if code != 0:
        issues.append("⚠️  Limited error handling (add try/except blocks)")

    # Check 5: Missing type hints
    code, stdout, stderr = run_command('grep -c "def.*->.*:" src/**/*.py 2>/dev/null')
    if code != 0:
        issues.append("⚠️  Missing return type hints")

    if issues:
        print_error(f"Found {len(issues)} issues:")
        for issue in issues:
            print(f"  {issue}")
    else:
        print_success("No critical issues found")

    print_info("\nRecommendations:")
    print("  1. Run: bandit -r src/  (security linter)")
    print("  2. Run: mypy src/  (type checking)")
    print("  3. Run: pylint src/  (code quality)")
    print("  4. Run: black src/  (code formatting)")

    return 0

def main():
    parser = argparse.ArgumentParser(description='Backend Developer Expert Tool')
    subparsers = parser.add_subparsers(dest='command')

    # scaffold-endpoint
    endpoint_parser = subparsers.add_parser('scaffold-endpoint', help='Generate FastAPI CRUD endpoints')
    endpoint_parser.add_argument('--name', required=True, help='Resource name (e.g., Task)')
    endpoint_parser.add_argument('--output', help='Output directory')

    # create-model
    model_parser = subparsers.add_parser('create-model', help='Generate SQLModel models')
    model_parser.add_argument('--name', required=True, help='Model name')
    model_parser.add_argument('--fields', help='Fields (e.g., name:str,age:int)')
    model_parser.add_argument('--output', help='Output directory')

    # generate-migration
    migration_parser = subparsers.add_parser('generate-migration', help='Generate Alembic migration')
    migration_parser.add_argument('--message', help='Migration message')

    # setup-auth
    auth_parser = subparsers.add_parser('setup-auth', help='Setup JWT authentication')
    auth_parser.add_argument('--output', help='Output directory')

    # generate-tests
    tests_parser = subparsers.add_parser('generate-tests', help='Generate pytest test files')
    tests_parser.add_argument('--resource', required=True, help='Resource name for tests')
    tests_parser.add_argument('--output', help='Output directory')

    # create-service
    service_parser = subparsers.add_parser('create-service', help='Create service layer')
    service_parser.add_argument('--name', required=True, help='Service name')
    service_parser.add_argument('--output', help='Output directory')

    # optimize-db
    subparsers.add_parser('optimize-db', help='Database optimization recommendations')

    # audit
    subparsers.add_parser('audit', help='Backend code security audit')

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return 1

    commands = {
        'scaffold-endpoint': scaffold_endpoint,
        'create-model': create_model,
        'generate-migration': generate_migration,
        'setup-auth': setup_auth,
        'generate-tests': generate_tests,
        'create-service': create_service,
        'optimize-db': optimize_db,
        'audit': audit
    }

    return commands.get(args.command, lambda a: 1)(args)

if __name__ == '__main__':
    sys.exit(main())
