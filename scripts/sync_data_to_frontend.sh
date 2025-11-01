#!/bin/bash
# Sync data files from project root to frontend public directory
# Run this when you update text files in data/ directory

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DATA_DIR="$PROJECT_ROOT/data"
FRONTEND_PUBLIC="$PROJECT_ROOT/frontend/public/data"

echo "Syncing data files to frontend..."

# Create destination directory if it doesn't exist
mkdir -p "$FRONTEND_PUBLIC"

# Copy JSON data files
if [ -f "$DATA_DIR/briefing_text.json" ]; then
  cp "$DATA_DIR/briefing_text.json" "$FRONTEND_PUBLIC/briefing_text.json"
  echo "✓ Copied briefing_text.json"
fi

if [ -f "$DATA_DIR/loading_text.json" ]; then
  cp "$DATA_DIR/loading_text.json" "$FRONTEND_PUBLIC/loading_text.json"
  echo "✓ Copied loading_text.json"
fi

# Copy other data files if needed
for file in "$DATA_DIR"/*.json; do
  if [ -f "$file" ]; then
    filename=$(basename "$file")
    if [ "$filename" != "briefing_text.json" ] && [ "$filename" != "loading_text.json" ]; then
      cp "$file" "$FRONTEND_PUBLIC/$filename"
      echo "✓ Copied $filename"
    fi
  fi
done

echo "Done! Frontend data files synced."
echo ""
echo "Note: Changes will be visible on next browser refresh (no rebuild needed)."

