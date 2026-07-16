#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

log() { echo -e "${GREEN}[test]${NC} $*"; }
err() { echo -e "${RED}[error]${NC} $*" >&2; }

cd "$PROJECT_ROOT"

log "Running backend tests with coverage..."
PYTHONPATH=backend python3 -m pytest backend/ \
    -v \
    --tb=short \
    --cov=backend/app \
    --cov-report=term-missing \
    --cov-report=html:htmlcov \
    --cov-report=xml:coverage.xml \
    --junitxml=test-results.xml \
    2>&1

log "Tests complete"
