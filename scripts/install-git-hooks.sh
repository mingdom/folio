#!/bin/bash

# Script to install git hooks

HOOK_DIR=$(git rev-parse --git-dir)/hooks
PROJECT_HOOK_DIR=scripts/git-hooks

echo "Installing git hooks..."

# Make sure the hooks directory exists
mkdir -p $HOOK_DIR

# Copy each hook from the project hooks directory to the git hooks directory
for hook in $PROJECT_HOOK_DIR/*; do
    if [ -f "$hook" ]; then
        hook_name=$(basename $hook)
        echo "Installing $hook_name hook..."
        cp "$hook" "$HOOK_DIR/$hook_name"
        chmod +x "$HOOK_DIR/$hook_name"
    fi
done

echo "Git hooks installed successfully!"
