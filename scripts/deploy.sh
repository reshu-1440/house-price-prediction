#!/usr/bin/env bash
set -euo pipefail

COMPOSE_FILE="${1:-docker-compose.yml}"

echo "Validating compose configuration (${COMPOSE_FILE})..."
docker compose -f "${COMPOSE_FILE}" config >/dev/null

echo "Starting API and MLflow services..."
docker compose -f "${COMPOSE_FILE}" up -d --build

echo "Waiting for API health check..."
for i in $(seq 1 20); do
  if curl -fsS http://127.0.0.1:8000/health >/dev/null; then
    echo "Service is healthy."
    exit 0
  fi
  sleep 2
done

echo "API health check timed out." >&2
exit 1
