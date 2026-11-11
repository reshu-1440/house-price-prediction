#!/usr/bin/env bash
set -euo pipefail

IMAGE_NAME="${1:-house-price-api}"
IMAGE_TAG="${2:-latest}"
TARGET_STAGE="${3:-runtime}"

echo "Building ${IMAGE_NAME}:${IMAGE_TAG} (target=${TARGET_STAGE})..."
docker build --target "${TARGET_STAGE}" -t "${IMAGE_NAME}:${IMAGE_TAG}" .
echo "Build complete: ${IMAGE_NAME}:${IMAGE_TAG}"
