#!/bin/bash
set -euo pipefail

# Source directory is the parent of this script
SOURCE_DIR="$(cd "$(dirname "$0")" && pwd)"
SKILL_DIR=~/.agents/skills/gsd-to-github

mkdir -p "$SKILL_DIR"
# Copy everything except .git directory and install.sh itself
rsync -a --exclude='.git' --exclude='install.sh' "$SOURCE_DIR"/ "$SKILL_DIR/"

echo "Installed to $SKILL_DIR"
