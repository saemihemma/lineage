#!/usr/bin/env python3
"""
Test Coverage Validation Script

Analyzes git diff to find changed files and suggests which tests should be updated
based on tests/test_map.json configuration.

Usage:
    python scripts/validate_test_coverage.py --check     # Suggestions only (non-blocking)
    python scripts/validate_test_coverage.py --enforce    # Block commit if tests missing (blocking)
"""
import json
import sys
import subprocess
from pathlib import Path
from typing import Dict, List, Set, Optional
from collections import defaultdict


# Colors for terminal output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    RESET = '\033[0m'


def colored_print(message: str, color: Optional[str] = None):
    """Print message with color if terminal supports it"""
    if color and sys.stdout.isatty():
        print(f"{color}{message}{Colors.RESET}")
    else:
        print(message)


def load_test_map() -> Dict:
    """Load test mapping configuration"""
    test_map_path = Path(__file__).parent.parent / "tests" / "test_map.json"
    if not test_map_path.exists():
        colored_print(f"❌ Error: {test_map_path} not found", Colors.RED)
        sys.exit(1)
    
    with open(test_map_path) as f:
        return json.load(f)


def get_changed_files() -> Set[str]:
    """Get list of changed files from git diff --cached"""
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            capture_output=True,
            text=True,
            check=True
        )
        files = {line.strip() for line in result.stdout.strip().split("\n") if line.strip()}
        return files
    except subprocess.CalledProcessError:
        # If no staged files, check unstaged diff
        try:
            result = subprocess.run(
                ["git", "diff", "--name-only"],
                capture_output=True,
                text=True,
                check=True
            )
            files = {line.strip() for line in result.stdout.strip().split("\n") if line.strip()}
            return files
        except subprocess.CalledProcessError:
            return set()


def find_matching_tests(changed_files: Set[str], test_map: Dict) -> Dict[str, List[str]]:
    """
    Find which tests should be updated based on changed files.
    
    Returns dict mapping test file -> list of changed code files that require it
    """
    test_to_code: Dict[str, List[str]] = defaultdict(list)
    
    code_paths = test_map.get("code_paths", {})
    
    for changed_file in changed_files:
        # Check exact matches
        if changed_file in code_paths:
            for test_file in code_paths[changed_file].get("required_tests", []):
                test_to_code[test_file].append(changed_file)
        
        # Check prefix matches (e.g., frontend/src/ matches frontend/src/)
        for code_path, config in code_paths.items():
            if changed_file.startswith(code_path) or code_path.startswith(changed_file):
                for test_file in config.get("required_tests", []):
                    if changed_file not in test_to_code[test_file]:
                        test_to_code[test_file].append(changed_file)
    
    return dict(test_to_code)


def check_test_files_exist(test_files: Set[str]) -> Dict[str, bool]:
    """Check which test files actually exist"""
    project_root = Path(__file__).parent.parent
    results = {}
    
    for test_file in test_files:
        test_path = project_root / test_file
        results[test_file] = test_path.exists()
    
    return results


def check_test_files_changed(test_files: Set[str], changed_files: Set[str]) -> Set[str]:
    """Check which test files were also changed"""
    return test_files.intersection(changed_files)


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Validate test coverage for changed files"
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check mode: suggestions only (non-blocking)"
    )
    parser.add_argument(
        "--enforce",
        action="store_true",
        help="Enforce mode: block commit if tests not updated (blocking)"
    )
    
    args = parser.parse_args()
    
    if not args.check and not args.enforce:
        args.check = True  # Default to check mode
    
    colored_print("🔍 Analyzing code changes for test coverage...", Colors.BLUE)
    print()
    
    # Load test map
    test_map = load_test_map()
    
    # Get changed files
    changed_files = get_changed_files()
    
    if not changed_files:
        colored_print("✅ No files changed - nothing to check", Colors.GREEN)
        return 0
    
    colored_print(f"📝 Found {len(changed_files)} changed file(s):", Colors.BOLD)
    for f in sorted(changed_files):
        print(f"   - {f}")
    print()
    
    # Find matching tests
    test_to_code = find_matching_tests(changed_files, test_map)
    
    if not test_to_code:
        colored_print("✅ No tests need to be updated for these changes", Colors.GREEN)
        return 0
    
    # Check which test files exist and were changed
    test_files = set(test_to_code.keys())
    test_exists = check_test_files_exist(test_files)
    test_changed = check_test_files_changed(test_files, changed_files)
    
    # Categorize tests
    missing_tests = []
    unchanged_tests = []
    changed_tests = []
    
    for test_file, code_files in test_to_code.items():
        if not test_exists.get(test_file, False):
            missing_tests.append((test_file, code_files))
        elif test_file in test_changed:
            changed_tests.append((test_file, code_files))
        else:
            unchanged_tests.append((test_file, code_files))
    
    # Display results
    has_warnings = False
    
    if missing_tests:
        colored_print("❌ MISSING TEST FILES:", Colors.RED)
        for test_file, code_files in missing_tests:
            colored_print(f"   {test_file} (does not exist)", Colors.RED)
            for code_file in code_files:
                print(f"      → Required by: {code_file}")
        has_warnings = True
        print()
    
    if unchanged_tests:
        colored_print("⚠️  TESTS THAT MAY NEED UPDATES:", Colors.YELLOW)
        for test_file, code_files in unchanged_tests:
            colored_print(f"   {test_file}", Colors.YELLOW)
            for code_file in code_files:
                print(f"      → Changed file: {code_file}")
            
            # Get test category
            test_config = test_map.get("test_files", {}).get(test_file, {})
            category = test_config.get("category", "unknown")
            must_pass = test_config.get("must_pass", False)
            
            if must_pass:
                colored_print(f"      ⚠️  REQUIRED: This test must pass (category: {category})", Colors.RED)
            else:
                print(f"      ℹ️  Category: {category}")
        has_warnings = True
        print()
    
    if changed_tests:
        colored_print("✅ TESTS THAT WERE UPDATED:", Colors.GREEN)
        for test_file, code_files in changed_tests:
            colored_print(f"   {test_file} (updated)", Colors.GREEN)
            for code_file in code_files:
                print(f"      → Matches: {code_file}")
        print()
    
    # Summary
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    if missing_tests:
        colored_print(f"❌ {len(missing_tests)} test file(s) are missing", Colors.RED)
    if unchanged_tests:
        colored_print(f"⚠️  {len(unchanged_tests)} test file(s) may need updates", Colors.YELLOW)
    if changed_tests:
        colored_print(f"✅ {len(changed_tests)} test file(s) were updated", Colors.GREEN)
    
    if not has_warnings:
        colored_print("✅ All required tests are present and up to date!", Colors.GREEN)
        print()
        return 0
    
    print()
    
    # Enforcement mode
    if args.enforce:
        if missing_tests:
            colored_print("❌ BLOCKING: Missing required test files", Colors.RED)
            return 1
        
        # Check if critical tests were updated
        critical_tests_need_update = []
        for test_file, code_files in unchanged_tests:
            test_config = test_map.get("test_files", {}).get(test_file, {})
            if test_config.get("must_pass", False):
                critical_tests_need_update.append(test_file)
        
        if critical_tests_need_update:
            colored_print("❌ BLOCKING: Critical tests need updates:", Colors.RED)
            for test_file in critical_tests_need_update:
                print(f"   - {test_file}")
            return 1
        
        return 0
    else:
        # Check mode - just warnings
        colored_print("💡 Tip: Review the tests above and update them if needed", Colors.BLUE)
        colored_print("   Use --enforce to block commits when tests are missing", Colors.BLUE)
        print()
        return 0


if __name__ == "__main__":
    sys.exit(main())

