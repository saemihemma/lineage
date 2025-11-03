#!/bin/bash
#
# Install pre-commit hook for smoke tests
#
# This script installs the pre-commit hook that runs smoke tests
# before every commit, ensuring critical user journeys never break.
#

set -e

HOOK_SOURCE="scripts/pre-commit-hook.sh"
HOOK_TARGET=".git/hooks/pre-commit"

echo "🔧 Installing pre-commit hook for smoke tests..."

# Check if we're in a git repository
if [ ! -d ".git" ]; then
    echo "❌ ERROR: Not in a git repository. Run this from the project root."
    exit 1
fi

# Check if source hook exists
if [ ! -f "$HOOK_SOURCE" ]; then
    echo "❌ ERROR: Hook source not found at $HOOK_SOURCE"
    exit 1
fi

# Copy hook to .git/hooks
cp "$HOOK_SOURCE" "$HOOK_TARGET"
chmod +x "$HOOK_TARGET"

echo "✅ Pre-commit hook installed at $HOOK_TARGET"
echo ""
echo "The hook will now run smoke tests before every commit."
echo "To test it, try making a commit (it will run the tests)."
echo ""
echo "To skip the hook (emergency only):"
echo "  git commit --no-verify -m 'message'"

