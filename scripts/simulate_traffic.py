"""Send simulated route requests and feedback to a running RouteWise API.

Example: python scripts/simulate_traffic.py --count 100 --policy ucb
This does not execute or move real money; transaction outcomes are simulated.
"""
from __future__ import annotations

import argparse
import random
import time
import uuid
from collections import Counter

import requests

# Simulated outcome probabilities deliberately differ from configured baseline metrics.
TRUE_SUCCESS_PROBABILITY = {
    "gateway_a": 0.972,
    "gateway_b": 0.943,
    "gateway_c": 0.986,
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--count", type=int, default=100)
    parser.add_argument("--policy", choices=["weighted", "ucb"], default="ucb")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--pause-ms", type=float, default=0.0)
    args = parser.parse_args()
    if args.count < 1 or args.pause_ms < 0:
        parser.error("count must be positive and pause-ms cannot be negative")

    rng = random.Random(args.seed)
    counts: Counter[str] = Counter()
    successes: Counter[str] = Counter()
    latencies: dict[str, list[float]] = {}
    for index in range(args.count):
        transaction_id = f"sim-{uuid.uuid4().hex[:12]}-{index}"
        request_payload = {
            "transaction_id": transaction_id,
            "amount": round(rng.uniform(100, 25000), 2),
            "currency": "INR",
            "policy": args.policy,
        }
        response = requests.post(f"{args.base_url.rstrip('/')}/route", json=request_payload, timeout=10)
        response.raise_for_status()
        route = response.json()
        gateway_id = route["gateway_id"]
        probability = TRUE_SUCCESS_PROBABILITY.get(gateway_id, 0.95)
        succeeded = rng.random() < probability
        baseline_latency = float(route["expected_latency_ms"])
        observed_latency = max(1.0, rng.gauss(baseline_latency, max(5.0, baseline_latency * 0.12)))
        feedback = {
            "transaction_id": transaction_id,
            "success": succeeded,
            "actual_latency_ms": round(observed_latency, 2),
        }
        feedback_response = requests.post(f"{args.base_url.rstrip('/')}/feedback", json=feedback, timeout=10)
        feedback_response.raise_for_status()
        counts[gateway_id] += 1
        successes[gateway_id] += int(succeeded)
        latencies.setdefault(gateway_id, []).append(observed_latency)
        if args.pause_ms:
            time.sleep(args.pause_ms / 1000.0)

    print(f"Completed {args.count} simulated routes using policy={args.policy!r}.")
    print("No real payment was attempted.")
    for gateway_id, count in sorted(counts.items()):
        print(
            f"{gateway_id}: routes={count}, simulated_success_rate={successes[gateway_id] / count:.3%}, "
            f"avg_observed_latency_ms={sum(latencies[gateway_id]) / count:.1f}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
