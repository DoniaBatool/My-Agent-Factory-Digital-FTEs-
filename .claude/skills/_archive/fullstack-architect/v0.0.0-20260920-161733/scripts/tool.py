#!/usr/bin/env python3
"""
Fullstack Architect Expert Tool - System design automation

Commands: design-system, create-adr, diagram-architecture, evaluate-tradeoffs,
         plan-scaling, security-review, cost-estimate, tech-stack-recommendation

Based on system design best practices, cloud architecture patterns, and scalability principles
"""
import argparse, subprocess, sys, os, json
from pathlib import Path
from datetime import datetime

class Colors:
    GREEN, RED, YELLOW, BLUE, BOLD, END = '\033[92m', '\033[91m', '\033[93m', '\033[94m', '\033[1m', '\033[0m'

def print_success(msg): print(f"{Colors.GREEN}✓{Colors.END} {msg}")
def print_error(msg): print(f"{Colors.RED}✗{Colors.END} {msg}")
def print_warning(msg): print(f"{Colors.YELLOW}⚠{Colors.END} {msg}")
def print_info(msg): print(f"{Colors.BLUE}ℹ{Colors.END} {msg}")
def print_header(msg): print(f"\n{Colors.BOLD}==> {msg}{Colors.END}")

def run_command(cmd: str, timeout: int = 300):
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return result.returncode, result.stdout, result.stderr
    except: return 1, "", "Error"

def design_system(args):
    print_header(f"Designing System: {args.name}")

    system_name = args.name
    requirements = args.requirements.split(',') if args.requirements else []

    design_doc = f'''# System Design: {system_name}

**Date:** {datetime.now().strftime('%Y-%m-%d')}
**Status:** Draft

## 1. Requirements

### Functional Requirements
'''
    for req in requirements:
        design_doc += f"- {req.strip()}\n"

    design_doc += '''
### Non-Functional Requirements
- Scalability: [Define scaling requirements]
- Performance: [Define performance targets]
- Availability: [Define uptime requirements]
- Security: [Define security requirements]

## 2. System Architecture

### High-Level Architecture
```
┌──────────────┐      ┌──────────────┐      ┌──────────────┐
│   Client     │─────▶│   API Layer  │─────▶│   Database   │
│   (Web/Mobile)      │   (REST/GQL) │      │   (Primary)  │
└──────────────┘      └──────────────┘      └──────────────┘
                             │
                             ▼
                      ┌──────────────┐
                      │  Cache Layer │
                      │  (Redis)     │
                      └──────────────┘
```

### Components
1. **Client Layer**
   - Web: Next.js 14 (React 18, TypeScript)
   - Mobile: React Native / Flutter (future)

2. **API Layer**
   - Framework: FastAPI (Python)
   - Authentication: JWT
   - Rate Limiting: Redis-based
   - Documentation: OpenAPI/Swagger

3. **Data Layer**
   - Primary DB: PostgreSQL (ACID compliant)
   - Cache: Redis (session, frequently accessed data)
   - Message Queue: Kafka/RabbitMQ (async tasks)

4. **Infrastructure**
   - Container: Docker
   - Orchestration: Kubernetes
   - CI/CD: GitHub Actions
   - Monitoring: Prometheus + Grafana

## 3. API Design

### REST Endpoints
- `GET /api/v1/resources` - List resources
- `POST /api/v1/resources` - Create resource
- `GET /api/v1/resources/:id` - Get resource
- `PUT /api/v1/resources/:id` - Update resource
- `DELETE /api/v1/resources/:id` - Delete resource

### Authentication Flow
1. User submits credentials → `/api/v1/auth/login`
2. Server validates → Returns JWT token
3. Client stores token → Sends in `Authorization: Bearer <token>`
4. Server validates token on each request

## 4. Data Model

### Core Entities
```sql
-- Users table
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Resources table (example)
CREATE TABLE resources (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    name VARCHAR(255) NOT NULL,
    data JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_resources_user_id ON resources(user_id);
CREATE INDEX idx_resources_created_at ON resources(created_at);
```

## 5. Scalability Strategy

### Horizontal Scaling
- Stateless API servers (scale horizontally)
- Load balancer (NGINX/HAProxy)
- Database read replicas
- Cache layer (Redis cluster)

### Vertical Scaling
- Database: Optimize queries, add indexes
- Application: Profile and optimize bottlenecks

### Caching Strategy
- Cache frequently accessed data
- TTL: 5 minutes for dynamic data, 1 hour for static data
- Invalidation: Event-driven (on updates)

## 6. Security Considerations

- **Authentication:** JWT with short expiration (15 minutes)
- **Authorization:** Role-based access control (RBAC)
- **Data Encryption:** HTTPS (TLS 1.3), encrypted database fields
- **Input Validation:** Pydantic schemas, SQL injection prevention
- **Rate Limiting:** 100 requests/minute per user
- **Audit Logging:** Track all data modifications

## 7. Monitoring & Observability

### Metrics
- Request latency (p50, p95, p99)
- Error rate (4xx, 5xx)
- Database query time
- Cache hit rate

### Logging
- Structured JSON logs
- Log levels: DEBUG, INFO, WARNING, ERROR, CRITICAL
- Centralized logging (ELK stack / CloudWatch)

### Alerting
- API response time > 500ms
- Error rate > 1%
- Database connection pool exhaustion
- Disk usage > 80%

## 8. Deployment Strategy

### Environments
- Development: Local Docker Compose
- Staging: Kubernetes cluster (mimics production)
- Production: Kubernetes cluster (HA, auto-scaling)

### CI/CD Pipeline
1. Commit → Run tests (unit, integration, E2E)
2. Tests pass → Build Docker image
3. Push to registry → Deploy to staging
4. Manual approval → Deploy to production

### Rollback Strategy
- Blue-green deployment
- Canary releases (10% → 50% → 100%)
- Immediate rollback on critical errors

## 9. Cost Estimation

### Monthly Costs (estimated)
- Compute: $200-500 (Kubernetes cluster)
- Database: $50-150 (managed PostgreSQL)
- Cache: $20-50 (Redis)
- Storage: $10-30 (S3/cloud storage)
- Monitoring: $20-50 (Prometheus/Grafana)
- **Total:** $300-780/month

### Optimization Strategies
- Use free tiers (Vercel, Render, Oracle Cloud)
- Auto-scaling (scale down during low traffic)
- Spot instances for non-critical workloads

## 10. Future Enhancements

- GraphQL API (in addition to REST)
- WebSocket for real-time features
- Microservices architecture (if needed)
- Multi-region deployment (global scale)
- Machine learning integration
'''

    output_dir = Path(args.output or "docs/architecture")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"{system_name.lower().replace(' ', '-')}-design.md"

    with open(output_file, 'w') as f:
        f.write(design_doc)

    print_success(f"Created: {output_file}")
    print_info("Review and customize the design document")
    return 0

def create_adr(args):
    print_header(f"Creating ADR: {args.title}")

    adr_number = args.number or 1
    title = args.title
    status = args.status or "Proposed"

    adr_content = f'''# ADR-{adr_number:03d}: {title}

**Date:** {datetime.now().strftime('%Y-%m-%d')}
**Status:** {status}
**Deciders:** [List decision makers]

## Context

[Describe the issue or architectural decision that needs to be made]

## Decision Drivers

- [Driver 1: e.g., Scalability requirements]
- [Driver 2: e.g., Team expertise]
- [Driver 3: e.g., Budget constraints]
- [Driver 4: e.g., Time to market]

## Considered Options

### Option 1: [First Option]
**Pros:**
- [Pro 1]
- [Pro 2]

**Cons:**
- [Con 1]
- [Con 2]

**Cost:** [Estimated cost]

### Option 2: [Second Option]
**Pros:**
- [Pro 1]
- [Pro 2]

**Cons:**
- [Con 1]
- [Con 2]

**Cost:** [Estimated cost]

### Option 3: [Third Option]
**Pros:**
- [Pro 1]
- [Pro 2]

**Cons:**
- [Con 1]
- [Con 2]

**Cost:** [Estimated cost]

## Decision Outcome

**Chosen Option:** [Selected option]

**Rationale:**
[Explain why this option was chosen]

## Consequences

### Positive
- [Positive consequence 1]
- [Positive consequence 2]

### Negative
- [Negative consequence 1]
- [Negative consequence 2]

### Neutral
- [Neutral consequence 1]

## Implementation Notes

[Any implementation details, migration steps, or rollout plan]

## Follow-up Actions

- [ ] [Action 1]
- [ ] [Action 2]
- [ ] [Action 3]

## References

- [Link to relevant documentation]
- [Link to related ADRs]
'''

    output_dir = Path(args.output or "docs/adr")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"{adr_number:03d}-{title.lower().replace(' ', '-')}.md"

    with open(output_file, 'w') as f:
        f.write(adr_content)

    print_success(f"Created: {output_file}")
    print_info(f"ADR Number: {adr_number:03d}")
    print_info(f"Status: {status}")
    return 0

def diagram_architecture(args):
    print_header("Generating Architecture Diagrams")

    diagram_type = args.type or "c4"

    if diagram_type == "c4":
        print_info("C4 Model Diagrams (use diagrams.net or PlantUML):")
        print("\n1. Context Diagram:")
        print("   Shows system in context with external users and systems")
        print("\n2. Container Diagram:")
        print("   Shows high-level technology choices (web app, API, database)")
        print("\n3. Component Diagram:")
        print("   Shows components within each container")
        print("\n4. Code Diagram:")
        print("   Shows class diagrams (usually not needed)")

    elif diagram_type == "sequence":
        print_info("Sequence Diagram Example (PlantUML):")
        print('''
@startuml
actor User
participant "Web App" as Web
participant "API Server" as API
participant "Database" as DB

User -> Web: Click "Login"
Web -> API: POST /api/v1/auth/login
API -> DB: Validate credentials
DB --> API: User found
API --> Web: JWT token
Web --> User: Redirect to dashboard
@enduml
''')

    elif diagram_type == "deployment":
        print_info("Deployment Diagram:")
        print('''
┌─────────────────────────────────────────────────────┐
│                   Production                         │
├─────────────────────────────────────────────────────┤
│                                                      │
│  ┌──────────────┐      ┌──────────────┐            │
│  │ Load Balancer│─────▶│   API Pods   │            │
│  │   (NGINX)    │      │   (3 replicas)            │
│  └──────────────┘      └──────────────┘            │
│                               │                      │
│                               ▼                      │
│                        ┌──────────────┐            │
│                        │  PostgreSQL  │            │
│                        │  (Managed)   │            │
│                        └──────────────┘            │
│                                                      │
└─────────────────────────────────────────────────────┘
''')

    print_success("Diagram templates generated")
    print_info("Tools: diagrams.net, PlantUML, Mermaid, or draw.io")
    return 0

def evaluate_tradeoffs(args):
    print_header("Technology Tradeoffs Analysis")

    choice = args.choice
    options = args.options.split(',') if args.options else []

    print_info(f"Evaluating: {choice}")
    print_info(f"Options: {', '.join(options)}\n")

    # Common tradeoffs
    tradeoffs = {
        "database": {
            "PostgreSQL": "✅ ACID, relations | ❌ Scaling writes",
            "MongoDB": "✅ Schema flexibility, horizontal scaling | ❌ No ACID (single doc only)",
            "DynamoDB": "✅ Serverless, auto-scale | ❌ Vendor lock-in, cost",
        },
        "api": {
            "REST": "✅ Simple, cacheable | ❌ Over-fetching/under-fetching",
            "GraphQL": "✅ Flexible queries | ❌ Complexity, caching hard",
            "gRPC": "✅ Performance, streaming | ❌ Browser support limited",
        },
        "deployment": {
            "Kubernetes": "✅ Orchestration, scaling | ❌ Complexity, cost",
            "Docker Compose": "✅ Simple, local dev | ❌ Not for production",
            "Serverless": "✅ Auto-scale, pay-per-use | ❌ Cold starts, vendor lock-in",
        },
        "auth": {
            "JWT": "✅ Stateless, scalable | ❌ Token revocation hard",
            "Session": "✅ Revocation easy | ❌ Stateful, sticky sessions",
            "OAuth2": "✅ Third-party auth | ❌ Complexity, dependency",
        },
    }

    if choice.lower() in tradeoffs:
        print(f"Tradeoffs for {choice}:\n")
        for option, tradeoff in tradeoffs[choice.lower()].items():
            print(f"  {option}: {tradeoff}")
    else:
        print_warning(f"No predefined tradeoffs for '{choice}'")

    print_info("\nRecommendation Factors:")
    print("  1. Team expertise")
    print("  2. Budget constraints")
    print("  3. Time to market")
    print("  4. Scalability requirements")
    print("  5. Vendor lock-in tolerance")

    return 0

def plan_scaling(args):
    print_header("Scalability Planning")

    current_users = args.current_users or 1000
    target_users = args.target_users or 100000

    print_info(f"Current: {current_users:,} users")
    print_info(f"Target: {target_users:,} users")
    print_info(f"Growth: {(target_users / current_users):.1f}x\n")

    # Scaling recommendations
    print("Horizontal Scaling Strategy:\n")
    print("1. Application Tier:")
    print("   - Current: 2 API servers")
    print(f"   - Target: {max(5, (target_users // 20000))} API servers (auto-scaling)")
    print("   - Stateless design (JWT, no server-side sessions)")

    print("\n2. Database Tier:")
    print("   - Current: Single PostgreSQL instance")
    print("   - Target: Primary + read replicas")
    print(f"   - Read replicas: {max(2, (target_users // 50000))}")

    print("\n3. Caching Layer:")
    print("   - Add Redis cluster")
    print("   - Cache frequently accessed data (90% hit rate target)")
    print("   - Reduce database load by 80%")

    print("\n4. CDN:")
    print("   - Serve static assets from CDN")
    print("   - Edge caching for API responses (where appropriate)")

    print("\n5. Load Balancer:")
    print("   - NGINX/HAProxy")
    print("   - Health checks + automatic failover")

    print_success("\nScalability plan generated")
    return 0

def security_review(args):
    print_header("Security Review Checklist")

    print("## 1. Authentication & Authorization")
    print("  ☐ Strong password policy (min 12 chars, complexity)")
    print("  ☐ MFA/2FA for sensitive operations")
    print("  ☐ JWT with short expiration (15 min)")
    print("  ☐ Refresh tokens with rotation")
    print("  ☐ Role-based access control (RBAC)")

    print("\n## 2. Data Protection")
    print("  ☐ HTTPS everywhere (TLS 1.3)")
    print("  ☐ Encrypt sensitive data at rest")
    print("  ☐ Hash passwords with bcrypt/argon2")
    print("  ☐ Secure secrets management (no hardcoded keys)")
    print("  ☐ Database field-level encryption (PII)")

    print("\n## 3. Input Validation")
    print("  ☐ Validate all user inputs (Pydantic)")
    print("  ☐ Prevent SQL injection (parameterized queries)")
    print("  ☐ Prevent XSS (escape HTML)")
    print("  ☐ Prevent CSRF (tokens, SameSite cookies)")
    print("  ☐ Rate limiting (prevent brute force)")

    print("\n## 4. API Security")
    print("  ☐ API authentication (JWT/API keys)")
    print("  ☐ CORS policy (whitelist origins)")
    print("  ☐ Request size limits (prevent DoS)")
    print("  ☐ Timeout configurations")
    print("  ☐ Error messages (no sensitive info leaks)")

    print("\n## 5. Infrastructure Security")
    print("  ☐ Firewall rules (least privilege)")
    print("  ☐ Container security (scan images)")
    print("  ☐ Kubernetes RBAC")
    print("  ☐ Network policies (pod-to-pod)")
    print("  ☐ Secrets management (Kubernetes secrets/Vault)")

    print("\n## 6. Monitoring & Audit")
    print("  ☐ Audit logs (who did what when)")
    print("  ☐ Security monitoring (intrusion detection)")
    print("  ☐ Vulnerability scanning (dependencies)")
    print("  ☐ Penetration testing (annual)")
    print("  ☐ Incident response plan")

    print_success("\nSecurity checklist complete")
    print_info("Tools: OWASP ZAP, Bandit, Trivy, npm audit")
    return 0

def cost_estimate(args):
    print_header("Cloud Cost Estimation")

    environment = args.environment or "production"
    traffic = args.traffic or "medium"

    print_info(f"Environment: {environment}")
    print_info(f"Traffic: {traffic}\n")

    # Cost breakdown
    costs = {
        "low": {
            "compute": 100,
            "database": 30,
            "cache": 15,
            "storage": 10,
            "bandwidth": 20,
            "monitoring": 10,
        },
        "medium": {
            "compute": 300,
            "database": 100,
            "cache": 40,
            "storage": 30,
            "bandwidth": 60,
            "monitoring": 30,
        },
        "high": {
            "compute": 800,
            "database": 300,
            "cache": 100,
            "storage": 100,
            "bandwidth": 200,
            "monitoring": 80,
        },
    }

    traffic_costs = costs.get(traffic, costs["medium"])

    print("Monthly Cost Breakdown:\n")
    total = 0
    for category, cost in traffic_costs.items():
        print(f"  {category.capitalize():15} ${cost:>6}")
        total += cost

    print(f"  {'─' * 24}")
    print(f"  {'Total':15} ${total:>6}/month\n")

    print("Cost Optimization Strategies:")
    print("  1. Use free tiers (Vercel, Render, Oracle Cloud)")
    print("  2. Spot instances for non-critical workloads")
    print("  3. Auto-scaling (scale down during low traffic)")
    print("  4. Reserved instances (1-3 year commitment)")
    print("  5. Optimize database queries (reduce compute)")
    print("  6. CDN for static assets (reduce bandwidth)")

    print_success(f"\nEstimated cost: ${total}/month")
    return 0

def tech_stack_recommendation(args):
    print_header("Tech Stack Recommendation")

    project_type = args.project_type
    team_size = args.team_size or 5

    print_info(f"Project: {project_type}")
    print_info(f"Team Size: {team_size}\n")

    stacks = {
        "web-app": {
            "frontend": "Next.js 14 (React 18, TypeScript, Tailwind CSS)",
            "backend": "FastAPI (Python) or Node.js (Express/NestJS)",
            "database": "PostgreSQL (relational) or MongoDB (document)",
            "auth": "JWT with refresh tokens",
            "deployment": "Vercel (frontend) + Render/Railway (backend)",
            "testing": "Jest/Vitest (frontend), pytest (backend)",
        },
        "api": {
            "framework": "FastAPI (Python) or Express (Node.js)",
            "database": "PostgreSQL with SQLModel/Prisma",
            "auth": "JWT or OAuth2",
            "docs": "OpenAPI/Swagger",
            "deployment": "Docker + Kubernetes",
            "testing": "pytest or Jest + Supertest",
        },
        "microservices": {
            "framework": "FastAPI (Python) or NestJS (Node.js)",
            "messaging": "Kafka or RabbitMQ",
            "orchestration": "Kubernetes + Helm",
            "service-mesh": "Istio or Linkerd",
            "monitoring": "Prometheus + Grafana",
            "tracing": "Jaeger or OpenTelemetry",
        },
        "realtime": {
            "frontend": "Next.js with WebSocket",
            "backend": "FastAPI with WebSocket or Socket.io",
            "database": "PostgreSQL + Redis (pub/sub)",
            "messaging": "Redis or Kafka",
            "deployment": "Kubernetes with sticky sessions",
            "testing": "pytest-asyncio or Jest",
        },
    }

    if project_type in stacks:
        print(f"Recommended Stack for {project_type}:\n")
        for component, tech in stacks[project_type].items():
            print(f"  {component.replace('-', ' ').title():15}: {tech}")
    else:
        print_warning(f"No recommendation for '{project_type}'")

    print_success("\nTech stack recommendation complete")
    return 0

def main():
    parser = argparse.ArgumentParser(description='Fullstack Architect Expert Tool')
    subparsers = parser.add_subparsers(dest='command')

    # design-system
    design_parser = subparsers.add_parser('design-system', help='Create system design document')
    design_parser.add_argument('--name', required=True, help='System name')
    design_parser.add_argument('--requirements', help='Comma-separated requirements')
    design_parser.add_argument('--output', help='Output directory')

    # create-adr
    adr_parser = subparsers.add_parser('create-adr', help='Create Architecture Decision Record')
    adr_parser.add_argument('--title', required=True, help='ADR title')
    adr_parser.add_argument('--number', type=int, help='ADR number')
    adr_parser.add_argument('--status', default='Proposed', help='Status (Proposed/Accepted/Deprecated)')
    adr_parser.add_argument('--output', help='Output directory')

    # diagram-architecture
    diagram_parser = subparsers.add_parser('diagram-architecture', help='Generate architecture diagrams')
    diagram_parser.add_argument('--type', choices=['c4', 'sequence', 'deployment'], default='c4', help='Diagram type')

    # evaluate-tradeoffs
    tradeoffs_parser = subparsers.add_parser('evaluate-tradeoffs', help='Evaluate technology tradeoffs')
    tradeoffs_parser.add_argument('--choice', required=True, help='Technology choice (database/api/deployment/auth)')
    tradeoffs_parser.add_argument('--options', help='Comma-separated options to evaluate')

    # plan-scaling
    scaling_parser = subparsers.add_parser('plan-scaling', help='Plan scalability strategy')
    scaling_parser.add_argument('--current-users', type=int, default=1000, help='Current users')
    scaling_parser.add_argument('--target-users', type=int, default=100000, help='Target users')

    # security-review
    subparsers.add_parser('security-review', help='Security review checklist')

    # cost-estimate
    cost_parser = subparsers.add_parser('cost-estimate', help='Estimate cloud costs')
    cost_parser.add_argument('--environment', default='production', help='Environment (dev/staging/production)')
    cost_parser.add_argument('--traffic', choices=['low', 'medium', 'high'], default='medium', help='Traffic level')

    # tech-stack-recommendation
    tech_parser = subparsers.add_parser('tech-stack-recommendation', help='Recommend tech stack')
    tech_parser.add_argument('--project-type', required=True, help='Project type (web-app/api/microservices/realtime)')
    tech_parser.add_argument('--team-size', type=int, default=5, help='Team size')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    commands = {
        'design-system': design_system,
        'create-adr': create_adr,
        'diagram-architecture': diagram_architecture,
        'evaluate-tradeoffs': evaluate_tradeoffs,
        'plan-scaling': plan_scaling,
        'security-review': security_review,
        'cost-estimate': cost_estimate,
        'tech-stack-recommendation': tech_stack_recommendation,
    }

    return commands.get(args.command, lambda a: 1)(args)

if __name__ == '__main__':
    sys.exit(main())
