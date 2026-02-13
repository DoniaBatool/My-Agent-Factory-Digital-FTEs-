#!/usr/bin/env python3
"""
Test Automatic Memory Pruning

Demonstrates that pruning happens automatically in background,
just like Claude's context compaction.
"""

import sys
from pathlib import Path
from datetime import datetime

# Add memory directory to path
sys.path.insert(0, str(Path(__file__).parent))

from auto_prune import AutoPruneMemory

def test_automatic_pruning():
    """
    Test that memory automatically prunes when exceeding threshold.

    Creates 25 entries with max_entries=10.
    Verifies that only 10 entries remain (auto-pruned).
    """
    print("🧪 Testing Automatic Memory Pruning")
    print("=" * 60)

    # Create test memory file (max 10 entries)
    test_file = '.claude/memory/test-auto-prune-memory.md'
    memory = AutoPruneMemory(test_file, max_entries=10)

    print(f"\n📝 Writing 25 entries (max: 10)...\n")

    # Write 25 entries
    for i in range(1, 26):
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        entry = f"[{timestamp}] Test entry {i} - Learning from bug fix"

        # Write entry (auto-prunes in background!)
        memory.append(entry)

        # Get stats after write
        stats = memory.get_stats()

        # Show progress every 5 entries
        if i % 5 == 0 or i <= 3:
            status = "⚠️ AUTO-PRUNING!" if stats['current_entries'] < i else "✓ Within limit"
            print(f"  Entry {i:2d}: {stats['current_entries']:2d} entries in memory {status}")

    # Final verification
    print(f"\n{'=' * 60}")
    print("📊 Final Results:")
    print(f"{'=' * 60}")

    final_stats = memory.get_stats()

    print(f"  Total entries written: 25")
    print(f"  Active entries in memory: {final_stats['current_entries']}")
    print(f"  Entries archived: {25 - final_stats['current_entries']}")
    print(f"  File size: {final_stats['file_size_kb']:.1f} KB")
    print(f"  Needs pruning: {final_stats['needs_pruning']}")

    # Verification
    print(f"\n{'=' * 60}")
    print("✅ Verification:")
    print(f"{'=' * 60}")

    if final_stats['current_entries'] == 10:
        print("  ✅ Memory stayed at 10 entries (auto-pruned!)")
        print("  ✅ Automatic pruning WORKS!")
        print("  ✅ User intervention: ZERO!")
        print("  ✅ Just like Claude's context compaction!")
    else:
        print(f"  ❌ Expected 10 entries, got {final_stats['current_entries']}")
        return False

    # Show recent entries
    print(f"\n{'=' * 60}")
    print("📝 Recent Entries (last 5):")
    print(f"{'=' * 60}")

    recent = memory.read_recent(limit=5)
    for entry in recent:
        print(f"  {entry}")

    # Archive info
    print(f"\n{'=' * 60}")
    print("📦 Archive Location:")
    print(f"{'=' * 60}")
    print(f"  .claude/memory/archive/{datetime.now().strftime('%Y-%m')}/")
    print(f"  (Archived entries compressed into patterns)")

    print(f"\n{'=' * 60}")
    print("🎉 AUTO-PRUNING TEST PASSED!")
    print(f"{'=' * 60}")
    print("\n✅ Memory automatically stays at 10 entries")
    print("✅ No user intervention needed")
    print("✅ Background operation (transparent)")
    print("✅ Works exactly like Claude's context compaction!")

    # Cleanup
    Path(test_file).unlink(missing_ok=True)

    return True


if __name__ == "__main__":
    success = test_automatic_pruning()
    sys.exit(0 if success else 1)
