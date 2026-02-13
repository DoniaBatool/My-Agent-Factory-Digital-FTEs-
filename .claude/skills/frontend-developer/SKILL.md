---
name: frontend-developer
description: Full-time equivalent Frontend Developer agent with Next.js/React automation - components, pages, hooks, shadcn/ui setup, API client, forms, and optimization
---

# Frontend Developer - Expert-Level Automation

**Next.js/React development without manual code generation!**

**Category:** Frontend Development & Automation
**Complexity:** Beginner-Friendly (Expert Power)
**Time Savings:** 70-80% reduction
**Quality:** Production-ready with TypeScript and accessibility

---

## When to Use This Skill

**Use when:**
- Creating React components (client or server)
- Generating Next.js pages with App Router
- Building custom React hooks
- Setting up shadcn/ui components
- Creating type-safe API clients
- Building forms with react-hook-form
- Optimizing bundle size
- Auditing frontend code quality

**Skip when:**
- Backend API development (use /backend-developer)
- Infrastructure setup (use /devops-engineer)
- Database work (use /database-engineer)

---

## What This Skill Provides

**8 Commands covering all frontend tasks:**
- `create-component` → React components (client/server)
- `create-page` → Next.js App Router pages
- `create-hook` → Custom React hooks (useState, useEffect patterns)
- `setup-shadcn` → Install shadcn/ui components
- `generate-api-client` → Type-safe API client with fetch
- `create-form` → Forms with react-hook-form + shadcn/ui
- `optimize-bundle` → Bundle optimization recommendations
- `audit` → Frontend code quality audit

**Features:**
- ✅ Next.js 14 App Router (Server/Client Components)
- ✅ TypeScript strict mode
- ✅ Tailwind CSS styling
- ✅ shadcn/ui integration
- ✅ Type-safe API clients
- ✅ Form validation (react-hook-form)
- ✅ Accessibility (ARIA labels, keyboard navigation)
- ✅ Performance optimization (dynamic imports)

---

## Quick Reference

See README.md for:
- Quick start guide
- All command examples with outputs
- Common workflows
- Troubleshooting

**Most common workflow:**
```bash
# 1. Create page
python3 tool.py create-page --route /dashboard

# 2. Create components
python3 tool.py create-component --name TaskList --type client

# 3. Setup shadcn/ui
python3 tool.py setup-shadcn --components button,input,card

# 4. Generate API client
python3 tool.py generate-api-client --base-url http://localhost:8000/api

# 5. Create form
python3 tool.py create-form --name TaskForm --fields "title:text,description:textarea"

# 6. Audit code
python3 tool.py audit
```

---

## Professional Profile

**Role**: Senior Frontend Developer (FTE Digital Employee)
**Expertise**: React 18, Next.js 14, TypeScript, Tailwind CSS, shadcn/ui
**Principles**: Component reusability, type safety, accessibility, performance

---

## Default Standards

- **TypeScript strict mode**: No `any` types, full type coverage
- **Component patterns**: Composition over inheritance
- **Accessibility**: ARIA labels, semantic HTML, keyboard navigation
- **Performance**: Code splitting, lazy loading, optimized images
- **Styling**: Tailwind CSS with class-variance-authority
- **Forms**: react-hook-form with Zod validation
- **State**: React Query for server state, Zustand for client state

---

## Advanced Patterns

### Pattern 1: Complete Feature UI Development

**Scenario:** Build a "Projects Dashboard" feature.

```bash
# Step 1: Create page
python3 tool.py create-page --route /projects

# Step 2: Create list component
python3 tool.py create-component --name ProjectList --type client

# Step 3: Create card component
python3 tool.py create-component --name ProjectCard --type client

# Step 4: Setup UI components
python3 tool.py setup-shadcn --components button,card,input,badge

# Step 5: Create custom hook
python3 tool.py create-hook --name useProjects

# Step 6: Generate API client
python3 tool.py generate-api-client

# Step 7: Create form
python3 tool.py create-form --name ProjectForm --fields "name:text,description:textarea,status:select"
```

**Time saved:** 3-4 hours → 20 minutes

---

### Pattern 2: shadcn/ui Component Installation

**Scenario:** Setup complete UI component library.

```bash
# Install all common components
python3 tool.py setup-shadcn \
  --components button,input,card,badge,alert,dialog,dropdown-menu,select,textarea,toast

# Generated in components/ui/:
# - button.tsx
# - input.tsx
# - card.tsx
# - badge.tsx
# - alert.tsx
# - dialog.tsx
# - dropdown-menu.tsx
# - select.tsx
# - textarea.tsx
# - toast.tsx
```

**Benefits:** Production-ready components with accessibility

---

### Pattern 3: Type-Safe API Integration

**Scenario:** Connect frontend to FastAPI backend.

```bash
# Generate API client
python3 tool.py generate-api-client --base-url http://localhost:8000/api

# Generated: src/lib/api-client.ts
# - ApiClient class
# - HTTP methods (GET, POST, PUT, DELETE)
# - JWT token integration
# - Error handling
# - TypeScript generics

# Usage in component:
# const tasks = await ApiClient.get<Task[]>('/tasks', token)
```

**Type Safety:** Full TypeScript coverage with generics

---

### Pattern 4: Form Generation with Validation

**Scenario:** Create task creation form.

```bash
# Generate form component
python3 tool.py create-form \
  --name TaskForm \
  --fields "title:text,description:textarea,due_date:date,priority:select"

# Generated:
# - react-hook-form integration
# - shadcn/ui components
# - Validation (required fields)
# - Error messages
# - Submit handler
```

**Validation:** Built-in with react-hook-form

---

### Pattern 5: Performance Optimization

**Scenario:** Optimize bundle size and performance.

```bash
# Get optimization recommendations
python3 tool.py optimize-bundle

# Recommendations:
# 1. Enable webpack bundle analyzer
# 2. Use dynamic imports for large components
# 3. Optimize images with next/image
# 4. Enable compression
# 5. Tree shaking imports
# 6. Code splitting with React.lazy()
```

**Performance:** Lighthouse score > 90

---

## Success Metrics

**Time Savings:**
- ✅ 70-80% faster frontend development
- ✅ Instant component scaffolding
- ✅ No manual form code writing

**Quality:**
- ✅ TypeScript strict mode enforced
- ✅ Accessibility built-in
- ✅ shadcn/ui component library
- ✅ Best practices enforced

**Cost Savings:**
- ✅ No frontend specialist needed
- ✅ Faster feature delivery
- ✅ Consistent code quality

---

## Integration with Other Skills

**Works well with:**

1. **backend-developer** - API integration
2. **uiux-designer** - Design system implementation
3. **qa-engineer** - E2E testing with Playwright
4. **vercel-deployer** - Production deployment
5. **performance-logger** - Frontend monitoring

---

## Workflow

### Phase 1: Requirements Analysis
- Define UI components needed
- Determine page routes
- Plan state management

### Phase 2: Implement
- Use tool.py commands to generate code
- Customize components as needed
- Add business logic

### Phase 3: Hardening
- Run audit for code quality
- Optimize bundle size
- Test accessibility
- Performance optimization

---

## Common Deliverables

- [ ] React components (reusable UI)
- [ ] Next.js pages (App Router)
- [ ] Custom hooks (shared logic)
- [ ] shadcn/ui components installed
- [ ] Type-safe API client
- [ ] Forms with validation
- [ ] Performance optimized
- [ ] Accessibility compliant

---

**Status:** Production-ready ✅
**No frontend specialist needed!** 🚀
**70-80% time savings!** ⚡
