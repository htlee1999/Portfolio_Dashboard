#!/usr/bin/env bash
# Start the FastAPI backend and the Next.js frontend together.
# Ports default to 8000 (API) and 3000 (web); override with API_PORT / WEB_PORT.
set -euo pipefail
cd "$(dirname "$0")"

API_PORT="${API_PORT:-8000}"
WEB_PORT="${WEB_PORT:-3000}"

[ -d web/node_modules ] || (cd web && npm install)

python3 -m uvicorn backend.main:app --port "$API_PORT" --reload --reload-dir backend &
API_PID=$!
trap 'kill $API_PID 2>/dev/null' EXIT

# Pass the port explicitly: Next.js would otherwise honor a PORT variable from the shell.
cd web && API_URL="http://127.0.0.1:$API_PORT" npx next dev --port "$WEB_PORT"
