---
name: api-contract-design
description: Design API contracts using OpenAPI specification, ensuring backward compatibility, proper versioning, and contract-first development approach.
---

# API Contract Design Skill

## Purpose
Implement contract-first API development using OpenAPI specifications to ensure API consistency and prevent breaking changes.

## When to Use
- Designing new APIs
- Microservices communication contracts
- Third-party API integration
- API versioning
- Client-server contract agreements

## OpenAPI Contract Example

```yaml
openapi: 3.0.0
info:
  title: Todo API
  version: 1.0.0
  description: Task management API

servers:
  - url: https://api.example.com/v1

paths:
  /tasks:
    get:
      summary: List tasks
      parameters:
        - name: status
          in: query
          schema:
            type: string
            enum: [pending, completed]
      responses:
        '200':
          description: Success
          content:
            application/json:
              schema:
                type: array
                items:
                  $ref: '#/components/schemas/Task'

    post:
      summary: Create task
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/CreateTaskInput'
      responses:
        '201':
          description: Created
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Task'

  /tasks/{id}:
    get:
      summary: Get task by ID
      parameters:
        - name: id
          in: path
          required: true
          schema:
            type: string
            format: uuid
      responses:
        '200':
          description: Success
        '404':
          description: Not found

components:
  schemas:
    Task:
      type: object
      required:
        - id
        - title
        - status
      properties:
        id:
          type: string
          format: uuid
        title:
          type: string
          minLength: 1
          maxLength: 200
        description:
          type: string
        status:
          type: string
          enum: [pending, in_progress, completed]
        created_at:
          type: string
          format: date-time

    CreateTaskInput:
      type: object
      required:
        - title
      properties:
        title:
          type: string
        description:
          type: string

  securitySchemes:
    BearerAuth:
      type: http
      scheme: bearer
      bearerFormat: JWT

security:
  - BearerAuth: []
```

## API Versioning Strategies

### 1. URL Versioning (Recommended)
```
/v1/tasks
/v2/tasks
```

### 2. Header Versioning
```
Accept: application/vnd.api+json;version=1
```

### 3. Query Parameter
```
/tasks?version=1
```

## Best Practices

✅ **Contract-First**: Design API before implementation
✅ **Backward Compatibility**: Never break existing clients
✅ **Versioning**: Plan for API evolution
✅ **Documentation**: Auto-generate from OpenAPI spec
✅ **Validation**: Validate requests against schema
✅ **Examples**: Provide request/response examples

## Breaking vs Non-Breaking Changes

**Non-Breaking (Safe):**
- Adding new endpoints
- Adding optional fields
- Adding enum values (with caution)
- Expanding string lengths

**Breaking (Require New Version):**
- Removing endpoints
- Removing fields
- Changing field types
- Renaming fields
- Making optional fields required

## Tools

- **Design**: Swagger Editor, Stoplight Studio
- **Validation**: openapi-spec-validator
- **Code Generation**: openapi-generator
- **Documentation**: Swagger UI, ReDoc
- **Testing**: Dredd, Schemathesis

## Workflow

1. **Design** OpenAPI spec
2. **Review** with stakeholders
3. **Generate** client/server code
4. **Implement** backend logic
5. **Validate** requests/responses
6. **Document** auto-generated docs
7. **Version** when breaking changes needed

---

**Status:** Active
**Priority:** 🔴 High (Contract-first development)
**Version:** 1.0.0
**Category:** API Design
