"""Post-deploy smoke checks for Q-Sentinel Mesh API."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request


def request_json(url: str, method: str = "GET") -> tuple[int, str]:
    req = urllib.request.Request(url=url, method=method)
    try:
        with urllib.request.urlopen(req, timeout=20) as res:
            return res.status, res.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        return exc.code, body


def main() -> int:
    parser = argparse.ArgumentParser(description="Run post-deploy smoke checks")
    parser.add_argument("--base-url", default="http://localhost:8000", help="Backend base URL")
    args = parser.parse_args()

    base = args.base_url.rstrip("/")
    checks = [
        ("health", "GET", f"{base}/api/health", {200}),
        ("readiness", "GET", f"{base}/api/health/ready", {200}),
        ("metrics", "GET", f"{base}/api/metrics/benchmark", {200}),
        ("federated", "GET", f"{base}/api/federated/rounds", {200}),
        ("demo-list", "GET", f"{base}/api/ct/demo", {200}),
        ("pqc-demo", "POST", f"{base}/api/pqc/demo", {200}),
    ]

    failed = []
    print("=" * 72)
    print("Q-Sentinel Mesh Post-Deploy Smoke")
    print("=" * 72)

    for name, method, url, expected in checks:
        status, body = request_json(url, method=method)
        ok = status in expected
        print(f"[{ 'OK' if ok else 'FAIL' }] {name:10s} {status:3d} {url}")

        if name == "readiness":
            try:
                parsed = json.loads(body)
                print(f"      ready={parsed.get('ready')} baseline={parsed.get('baseline_loaded')} hybrid={parsed.get('hybrid_loaded')}")
                if not parsed.get("ready", False):
                    failed.append(f"readiness endpoint returned ready=false: {parsed.get('issues')}")
            except Exception:
                failed.append("readiness endpoint did not return valid JSON")

        if not ok:
            failed.append(f"{name} returned HTTP {status}")

    print()
    if failed:
        print("Smoke FAILED:")
        for item in failed:
            print(f" - {item}")
        return 1

    print("Smoke PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
