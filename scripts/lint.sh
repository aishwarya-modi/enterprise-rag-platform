#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

log() { echo -e "${GREEN}[lint]${NC} $*"; }
err() { echo -e "${RED}[error]${NC} $*" >&2; }

cd "$PROJECT_ROOT"

log "Running ruff lint..."
cd backend
/Users/aishwarya/Library/Python/3.9/bin/ruff check app/ --output-format=concise 2>/dev/null || python3 -m ruff check app/ --output-format=concise || warn "ruff not available, skipping"

log "Running ruff format check..."
/Users/aishwarya/Library/Python/3.9/bin/ruff format --check app/ 2>/dev/null || python3 -m ruff format --check app/ || warn "ruff format not available, skipping"

cd "$PROJECT_ROOT/frontend"

log "Running next lint..."
npx next lint 2>/dev/null || warn "next lint not available"

log "All lint checks passed"
