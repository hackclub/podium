#!/usr/bin/env bash
# Run E2E tests locally via act, injecting a short-lived Doppler service token.
# The token expires in 1 hour and is never written to disk.
set -euo pipefail

echo "Generating temporary Doppler service token..."
TOKEN=$(doppler configs tokens create "act-$(date +%s)" \
  --project podium --config dev \
  --max-age 1h \
  --plain)

echo "Running act..."
act -W .github/workflows/e2e-tests.yaml \
  --secret "DOPPLER_TOKEN=$TOKEN" \
  "$@"
