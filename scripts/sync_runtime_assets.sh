#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/q-sentinel-mesh}"
ASSET_BUCKET="${ASSET_BUCKET:-}"

mkdir -p "${APP_DIR}/weights" "${APP_DIR}/data/samples"

if [[ -z "${ASSET_BUCKET}" ]]; then
  echo "[sync-runtime-assets] ASSET_BUCKET not set; skipping S3 sync"
  exit 0
fi

echo "[sync-runtime-assets] Syncing runtime assets from s3://${ASSET_BUCKET}"
aws s3 sync "s3://${ASSET_BUCKET}/weights/" "${APP_DIR}/weights/" --no-progress || true
aws s3 sync "s3://${ASSET_BUCKET}/data/samples/" "${APP_DIR}/data/samples/" --no-progress || true

echo "[sync-runtime-assets] Done"
