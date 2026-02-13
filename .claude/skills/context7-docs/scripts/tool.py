#!/usr/bin/env python3
"""
Context7 MCP Documentation Lookup Tool

This script provides on-demand access to library documentation
via the Context7 MCP server.

Usage:
    python tool.py --library fastapi --query "dependency injection"
    python tool.py --library nextjs --query "app router"
    python tool.py --library helm --query "chart templates"
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Optional


class Context7Client:
    """Client for interacting with Context7 MCP server."""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Context7 client.

        Args:
            api_key: Context7 API key. If not provided, reads from .mcp.json
        """
        self.api_key = api_key or self._load_api_key()

    def _load_api_key(self) -> str:
        """Load API key from .claude/.mcp.json configuration."""
        # Try multiple possible locations
        possible_paths = [
            Path(__file__).parent.parent.parent.parent / ".mcp.json",  # .claude/.mcp.json
            Path.home() / ".claude" / ".mcp.json",  # ~/.claude/.mcp.json
        ]

        for mcp_config_path in possible_paths:
            if mcp_config_path.exists():
                try:
                    with open(mcp_config_path) as f:
                        config = json.load(f)

                    # Extract API key from context7 server config
                    context7_config = config.get("mcpServers", {}).get("context7", {})
                    args = context7_config.get("args", [])

                    # Find --api-key argument
                    for i, arg in enumerate(args):
                        if arg == "--api-key" and i + 1 < len(args):
                            return args[i + 1]
                except (json.JSONDecodeError, KeyError):
                    continue

        raise ValueError(
            "Context7 API key not found. Please configure in .claude/.mcp.json"
        )

    def resolve_library(self, library_name: str) -> dict:
        """
        Resolve library name to Context7 library ID.

        Args:
            library_name: Name of the library (e.g., "fastapi", "nextjs")

        Returns:
            Library metadata including ID
        """
        # This would call the MCP server's resolve-library-id tool
        # For now, return a placeholder
        return {
            "library": library_name,
            "status": "resolved",
            "message": f"Ready to search {library_name} documentation"
        }

    def search_docs(self, library_name: str, query: str, max_tokens: int = 5000) -> dict:
        """
        Search library documentation for a specific query.

        Args:
            library_name: Name of the library
            query: Search query
            max_tokens: Maximum tokens to return (default 5000)

        Returns:
            Documentation results
        """
        # This would call the MCP server's get-library-docs tool
        # For now, return instructions for MCP usage
        return {
            "library": library_name,
            "query": query,
            "max_tokens": max_tokens,
            "mcp_tool": "get-library-docs",
            "instructions": f"""
To fetch documentation, use the Context7 MCP tools:

1. First resolve the library ID:
   Tool: resolve-library-id
   Input: {{"libraryName": "{library_name}"}}

2. Then get documentation:
   Tool: get-library-docs
   Input: {{
       "context7CompatibleLibraryID": "<id-from-step-1>",
       "topic": "{query}",
       "tokens": {max_tokens}
   }}
"""
        }


def main():
    """Main entry point for CLI usage."""
    parser = argparse.ArgumentParser(
        description="Context7 Documentation Lookup Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python tool.py --library fastapi --query "dependency injection"
  python tool.py --library nextjs --query "app router server components"
  python tool.py --library kubernetes --query "deployment yaml"
  python tool.py --library helm --query "chart templates values"
        """
    )

    parser.add_argument(
        "--library", "-l",
        required=True,
        help="Library name (e.g., fastapi, nextjs, kubernetes)"
    )

    parser.add_argument(
        "--query", "-q",
        required=True,
        help="Search query for documentation"
    )

    parser.add_argument(
        "--max-tokens", "-t",
        type=int,
        default=5000,
        help="Maximum tokens to return (default: 5000)"
    )

    parser.add_argument(
        "--api-key", "-k",
        help="Context7 API key (optional, reads from .mcp.json if not provided)"
    )

    parser.add_argument(
        "--json", "-j",
        action="store_true",
        help="Output in JSON format"
    )

    args = parser.parse_args()

    try:
        client = Context7Client(api_key=args.api_key)

        # Resolve library
        resolve_result = client.resolve_library(args.library)

        # Search documentation
        docs_result = client.search_docs(
            library_name=args.library,
            query=args.query,
            max_tokens=args.max_tokens
        )

        if args.json:
            output = {
                "library": args.library,
                "query": args.query,
                "resolve": resolve_result,
                "search": docs_result
            }
            print(json.dumps(output, indent=2))
        else:
            print(f"""
╔══════════════════════════════════════════════════════════════╗
║  🔧 Context7 Documentation Lookup                            ║
╠══════════════════════════════════════════════════════════════╣
║  Library: {args.library:<50} ║
║  Query: {args.query:<52} ║
║  Max Tokens: {args.max_tokens:<46} ║
╚══════════════════════════════════════════════════════════════╝

{docs_result['instructions']}

To use via MCP in Claude Code:
1. Ensure context7 MCP server is configured in .claude/.mcp.json
2. Claude will automatically use the MCP tools when this skill is invoked
""")

    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
