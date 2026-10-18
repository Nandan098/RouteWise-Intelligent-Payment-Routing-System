"""Concurrent load-test client for a running RouteWise API.

Example: python scripts/load_test.py --requests 500 --concurrency 20
The reported measurements describe your current machine and local configuration.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import math
import statistics
import time
import uuid

import requests


def percentile(values: list[float], quantile: float) -> float:
    ordered = sorted(values)
    if not ordered:
        return 0.0
    position = (len(ordered) - 1) * quantile
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] * (upper - position) + ordered[upper] * (position - lower)


def make_request(base_url: str, index: int) -> tuple[float, bool, str]:
    payload = {
        "transaction_id": f"load-{uuid.uuid4().hex}-{index}",
        "amount": 500.0 + (index % 100) * 37.5,
        "currency": "INR",
        "policy": "weighted",
    }
    started = time.perf_counter()
    try:
        response = requests.post(f"{base_url.rstrip('/')}/route", json=payload, timeout=15)
        elapsed_ms = (time.perf_counter() - started) * 1000
        return elapsed_ms, response.status_code == 200, f"HTTP {response.status_code}"
    except requests.RequestException as exc:
        elapsed_ms = (time.perf_counter() - started) * 1000
        return elapsed_ms, False, type(exc).__name__


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--requests", type=int, default=200)
    parser.add_argument("--concurrency", type=int, default=10)
    args = parser.parse_args()
    if args.requests < 1 or args.concurrency < 1:
        parser.error("requests and concurrency must be positive")
    requests.get(f"{args.base_url.rstrip('/')}/health", timeout=5).raise_for_status()
    results = []
    started = time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.concurrency) as pool:
        futures = [pool.submit(make_request, args.base_url, index) for index in range(args.requests)]
        results = [future.result() for future in concurrent.futures.as_completed(futures)]
    total_seconds = time.perf_counter() - started
    latencies = [item[0] for item in results]
    successes = sum(int(item[1]) for item in results)
    failures = len(results) - successes
    print("RouteWise API load test (measured on this machine; not a service-level guarantee)")
    print(f"Requests: {len(results)} | succeeded: {successes} | failed: {failures}")
    print(f"Throughput: {len(results) / total_seconds:.2f} requests/second")
    print(f"Latency ms: p50={percentile(latencies, .50):.2f}, p95={percentile(latencies, .95):.2f}, p99={percentile(latencies, .99):.2f}")
    if failures:
        print("Sample failures:", [item[2] for item in results if not item[1]][:5])
    if latencies:
        print(f"Mean latency: {statistics.mean(latencies):.2f} ms")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
