#!/usr/bin/env python3
"""
Batch convert all ACTIVITY markdown files to HTML.

This script finds all ACTIVITY_*.md files in the repository and converts them
to HTML using convert_activity_to_html.py
"""

import subprocess
import sys
from pathlib import Path


def find_activity_files(repo_root: Path) -> list[Path]:
    """Find all ACTIVITY_*.md files in the repository."""
    activity_files = []
    
    # Search in numbered module directories (00_*, 01_*, etc.)
    for module_dir in sorted(repo_root.glob('[0-9][0-9]_*')):
        if module_dir.is_dir():
            # Search in module directory and subdirectories
            for md_file in module_dir.rglob('ACTIVITY_*.md'):
                activity_files.append(md_file)
    
    return sorted(activity_files)


def main():
    """Main entry point."""
    # Find repo root
    repo_root = None
    current = Path(__file__).resolve().parent.parent.parent.parent
    while current != current.parent:
        if (current / '.git').exists() or (current / '.gitignore').exists():
            repo_root = current
            break
        current = current.parent
    
    if not repo_root:
        repo_root = Path.cwd()
    
    # Get the convert script path
    convert_script = Path(__file__).parent / 'convert_activity_to_html.py'
    
    if not convert_script.exists():
        print(f"Error: convert_activity_to_html.py not found at {convert_script}")
        sys.exit(1)
    
    # Find all ACTIVITY files
    activity_files = find_activity_files(repo_root)
    
    if not activity_files:
        print("No ACTIVITY_*.md files found.")
        sys.exit(0)
    
    print(f"Found {len(activity_files)} ACTIVITY file(s) to convert:\n")
    
    # Convert each file
    success_count = 0
    error_count = 0
    
    for md_file in activity_files:
        rel_path = md_file.relative_to(repo_root)
        print(f"Converting: {rel_path}")
        
        try:
            result = subprocess.run(
                [sys.executable, str(convert_script), str(md_file)],
                capture_output=True,
                text=True,
                cwd=repo_root
            )
            
            if result.returncode == 0:
                print(f"  ✓ Success")
                success_count += 1
            else:
                print(f"  ✗ Error: {result.stderr.strip()}")
                error_count += 1
        except Exception as e:
            print(f"  ✗ Exception: {e}")
            error_count += 1
    
    print(f"\n{'='*60}")
    print(f"Summary: {success_count} succeeded, {error_count} failed")
    print(f"{'='*60}")


if __name__ == '__main__':
    main()
