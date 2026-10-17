#!/usr/bin/env bash
set -euo pipefail
repo_dir=$(git -C "$(dirname "$0")" rev-parse --show-toplevel)
evidence_dir="$repo_dir/docs/evidence/sprint-01/S1-OPTIMIZATION-FIRST-FIT/integration"
export NEWGLASS_REQUIRE_POSTGRES=1
# Synthetic accounts created by tests.e2e_server in its owned loopback cluster.
export HU015_E2E_USERNAME=O70000001 HU015_E2E_PASSWORD='Orders-test-2026!'
export TA_DASHBOARD_E2E_ADMIN_USERNAME=A70000003 TA_DASHBOARD_E2E_ADMIN_PASSWORD='Admin-test-2026!'
export TA_DASHBOARD_E2E_OPERATOR_USERNAME=O70000001 TA_DASHBOARD_E2E_OPERATOR_PASSWORD='Orders-test-2026!'
export TA_DASHBOARD_E2E_WAREHOUSE_USERNAME=A70000002 TA_DASHBOARD_E2E_WAREHOUSE_PASSWORD='Inventory-test-2026!'
export NEWGLASS_E2E_API_ORIGIN=http://127.0.0.1:8017
export NEWGLASS_E2E_EVIDENCE_DIR="$evidence_dir/dashboard"
cd "$repo_dir/frontend"
exec npx playwright test --config="$evidence_dir/playwright.config.mjs" "$@"
