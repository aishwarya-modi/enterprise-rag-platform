# Project Structure

This repository is organized into enterprise-grade areas that separate concerns, support deployment, and make the system easier to operate at scale.

## Top-level directories

- backend/: Contains the API server, business services, persistence layers, and backend-specific tests.
- frontend/: Hosts the user-facing application and its presentation layer.
- helm/: Holds Helm charts for packaging and deploying the application to Kubernetes.
- infra/: Contains infrastructure-as-code and environment provisioning assets.
- docker/: Stores container build assets, local container definitions, and compose-oriented tooling.
- k8s/: Keeps Kubernetes manifests and deployment overlays.
- tests/: Centralizes automated testing across unit, integration, end-to-end, and performance layers.
- docs/: Contains architecture decisions, developer guides, and operational documentation.
- scripts/: Stores automation helpers for setup, deployment, and maintenance tasks.
- .github/: Carries repository automation, contribution workflow, and CI/CD governance files.

## Why this structure exists

This layout supports clear ownership, repeatable deployments, safer releases, and easier onboarding for new contributors.
