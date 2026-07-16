#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
REGISTRY="${REGISTRY:-ghcr.io}"
ORG="${ORG:-enterprise-rag}"
TAG="${TAG:-$(git rev-parse --short HEAD)}"
NAMESPACE="${NAMESPACE:-rag-platform}"
RELEASE_NAME="${RELEASE_NAME:-rag-platform}"
CHART_PATH="$PROJECT_ROOT/helm/rag-platform"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() { echo -e "${GREEN}[deploy]${NC} $*"; }
warn() { echo -e "${YELLOW}[warn]${NC} $*"; }
err() { echo -e "${RED}[error]${NC} $*" >&2; }

usage() {
    cat <<EOF
Usage: $0 <command>

Commands:
  build       Build Docker images
  push        Push Docker images to registry
  deploy      Deploy to Kubernetes via Helm
  upgrade     Upgrade existing deployment
  teardown    Remove deployment
  status      Show deployment status
  logs        Tail logs from all pods

Environment:
  REGISTRY     Container registry (default: ghcr.io)
  ORG          Organization (default: enterprise-rag)
  TAG          Image tag (default: git short SHA)
  NAMESPACE    Kubernetes namespace (default: rag-platform)
  RELEASE_NAME Helm release name (default: rag-platform)
EOF
}

cmd_build() {
    log "Building backend image: $REGISTRY/$ORG/backend:$TAG"
    docker build -t "$REGISTRY/$ORG/backend:$TAG" -t "$REGISTRY/$ORG/backend:latest" "$PROJECT_ROOT/backend"

    log "Building frontend image: $REGISTRY/$ORG/frontend:$TAG"
    docker build -t "$REGISTRY/$ORG/frontend:$TAG" -t "$REGISTRY/$ORG/frontend:latest" "$PROJECT_ROOT/frontend"

    log "Build complete"
}

cmd_push() {
    log "Pushing images to $REGISTRY/$ORG..."
    docker push "$REGISTRY/$ORG/backend:$TAG"
    docker push "$REGISTRY/$ORG/backend:latest"
    docker push "$REGISTRY/$ORG/frontend:$TAG"
    docker push "$REGISTRY/$ORG/frontend:latest"
    log "Push complete"
}

cmd_deploy() {
    log "Deploying $RELEASE_NAME to namespace $NAMESPACE..."

    kubectl create namespace "$NAMESPACE" --dry-run=client -o yaml | kubectl apply -f -

    helm dependency update "$CHART_PATH" 2>/dev/null || true

    helm upgrade --install "$RELEASE_NAME" "$CHART_PATH" \
        --namespace "$NAMESPACE" \
        --set backend.image.repository="$REGISTRY/$ORG/backend" \
        --set backend.image.tag="$TAG" \
        --set frontend.image.repository="$REGISTRY/$ORG/frontend" \
        --set frontend.image.tag="$TAG" \
        --wait \
        --timeout 5m

    log "Deploy complete"
    cmd_status
}

cmd_upgrade() {
    log "Upgrading $RELEASE_NAME..."
    cmd_deploy
}

cmd_teardown() {
    warn "Removing release $RELEASE_NAME from namespace $NAMESPACE..."
    helm uninstall "$RELEASE_NAME" --namespace "$NAMESPACE" || true
    log "Teardown complete"
}

cmd_status() {
    echo ""
    log "Release: $RELEASE_NAME"
    helm status "$RELEASE_NAME" --namespace "$NAMESPACE" 2>/dev/null || warn "Release not found"
    echo ""
    log "Pods:"
    kubectl get pods -n "$NAMESPACE" -l "app.kubernetes.io/instance=$RELEASE_NAME" 2>/dev/null || true
    echo ""
    log "Services:"
    kubectl get svc -n "$NAMESPACE" -l "app.kubernetes.io/instance=$RELEASE_NAME" 2>/dev/null || true
    echo ""
    log "HPA:"
    kubectl get hpa -n "$NAMESPACE" -l "app.kubernetes.io/instance=$RELEASE_NAME" 2>/dev/null || true
}

cmd_logs() {
    log "Tailing logs..."
    kubectl logs -n "$NAMESPACE" -l "app.kubernetes.io/instance=$RELEASE_NAME" --all-containers -f --tail=100
}

case "${1:-}" in
    build)   cmd_build ;;
    push)    cmd_push ;;
    deploy)  cmd_deploy ;;
    upgrade) cmd_upgrade ;;
    teardown) cmd_teardown ;;
    status)  cmd_status ;;
    logs)    cmd_logs ;;
    *)       usage ;;
esac
