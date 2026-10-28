#!/usr/bin/env bash
# Builds the React app and copies it to backend/static, where FastAPI serves it.
set -euo pipefail
cd "$(dirname "$0")/.."
(cd frontend && npm ci --no-audit --no-fund && npm run build)
rm -rf backend/static
cp -r frontend/dist backend/static
echo "Frontend built -> backend/static"
