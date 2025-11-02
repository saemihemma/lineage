#!/usr/bin/env python3
"""
Cross-platform verification script for LINEAGE game.
Runs unit tests and optionally verifies application launch.
"""

import sys
import os
import subprocess
import argparse
import time
from pathlib import Path

# Colors for terminal output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    RESET = '\033[0m'


def colored_print(message, color=None):
    """Print message with color if terminal supports it"""
    if color and sys.stdout.isatty():
        print(f"{color}{message}{Colors.RESET}")
    else:
        print(message)


def find_test_files():
    """Find all test_*.py files in the project root and tests/ directory"""
    project_root = Path(__file__).parent.parent
    test_files = []
    
    # Find test files in root
    for test_file in project_root.glob("test_*.py"):
        test_files.append(str(test_file))
    
    # Find test files in tests/ directory
    tests_dir = project_root / "tests"
    if tests_dir.exists():
        for test_file in tests_dir.glob("test_*.py"):
            test_files.append(str(test_file))
    
    return test_files


def run_tests():
    """Run all unit tests using unittest discover"""
    project_root = Path(__file__).parent.parent
    os.chdir(project_root)
    
    colored_print("\n" + "="*60, Colors.BLUE)
    colored_print("Running Unit Tests", Colors.BOLD + Colors.BLUE)
    colored_print("="*60 + "\n", Colors.BLUE)
    
    # Use unittest discover to find and run all tests
    cmd = [sys.executable, "-m", "unittest", "discover", "-v"]
    
    try:
        result = subprocess.run(
            cmd,
            cwd=project_root,
            capture_output=False,  # Show output in real-time
            text=True
        )
        
        if result.returncode == 0:
            colored_print("\n✓ All tests passed!", Colors.GREEN + Colors.BOLD)
            return True
        else:
            colored_print("\n✗ Some tests failed!", Colors.RED + Colors.BOLD)
            return False
            
    except Exception as e:
        colored_print(f"\n✗ Error running tests: {e}", Colors.RED + Colors.BOLD)
        return False


def run_frontend_build_check():
    """Verify frontend TypeScript compilation and build succeeds"""
    project_root = Path(__file__).parent.parent
    frontend_dir = project_root / "frontend"
    
    if not frontend_dir.exists():
        colored_print("✗ frontend/ directory not found!", Colors.RED + Colors.BOLD)
        return False
    
    colored_print("\n" + "="*60, Colors.BLUE)
    colored_print("Checking Frontend Build", Colors.BOLD + Colors.BLUE)
    colored_print("="*60 + "\n", Colors.BLUE)
    
    # Check if node_modules exists (dependencies installed)
    node_modules = frontend_dir / "node_modules"
    if not node_modules.exists():
        colored_print("⚠ node_modules not found. Installing dependencies...", Colors.YELLOW)
        try:
            result = subprocess.run(
                ["npm", "install"],
                cwd=frontend_dir,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            if result.returncode != 0:
                colored_print(f"✗ npm install failed: {result.stderr}", Colors.RED + Colors.BOLD)
                return False
        except subprocess.TimeoutExpired:
            colored_print("✗ npm install timed out", Colors.RED + Colors.BOLD)
            return False
        except FileNotFoundError:
            colored_print("✗ npm not found. Install Node.js to check frontend build.", Colors.RED + Colors.BOLD)
            return False
    
    # Run TypeScript type check only (faster than full build)
    colored_print("Running TypeScript type check...", Colors.YELLOW)
    try:
        result = subprocess.run(
            ["npm", "run", "build"],
            cwd=frontend_dir,
            capture_output=True,
            text=True,
            timeout=120  # 2 minute timeout
        )
        
        if result.returncode == 0:
            colored_print("✓ Frontend build succeeded!", Colors.GREEN + Colors.BOLD)
            return True
        else:
            colored_print("✗ Frontend build failed!", Colors.RED + Colors.BOLD)
            # Print relevant error output
            if result.stderr:
                # Show last 50 lines of stderr to see the actual error
                lines = result.stderr.split('\n')
                error_lines = lines[-50:] if len(lines) > 50 else lines
                colored_print("\nError output:", Colors.RED)
                print('\n'.join(error_lines))
            return False
            
    except subprocess.TimeoutExpired:
        colored_print("✗ Frontend build timed out", Colors.RED + Colors.BOLD)
        return False
    except FileNotFoundError:
        colored_print("✗ npm not found. Skipping frontend build check.", Colors.YELLOW)
        colored_print("  Install Node.js to enable frontend build verification.", Colors.YELLOW)
        return True  # Don't fail if npm is not available
    except Exception as e:
        colored_print(f"✗ Error checking frontend build: {e}", Colors.RED + Colors.BOLD)
        return False


def verify_app_launch(timeout=10):
    """Verify that the application can launch without errors"""
    project_root = Path(__file__).parent.parent
    os.chdir(project_root)
    
    colored_print("\n" + "="*60, Colors.BLUE)
    colored_print("Verifying Application Launch", Colors.BOLD + Colors.BLUE)
    colored_print("="*60 + "\n", Colors.BLUE)
    
    main_script = project_root / "main.py"
    if not main_script.exists():
        colored_print("✗ main.py not found!", Colors.RED + Colors.BOLD)
        return False
    
    # Launch the app with a timeout
    # Note: We can't easily auto-close tkinter apps, so we'll just verify
    # that it starts without immediate errors
    colored_print(f"Launching {main_script}...", Colors.YELLOW)
    colored_print("(This will open the game window - close it manually to continue)", Colors.YELLOW)
    
    try:
        # Check if tkinter is available
        import tkinter
        colored_print("✓ Tkinter is available", Colors.GREEN)
    except ImportError:
        colored_print("✗ Tkinter is not available!", Colors.RED + Colors.BOLD)
        colored_print("  Install a Python build with Tkinter support", Colors.RED)
        return False
    
    try:
        # Import main to check for syntax errors
        import importlib.util
        spec = importlib.util.spec_from_file_location("main", main_script)
        if spec is None or spec.loader is None:
            colored_print("✗ Could not load main.py", Colors.RED + Colors.BOLD)
            return False
        
        module = importlib.util.module_from_spec(spec)
        
        # Try to load the module (this will catch import/syntax errors)
        try:
            spec.loader.exec_module(module)
            colored_print("✓ main.py loads without syntax errors", Colors.GREEN)
        except Exception as e:
            colored_print(f"✗ Error loading main.py: {e}", Colors.RED + Colors.BOLD)
            return False
        
        # Note: We don't actually run mainloop() here because it would block
        # Instead, we just verify the code can be imported/parsed
        colored_print("✓ Application appears to be launchable", Colors.GREEN)
        colored_print("\nNote: Full launch test requires manual verification", Colors.YELLOW)
        return True
        
    except Exception as e:
        colored_print(f"✗ Error during verification: {e}", Colors.RED + Colors.BOLD)
        return False


def main():
    """Main verification entry point"""
    parser = argparse.ArgumentParser(
        description="Verify LINEAGE game: run tests and optionally check app launch"
    )
    parser.add_argument(
        "--tests-only",
        action="store_true",
        help="Only run tests, skip app verification"
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="Run full verification (tests + app launch)"
    )
    
    args = parser.parse_args()
    
    # Default behavior: run tests only (quick check)
    run_app_check = args.full
    
    colored_print("\n" + "="*60, Colors.BOLD)
    colored_print("LINEAGE Verification", Colors.BOLD)
    colored_print("="*60, Colors.BOLD)
    
    # Step 1: Run backend tests
    tests_passed = run_tests()
    
    if not tests_passed:
        colored_print("\n" + "="*60, Colors.RED)
        colored_print("VERIFICATION FAILED: Backend tests failed", Colors.RED + Colors.BOLD)
        colored_print("="*60 + "\n", Colors.RED)
        sys.exit(1)
    
    # Step 1.5: Check frontend build (TypeScript compilation)
    frontend_build_ok = run_frontend_build_check()
    
    if not frontend_build_ok:
        colored_print("\n" + "="*60, Colors.RED)
        colored_print("VERIFICATION FAILED: Frontend build failed", Colors.RED + Colors.BOLD)
        colored_print("="*60 + "\n", Colors.RED)
        colored_print("Fix TypeScript errors before pushing!", Colors.RED + Colors.BOLD)
        sys.exit(1)
    
    # Step 2: App verification (if requested)
    if run_app_check:
        app_ok = verify_app_launch()
        if not app_ok:
            colored_print("\n" + "="*60, Colors.RED)
            colored_print("VERIFICATION FAILED: App launch check failed", Colors.RED + Colors.BOLD)
            colored_print("="*60 + "\n", Colors.RED)
            sys.exit(1)
    
    # Success!
    colored_print("\n" + "="*60, Colors.GREEN)
    colored_print("✓ VERIFICATION PASSED", Colors.GREEN + Colors.BOLD)
    colored_print("="*60 + "\n", Colors.GREEN)
    
    if not run_app_check:
        colored_print("Note: Use --full to also verify app launch", Colors.YELLOW)
    
    sys.exit(0)


if __name__ == "__main__":
    main()

