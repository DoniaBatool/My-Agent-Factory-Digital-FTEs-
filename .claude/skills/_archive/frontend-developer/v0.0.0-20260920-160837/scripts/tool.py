#!/usr/bin/env python3
"""
Frontend Developer Expert Tool - Next.js/React automation

Commands: create-component, create-page, create-hook, setup-shadcn,
         generate-api-client, create-form, optimize-bundle, audit

Based on Next.js 14, React 18, TypeScript, Tailwind CSS, and shadcn/ui best practices
"""
import argparse, subprocess, sys, os, json
from pathlib import Path

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

def create_component(args):
    print_header(f"Creating React Component: {args.name}")

    component_name = args.name
    component_type = args.type or "client"  # client or server

    # Determine directive
    directive = '"use client";\n\n' if component_type == "client" else ''

    component_code = f'''{directive}import React from 'react';

interface {component_name}Props {{
  // Add your props here
}}

export function {component_name}({{ }}: {component_name}Props) {{
  return (
    <div className="p-4">
      <h2 className="text-2xl font-bold">{component_name}</h2>
      <p className="text-muted-foreground">Component implementation here</p>
    </div>
  );
}}
'''

    output_dir = Path(args.output or "src/components")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"{component_name}.tsx"

    with open(output_file, 'w') as f:
        f.write(component_code)

    print_success(f"Created: {output_file}")
    print_info(f"Type: {component_type.upper()} Component")
    print_info("Next: Import in your page or layout")
    return 0

def create_page(args):
    print_header(f"Creating Next.js Page: {args.route}")

    route = args.route.strip('/')
    route_parts = route.split('/')
    page_name = route_parts[-1] if route_parts else 'home'

    # Create page.tsx for App Router
    page_code = '''import React from 'react';

export default function Page() {
  return (
    <div className="container mx-auto px-4 py-8">
      <h1 className="text-4xl font-bold mb-4">''' + page_name.capitalize() + '''</h1>
      <p className="text-muted-foreground">Page content here</p>
    </div>
  );
}

export const metadata = {
  title: "''' + page_name.capitalize() + '''",
  description: "''' + page_name.capitalize() + ''' page",
};
'''

    output_dir = Path(args.output or "src/app") / route
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "page.tsx"

    with open(output_file, 'w') as f:
        f.write(page_code)

    print_success(f"Created: {output_file}")
    print_info(f"Route: /{route}")
    print_info("Next: Navigate to http://localhost:3000/" + route)
    return 0

def create_hook(args):
    print_header(f"Creating Custom Hook: {args.name}")

    hook_name = args.name if args.name.startswith('use') else f"use{args.name.capitalize()}"

    hook_code = f'''"use client";

import {{ useState, useEffect }} from 'react';

export function {hook_name}() {{
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {{
    // Your logic here
    setLoading(false);
  }}, []);

  return {{ data, loading, error }};
}}
'''

    output_dir = Path(args.output or "src/hooks")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"{hook_name}.ts"

    with open(output_file, 'w') as f:
        f.write(hook_code)

    print_success(f"Created: {output_file}")
    print_info("Usage: const { data, loading, error } = " + hook_name + "()")
    return 0

def setup_shadcn(args):
    print_header("Setting Up shadcn/ui Components")

    components = args.components.split(',') if args.components else ['button', 'input', 'card']

    print_info("Installing shadcn/ui components...")

    for component in components:
        component = component.strip()
        cmd = f"npx shadcn-ui@latest add {component} -y"
        code, stdout, stderr = run_command(cmd)

        if code == 0:
            print_success(f"Installed: {component}")
        else:
            print_error(f"Failed: {component}")
            print_error(stderr)

    print_success("shadcn/ui setup complete")
    print_info("Import: import { Button } from '@/components/ui/button'")
    return 0

def generate_api_client(args):
    print_header("Generating API Client")

    base_url = args.base_url or "http://localhost:8000/api"

    api_client_code = f'''"use client";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "{base_url}";

export class ApiClient {{
  private static getHeaders(token?: string): HeadersInit {{
    const headers: HeadersInit = {{
      'Content-Type': 'application/json',
    }};

    if (token) {{
      headers['Authorization'] = `Bearer ${{token}}`;
    }}

    return headers;
  }}

  static async get<T>(endpoint: string, token?: string): Promise<T> {{
    const response = await fetch(`${{API_BASE_URL}}${{endpoint}}`, {{
      method: 'GET',
      headers: this.getHeaders(token),
    }});

    if (!response.ok) {{
      throw new Error(`HTTP error! status: ${{response.status}}`);
    }}

    return response.json();
  }}

  static async post<T>(endpoint: string, data: any, token?: string): Promise<T> {{
    const response = await fetch(`${{API_BASE_URL}}${{endpoint}}`, {{
      method: 'POST',
      headers: this.getHeaders(token),
      body: JSON.stringify(data),
    }});

    if (!response.ok) {{
      throw new Error(`HTTP error! status: ${{response.status}}`);
    }}

    return response.json();
  }}

  static async put<T>(endpoint: string, data: any, token?: string): Promise<T> {{
    const response = await fetch(`${{API_BASE_URL}}${{endpoint}}`, {{
      method: 'PUT',
      headers: this.getHeaders(token),
      body: JSON.stringify(data),
    }});

    if (!response.ok) {{
      throw new Error(`HTTP error! status: ${{response.status}}`);
    }}

    return response.json();
  }}

  static async delete<T>(endpoint: string, token?: string): Promise<T> {{
    const response = await fetch(`${{API_BASE_URL}}${{endpoint}}`, {{
      method: 'DELETE',
      headers: this.getHeaders(token),
    }});

    if (!response.ok) {{
      throw new Error(`HTTP error! status: ${{response.status}}`);
    }}

    return response.json();
  }}
}}
'''

    output_dir = Path(args.output or "src/lib")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "api-client.ts"

    with open(output_file, 'w') as f:
        f.write(api_client_code)

    print_success(f"Created: {output_file}")
    print_info("Usage: ApiClient.get('/tasks', token)")
    print_info(f"Base URL: {base_url}")
    return 0

def create_form(args):
    print_header(f"Creating Form Component: {args.name}")

    form_name = args.name
    fields = args.fields.split(',') if args.fields else ['name:text', 'email:email']

    # Parse fields
    form_fields = []
    for field in fields:
        if ':' in field:
            field_name, field_type = field.split(':')
            form_fields.append({'name': field_name, 'type': field_type})

    # Generate form component with react-hook-form
    form_code = f'''"use client";

import React from 'react';
import {{ useForm }} from 'react-hook-form';
import {{ Button }} from '@/components/ui/button';
import {{ Input }} from '@/components/ui/input';
import {{ Label }} from '@/components/ui/label';

interface {form_name}Data {{
'''

    for field in form_fields:
        form_code += f"  {field['name']}: string;\n"

    form_code += f'''}}

export function {form_name}() {{
  const {{ register, handleSubmit, formState: {{ errors }} }} = useForm<{form_name}Data>();

  const onSubmit = (data: {form_name}Data) => {{
    console.log(data);
    // Handle form submission
  }};

  return (
    <form onSubmit={{handleSubmit(onSubmit)}} className="space-y-4">
'''

    for field in form_fields:
        form_code += f'''      <div>
        <Label htmlFor="{field['name']}">{field['name'].capitalize()}</Label>
        <Input
          id="{field['name']}"
          type="{field['type']}"
          {{...register("{field['name']}", {{ required: true }})}}
        />
        {{errors.{field['name']} && <span className="text-red-500 text-sm">This field is required</span>}}
      </div>
'''

    form_code += '''      <Button type="submit">Submit</Button>
    </form>
  );
}
'''

    output_dir = Path(args.output or "src/components/forms")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"{form_name}.tsx"

    with open(output_file, 'w') as f:
        f.write(form_code)

    print_success(f"Created: {output_file}")
    print_info("Install: npm install react-hook-form")
    print_info("shadcn: npx shadcn-ui@latest add input label button")
    return 0

def optimize_bundle(args):
    print_header("Bundle Optimization Recommendations")

    print_info("1. Enable webpack bundle analyzer:")
    print("   npm install @next/bundle-analyzer")
    print("   // next.config.js")
    print("   const withBundleAnalyzer = require('@next/bundle-analyzer')()")
    print("   module.exports = withBundleAnalyzer({})")

    print_info("\n2. Use dynamic imports for large components:")
    print("   const HeavyComponent = dynamic(() => import('./HeavyComponent'))")

    print_info("\n3. Optimize images:")
    print("   Use next/image component for automatic optimization")

    print_info("\n4. Enable compression in next.config.js:")
    print("   compress: true")

    print_info("\n5. Tree shaking:")
    print("   Import only what you need: import { Button } from '@/components/ui/button'")

    print_info("\n6. Code splitting:")
    print("   Use React.lazy() and Suspense for route-based code splitting")

    print_success("Optimization guide complete")
    return 0

def audit(args):
    print_header("Frontend Code Audit")

    issues = []

    print_info("Checking for common issues...")

    # Check 1: Missing TypeScript types
    code, stdout, stderr = run_command('grep -r ": any" src/ 2>/dev/null | wc -l')
    if code == 0 and stdout:
        count = stdout.strip()
        if int(count) > 0:
            issues.append(f"⚠️  Found {count} 'any' types (use proper TypeScript types)")

    # Check 2: Missing alt tags on images
    code, stdout, stderr = run_command('grep -r "<img" src/ 2>/dev/null | grep -v "alt=" | wc -l')
    if code == 0 and stdout:
        count = stdout.strip()
        if int(count) > 0:
            issues.append(f"⚠️  Found {count} images without alt tags (accessibility issue)")

    # Check 3: Console.log statements
    code, stdout, stderr = run_command('grep -r "console.log" src/ 2>/dev/null | wc -l')
    if code == 0 and stdout:
        count = stdout.strip()
        if int(count) > 0:
            issues.append(f"⚠️  Found {count} console.log statements (remove in production)")

    # Check 4: Unused CSS/Tailwind classes
    print_info("Run: npx tailwindcss-unused-classes for unused Tailwind classes")

    if issues:
        print_error(f"Found {len(issues)} issues:")
        for issue in issues:
            print(f"  {issue}")
    else:
        print_success("No critical issues found")

    print_info("\nRecommendations:")
    print("  1. Run: npm run lint (ESLint)")
    print("  2. Run: npm run type-check (TypeScript)")
    print("  3. Run: npm audit (security vulnerabilities)")
    print("  4. Run: lighthouse (performance audit)")

    return 0

def main():
    parser = argparse.ArgumentParser(description='Frontend Developer Expert Tool')
    subparsers = parser.add_subparsers(dest='command')

    # create-component
    component_parser = subparsers.add_parser('create-component', help='Create React component')
    component_parser.add_argument('--name', required=True, help='Component name')
    component_parser.add_argument('--type', choices=['client', 'server'], default='client', help='Component type')
    component_parser.add_argument('--output', help='Output directory')

    # create-page
    page_parser = subparsers.add_parser('create-page', help='Create Next.js page')
    page_parser.add_argument('--route', required=True, help='Route path (e.g., /about)')
    page_parser.add_argument('--output', help='Output directory')

    # create-hook
    hook_parser = subparsers.add_parser('create-hook', help='Create custom React hook')
    hook_parser.add_argument('--name', required=True, help='Hook name')
    hook_parser.add_argument('--output', help='Output directory')

    # setup-shadcn
    shadcn_parser = subparsers.add_parser('setup-shadcn', help='Setup shadcn/ui components')
    shadcn_parser.add_argument('--components', default='button,input,card', help='Components to install (comma-separated)')

    # generate-api-client
    api_parser = subparsers.add_parser('generate-api-client', help='Generate API client')
    api_parser.add_argument('--base-url', default='http://localhost:8000/api', help='Base API URL')
    api_parser.add_argument('--output', help='Output directory')

    # create-form
    form_parser = subparsers.add_parser('create-form', help='Create form component')
    form_parser.add_argument('--name', required=True, help='Form name')
    form_parser.add_argument('--fields', default='name:text,email:email', help='Form fields (name:type)')
    form_parser.add_argument('--output', help='Output directory')

    # optimize-bundle
    subparsers.add_parser('optimize-bundle', help='Bundle optimization recommendations')

    # audit
    subparsers.add_parser('audit', help='Frontend code audit')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    commands = {
        'create-component': create_component,
        'create-page': create_page,
        'create-hook': create_hook,
        'setup-shadcn': setup_shadcn,
        'generate-api-client': generate_api_client,
        'create-form': create_form,
        'optimize-bundle': optimize_bundle,
        'audit': audit
    }

    return commands.get(args.command, lambda a: 1)(args)

if __name__ == '__main__':
    sys.exit(main())
