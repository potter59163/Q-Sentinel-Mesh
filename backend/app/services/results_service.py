"""Load benchmark/fed/threshold JSONs from local filesystem or S3."""
import json
import os
from pathlib import Path
from app.core.config import settings


class ResultsService:
    def __init__(self):
        # Resolve results dir relative to repo root
        # backend/ is inside q-sentinel-mesh/, so parent.parent = repo root
        self._base = Path(__file__).parent.parent.parent.parent / settings.LOCAL_RESULTS_DIR

    def _load(self, filename: str) -> dict | list:
        path = self._base / filename
        if not path.exists():
            return {}
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    def get_benchmark(self) -> dict:
        return self._load("benchmark_results.json")

    def get_fed_rounds(self) -> list:
        data = self._load("fed_results.json")
        return data if isinstance(data, list) else []

    def get_thresholds(self) -> dict:
        return self._load("optimal_thresholds.json")


results_service = ResultsService()
