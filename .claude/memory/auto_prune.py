#!/usr/bin/env python3
"""
Automatic Memory Pruning Module

Provides automatic memory compaction just like Claude's context management.
Agents import this module and pruning happens automatically in the background.

Usage:
    from .claude.memory.auto_prune import AutoPruneMemory

    # Automatic pruning on every write
    memory = AutoPruneMemory('.claude/memory/agents/live-skill-learner.md')
    memory.append('[2026-02-12 10:00] Fixed bug...')
    # → Automatically prunes if > 100 entries!

Features:
    - Transparent: Agents don't need to know about pruning
    - Automatic: Prunes when threshold exceeded
    - Background: No user intervention needed
    - Safe: Archives before pruning
"""

import os
import re
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Tuple, Optional

# Configuration
MAX_ENTRIES = 100
MAX_SIZE_KB = 100
ARCHIVE_DIR = Path(".claude/memory/archive")

class AutoPruneMemory:
    """
    Automatic memory management with transparent pruning.

    Works like Claude's context compaction - automatically compacts
    when thresholds are exceeded, without user intervention.
    """

    def __init__(self, memory_file: str, max_entries: int = MAX_ENTRIES):
        self.memory_file = Path(memory_file)
        self.max_entries = max_entries
        self.archive_dir = ARCHIVE_DIR

        # Ensure file exists
        if not self.memory_file.exists():
            self.memory_file.parent.mkdir(parents=True, exist_ok=True)
            self.memory_file.touch()

    def append(self, entry: str, auto_prune: bool = True) -> None:
        """
        Append entry to memory and automatically prune if needed.

        Args:
            entry: Memory entry to append (format: [YYYY-MM-DD HH:MM] text)
            auto_prune: Enable automatic pruning (default: True)

        Example:
            memory.append('[2026-02-12 10:00] Fixed JWT bug in auth.py')
            # → Automatically prunes if > 100 entries
        """
        # Append entry
        with open(self.memory_file, 'a') as f:
            f.write(f"{entry}\n")

        # Auto-prune if enabled
        if auto_prune:
            self._check_and_prune()

    def _check_and_prune(self) -> None:
        """
        Check if pruning needed and prune automatically.

        Triggered after every memory write.
        Silent operation - no output to user.
        """
        # Read current file
        if not self.memory_file.exists():
            return

        content = self.memory_file.read_text()

        # Extract entries
        entry_pattern = r'\[(\d{4}-\d{2}-\d{2}[^\]]*)\]\s+([^\n]+)'
        entries = re.findall(entry_pattern, content)

        # Check if pruning needed
        if len(entries) <= self.max_entries:
            return  # No pruning needed

        # Prune automatically
        self._prune_now(entries)

    def _prune_now(self, entries: List[Tuple[str, str]]) -> None:
        """
        Execute pruning immediately (background operation).

        Args:
            entries: List of (timestamp, entry) tuples
        """
        # Separate entries
        entries_to_keep = entries[-self.max_entries:]
        entries_to_archive = entries[:-self.max_entries]

        # Extract patterns
        patterns = self._extract_patterns(entries_to_archive)

        # Create archive
        self._create_archive(entries_to_archive, patterns)

        # Rebuild memory file
        new_content = self._rebuild_file(entries_to_keep, patterns, len(entries))
        self.memory_file.write_text(new_content)

    def _extract_patterns(self, entries: List[Tuple[str, str]]) -> Dict:
        """Extract recurring patterns from archived entries."""
        patterns = {}

        for timestamp, entry in entries:
            # Pattern detection
            entry_lower = entry.lower()

            if "timeout" in entry_lower or "timed out" in entry_lower:
                patterns["connection_timeout"] = patterns.get("connection_timeout", 0) + 1
            elif "config" in entry_lower or "missing" in entry_lower:
                patterns["missing_config"] = patterns.get("missing_config", 0) + 1
            elif "platform" in entry_lower or "os" in entry_lower:
                patterns["platform_specific"] = patterns.get("platform_specific", 0) + 1
            elif "migration" in entry_lower or "database" in entry_lower:
                patterns["database_migration"] = patterns.get("database_migration", 0) + 1
            elif "rename" in entry_lower:
                patterns["rename"] = patterns.get("rename", 0) + 1
            elif "add field" in entry_lower:
                patterns["add_field"] = patterns.get("add_field", 0) + 1
            elif "fix" in entry_lower or "fixed" in entry_lower:
                patterns["bug_fix"] = patterns.get("bug_fix", 0) + 1
            elif "update" in entry_lower or "updated" in entry_lower:
                patterns["update"] = patterns.get("update", 0) + 1

        return patterns

    def _create_archive(self, entries: List[Tuple[str, str]], patterns: Dict) -> Path:
        """Create archive file with compressed history."""
        now = datetime.now()
        month_dir = self.archive_dir / now.strftime("%Y-%m")
        month_dir.mkdir(parents=True, exist_ok=True)

        archive_file = month_dir / f"{self.memory_file.stem}-{now.strftime('%Y-%m')}.md"

        # Build archive content
        if archive_file.exists():
            existing = archive_file.read_text()
            content = existing + f"\n\n## Auto-Pruned: {now.isoformat()}\n\n"
        else:
            content = f"# {self.memory_file.stem.replace('-', ' ').title()} Archive\n\n"
            content += f"**Created:** {now.isoformat()}\n"
            content += f"**Auto-Pruning:** Enabled (like Claude's context compaction)\n\n"

        # Add patterns
        content += "## Extracted Patterns\n\n"
        for pattern, count in sorted(patterns.items(), key=lambda x: x[1], reverse=True):
            content += f"- **{pattern.replace('_', ' ').title()}:** {count} occurrences\n"

        # Add sample entries (10%)
        sample_size = max(1, len(entries) // 10)
        samples = entries[-sample_size:]

        content += f"\n## Sample Entries ({sample_size}/{len(entries)} kept)\n\n"
        for timestamp, entry in samples:
            content += f"[{timestamp}] {entry}\n"

        content += f"\n_(Remaining {len(entries) - sample_size} entries compressed into patterns)_\n"

        archive_file.write_text(content)
        return archive_file

    def _rebuild_file(self, entries: List[Tuple[str, str]], patterns: Dict, total_count: int) -> str:
        """Rebuild memory file with recent entries + pattern summary."""
        content = f"# {self.memory_file.stem.replace('-', ' ').title()} Memory\n\n"
        content += f"**Auto-Pruning:** Enabled (like Claude's context compaction)\n"
        content += f"**Last Pruned:** {datetime.now().isoformat()}\n"
        content += f"**Total Historical:** {total_count} entries\n\n"
        content += "---\n\n"

        # Statistics
        content += "## 📊 Statistics\n\n"
        content += f"- **Active Entries:** {len(entries)}\n"
        content += f"- **Total Historical:** {total_count}\n"
        content += f"- **Archived:** {total_count - len(entries)}\n"
        content += f"- **Compression Ratio:** {((total_count - len(entries)) / total_count * 100):.1f}%\n\n"

        # Patterns (if any archived)
        if patterns:
            content += "## 🎯 Learned Patterns (from archived entries)\n\n"
            for pattern, count in sorted(patterns.items(), key=lambda x: x[1], reverse=True):
                content += f"- **{pattern.replace('_', ' ').title()}:** {count} occurrences\n"
            content += "\n"

        content += "---\n\n"

        # Recent entries
        content += f"## 📝 Recent Entries (Last {len(entries)})\n\n"
        for timestamp, entry in entries:
            content += f"[{timestamp}] {entry}\n"

        content += "\n---\n\n"
        content += "_Auto-pruning: Keeps last 100 entries, compacts older ones (like Claude)_\n"
        content += f"_Archive: `.claude/memory/archive/`_\n"

        return content

    def read_recent(self, limit: Optional[int] = None) -> List[str]:
        """
        Read recent entries from memory.

        Args:
            limit: Number of recent entries to return (default: all)

        Returns:
            List of recent memory entries
        """
        if not self.memory_file.exists():
            return []

        content = self.memory_file.read_text()
        entry_pattern = r'\[(\d{4}-\d{2}-\d{2}[^\]]*)\]\s+([^\n]+)'
        entries = re.findall(entry_pattern, content)

        if limit:
            entries = entries[-limit:]

        return [f"[{ts}] {entry}" for ts, entry in entries]

    def get_stats(self) -> Dict:
        """
        Get memory statistics.

        Returns:
            Dict with current_entries, file_size_kb, needs_pruning
        """
        if not self.memory_file.exists():
            return {
                "current_entries": 0,
                "file_size_kb": 0,
                "needs_pruning": False
            }

        content = self.memory_file.read_text()
        entry_pattern = r'\[(\d{4}-\d{2}-\d{2}[^\]]*)\]\s+([^\n]+)'
        entries = re.findall(entry_pattern, content)

        file_size_kb = len(content) / 1024

        return {
            "current_entries": len(entries),
            "file_size_kb": file_size_kb,
            "needs_pruning": len(entries) > self.max_entries
        }


# Convenience functions for direct use
def append_memory(memory_file: str, entry: str) -> None:
    """
    Quick function to append to memory with auto-pruning.

    Usage:
        from .claude.memory.auto_prune import append_memory
        append_memory('.claude/memory/agents/live-skill-learner.md',
                      '[2026-02-12 10:00] Fixed bug...')
    """
    memory = AutoPruneMemory(memory_file)
    memory.append(entry)


def get_memory_stats(memory_file: str) -> Dict:
    """
    Quick function to get memory statistics.

    Usage:
        from .claude.memory.auto_prune import get_memory_stats
        stats = get_memory_stats('.claude/memory/agents/live-skill-learner.md')
        print(f"Entries: {stats['current_entries']}")
    """
    memory = AutoPruneMemory(memory_file)
    return memory.get_stats()


# Example usage
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python3 auto_prune.py <memory_file>")
        print("Example: python3 auto_prune.py .claude/memory/agents/live-skill-learner.md")
        sys.exit(1)

    memory_file = sys.argv[1]
    memory = AutoPruneMemory(memory_file)

    # Show stats
    stats = memory.get_stats()
    print(f"📊 Memory Statistics: {memory_file}")
    print(f"  Current entries: {stats['current_entries']}")
    print(f"  File size: {stats['file_size_kb']:.1f} KB")
    print(f"  Needs pruning: {'Yes ⚠️' if stats['needs_pruning'] else 'No ✅'}")

    # Show recent entries
    recent = memory.read_recent(limit=5)
    if recent:
        print(f"\n📝 Recent Entries (last 5):")
        for entry in recent:
            print(f"  {entry}")
    else:
        print("\n(No entries yet)")
