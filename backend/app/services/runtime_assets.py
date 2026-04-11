"""Ensure runtime assets such as model weights and demo CT cases exist locally."""
from __future__ import annotations

from pathlib import Path

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from app.core.config import settings


REPO_ROOT = Path(__file__).parent.parent.parent.parent
WEIGHTS_DIR = REPO_ROOT / "weights"
DEMO_SAMPLES_DIR = REPO_ROOT / "data" / "samples"


class RuntimeAssetsService:
    def __init__(self) -> None:
        self._s3 = None
        self._last_status = {
            "attempted": False,
            "enabled": False,
            "bucket": settings.S3_BUCKET,
            "synced_prefixes": [],
            "errors": [],
        }

    def ensure_runtime_assets(self) -> None:
        """Best-effort sync from S3 for ECS-style deployments."""
        WEIGHTS_DIR.mkdir(parents=True, exist_ok=True)
        DEMO_SAMPLES_DIR.mkdir(parents=True, exist_ok=True)

        self._last_status = {
            "attempted": True,
            "enabled": settings.USE_S3,
            "bucket": settings.S3_BUCKET,
            "synced_prefixes": [],
            "errors": [],
        }

        if not settings.USE_S3:
            print("[RuntimeAssets] USE_S3 is disabled; skipping remote sync")
            return

        if not settings.S3_BUCKET:
            print("[RuntimeAssets] S3_BUCKET is empty; skipping remote sync")
            return

        self._sync_prefix(settings.WEIGHTS_S3_PREFIX, WEIGHTS_DIR)
        self._sync_prefix(settings.DEMO_SAMPLES_S3_PREFIX, DEMO_SAMPLES_DIR)

    def get_status(self) -> dict:
        return {
            **self._last_status,
            "weights_dir": str(WEIGHTS_DIR),
            "demo_samples_dir": str(DEMO_SAMPLES_DIR),
        }

    def _client(self):
        if self._s3 is None:
            self._s3 = boto3.client("s3", region_name=settings.AWS_REGION)
        return self._s3

    def _sync_prefix(self, prefix: str, target_dir: Path) -> None:
        normalized_prefix = prefix.strip("/")
        if not normalized_prefix:
            return

        bucket = settings.S3_BUCKET
        print(f"[RuntimeAssets] Syncing s3://{bucket}/{normalized_prefix}/ -> {target_dir}")

        try:
            paginator = self._client().get_paginator("list_objects_v2")
            page_iterator = paginator.paginate(Bucket=bucket, Prefix=f"{normalized_prefix}/")
            downloaded = 0

            for page in page_iterator:
                for obj in page.get("Contents", []):
                    key = obj["Key"]
                    if key.endswith("/"):
                        continue

                    relative_key = key[len(normalized_prefix) + 1 :]
                    destination = target_dir / relative_key
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    self._client().download_file(bucket, key, str(destination))
                    downloaded += 1

            print(f"[RuntimeAssets] Synced {downloaded} file(s) from {normalized_prefix}/")
            self._last_status["synced_prefixes"].append(
                {"prefix": f"{normalized_prefix}/", "downloaded": downloaded}
            )
        except (BotoCoreError, ClientError) as exc:
            print(f"[RuntimeAssets] Failed to sync {normalized_prefix}/: {exc}")
            self._last_status["errors"].append(
                {"prefix": f"{normalized_prefix}/", "detail": str(exc)}
            )


runtime_assets_service = RuntimeAssetsService()
