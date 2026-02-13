#!/usr/bin/env python3
"""
Memory Pruning Script

Automatically prunes agent memory files to prevent context explosion.

Usage:
    python3 prune-memory.py                    # Prune all memory files
    python3 prune-memory.py --agent live-skill-learner  # Specific agent
    python3 prune-memory.py --dry-run          # Show what would be pruned
"""

import os
import re
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Tuple

# Configuration
MAX_ENTRIES = 100
MAX_SIZE_KB = 100
ARCHIVE_DIR = Path(".claude/memory/archive")
MEMORY_DIR = Path(".claude/memory/agents")

class MemoryPruner:
    def __init__(self, dry_run=False):
        self.dry_run = dry_run
        self.stats = {
            "files_checked": 0,
            "files_pruned": 0,
            "entries_archived": 0,
            "bytes_saved": 0
        }

    def prune_agent_memory(self, memory_file: Path) -> Tuple[int, int]:
        """Prune a single agent memory file.

        Returns: (entries_archived, bytes_saved)
        """
        if not memory_file.exists():
            return 0, 0

        # Read current file
        content = memory_file.read_text()
        original_size = len(content)

        # Extract entries (format: [YYYY-MM-DD HH:MM] ...)
        entry_pattern = r'\[(\d{4}-\d{2}-\d{2}[^\]]*)\]\s+([^\n]+)'
        entries = re.findall(entry_pattern, content)

        if len(entries) <= MAX_ENTRIES:
            print(f"✓ {memory_file.name}: {len(entries)} entries (within limit)")
            return 0, 0

        # Separate entries to keep vs archive
        entries_to_keep = entries[-MAX_ENTRIES:]  # Last 100
        entries_to_archive = entries[:-MAX_ENTRIES]  # Older ones

        # Extract patterns before archiving details
        patterns = self._extract_patterns(entries_to_archive)

        # Create archive
        archive_path = self._create_archive(memory_file, entries_to_archive, patterns)

        # Rewrite memory file with kept entries
        if not self.dry_run:
            new_content = self._rebuild_memory_file(
                memory_file,
                entries_to_keep,
                patterns,
                len(entries)
            )
            memory_file.write_text(new_content)
            new_size = len(new_content)
        else:
            new_size = original_size // 2  # Estimate

        bytes_saved = original_size - new_size

        print(f"✓ {memory_file.name}: Archived {len(entries_to_archive)} entries")
        print(f"  Kept: {len(entries_to_keep)} recent entries")
        print(f"  Saved: {bytes_saved / 1024:.1f} KB")
        print(f"  Archive: {archive_path}")

        return len(entries_to_archive), bytes_saved

    def _extract_patterns(self, entries: List[Tuple[str, str]]) -> Dict:
        """Extract recurring patterns from entries."""
        patterns = {}

        for timestamp, entry in entries:
            # Simple pattern: extract issue type
            if "timeout" in entry.lower():
                patterns["connection_timeout"] = patterns.get("connection_timeout", 0) + 1
            elif "config" in entry.lower() or "missing" in entry.lower():
                patterns["missing_config"] = patterns.get("missing_config", 0) + 1
            elif "platform" in entry.lower() or "os" in entry.lower():
                patterns["platform_specific"] = patterns.get("platform_specific", 0) + 1
            elif "migration" in entry.lower() or "database" in entry.lower():
                patterns["database_migration"] = patterns.get("database_migration", 0) + 1
            elif "rename" in entry.lower():
                patterns["rename"] = patterns.get("rename", 0) + 1
            elif "add field" in entry.lower():
                patterns["add_field"] = patterns.get("add_field", 0) + 1

        return patterns

    def _create_archive(self, memory_file: Path, entries: List, patterns: Dict) -> Path:
        """Create archive file with old entries and patterns."""
        # Determine archive path
        now = datetime.now()
        month_dir = ARCHIVE_DIR / now.strftime("%Y-%m")
        month_dir.mkdir(parents=True, exist_ok=True)

        archive_file = month_dir / f"{memory_file.stem}-{now.strftime('%Y-%m')}.md"

        # Check if archive exists, append if so
        if archive_file.exists():
            existing = archive_file.read_text()
            archive_content = existing + f"\n\n## Archived: {now.isoformat()}\n\n"
        else:
            archive_content = f"# {memory_file.stem} Archive - {now.strftime('%B %Y')}\n\n"
            archive_content += f"**Created:** {now.isoformat()}\n\n"
            archive_content += "## Summary Statistics\n\n"
            archive_content += f"- Entries archived: {len(entries)}\n\n"

        # Add patterns
        archive_content += "## Extracted Patterns\n\n"
        for pattern, count in sorted(patterns.items(), key=lambda x: x[1], reverse=True):
            archive_content += f"- **{pattern.replace('_', ' ').title()}:** {count} occurrences\n"

        # Add high-impact entries only (keep last 10% as examples)
        high_impact = entries[int(len(entries) * 0.9):]
        archive_content += "\n## Sample Entries (10% kept as examples)\n\n"
        for timestamp, entry in high_impact:
            archive_content += f"[{timestamp}] {entry}\n"

        archive_content += f"\n_(Remaining {len(entries) - len(high_impact)} entries compressed into patterns above)_\n"

        if not self.dry_run:
            archive_file.write_text(archive_content)

        return archive_file

    def _rebuild_memory_file(self, memory_file: Path, entries: List, patterns: Dict, total_count: int) -> str:
        """Rebuild memory file with kept entries and pattern summary."""
        content = f"# {memory_file.stem.replace('-', ' ').title()} Memory\n\n"
        content += f"**Last Pruned:** {datetime.now().isoformat()}\n"
        content += f"**Total Historical Entries:** {total_count}\n\n"

        content += "---\n\n## 📊 Statistics\n\n"
        content += f"- **Active Entries:** {len(entries)}\n"
        content += f"- **Total Historical:** {total_count}\n"
        content += f"- **Archived:** {total_count - len(entries)}\n\n"

        content += "## 🎯 Extracted Patterns (from archived entries)\n\n"
        for pattern, count in sorted(patterns.items(), key=lambda x: x[1], reverse=True):
            content += f"- **{pattern.replace('_', ' ').title()}:** {count} occurrences\n"

        content += "\n---\n\n## 📝 Recent Entries (Last 100)\n\n"
        for timestamp, entry in entries:
            content += f"[{timestamp}] {entry}\n"

        content += "\n---\n\n"
        content += "**Auto-pruning:** Keeps last 100 entries, archives older ones\n"
        content += "**Archive location:** `.claude/memory/archive/`\n"

        return content

    def prune_shared_memory(self, shared_file: Path) -> Tuple[int, int]:
        """Prune shared memory file by compressing agent sections."""
        if not shared_file.exists():
            return 0, 0

        content = shared_file.read_text()
        original_size = len(content)

        # Check size
        if original_size < MAX_SIZE_KB * 1024 * 2:  # 200KB limit for shared
            print(f"✓ {shared_file.name}: {original_size / 1024:.1f} KB (within limit)")
            return 0, 0

        print(f"⚠ {shared_file.name}: {original_size / 1024:.1f} KB (needs pruning)")
        print(f"  Shared memory should be pruned by updating agent sections")
        print(f"  Each agent should keep only summary stats, not full history")

        # For shared memory, we don't auto-prune (too risky)
        # Instead, we recommend manual review
        return 0, 0

    def run(self, agent_name: str = None):
        """Run pruning on all or specific agent memory."""
        print("🔍 Memory Pruning - Starting...\n")

        if agent_name:
            # Prune specific agent
            memory_file = MEMORY_DIR / f"{agent_name}.md"
            archived, saved = self.prune_agent_memory(memory_file)
            self.stats["files_checked"] = 1
            if archived > 0:
                self.stats["files_pruned"] = 1
                self.stats["entries_archived"] = archived
                self.stats["bytes_saved"] = saved
        else:
            # Prune all agent memory files
            for memory_file in MEMORY_DIR.glob("*.md"):
                self.stats["files_checked"] += 1
                archived, saved = self.prune_agent_memory(memory_file)
                if archived > 0:
                    self.stats["files_pruned"] += 1
                    self.stats["entries_archived"] += archived
                    self.stats["bytes_saved"] += saved

            # Check shared memory
            shared_file = MEMORY_DIR.parent / "agents-memory.md"
            self.prune_shared_memory(shared_file)

        # Print summary
        print("\n📊 Pruning Summary:")
        print(f"  Files checked: {self.stats['files_checked']}")
        print(f"  Files pruned: {self.stats['files_pruned']}")
        print(f"  Entries archived: {self.stats['entries_archived']}")
        print(f"  Space saved: {self.stats['bytes_saved'] / 1024:.1f} KB")

        if self.dry_run:
            print("\n⚠️  DRY RUN - No changes made")
        else:
            print("\n✅ Pruning complete!")

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Prune agent memory files")
    parser.add_argument("--agent", help="Specific agent to prune")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be pruned")

    args = parser.parse_args()

    pruner = MemoryPruner(dry_run=args.dry_run)
    pruner.run(agent_name=args.agent)
