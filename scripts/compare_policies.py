"""Compare static weighted selection, round-robin, and UCB1 in a synthetic simulation."""
from __future__ import annotations

import argparse
import csv
import math
import random
from pathlib import Path

GATEWAYS = {
    "gateway_a": {"success_probability": 0.972, "latency_ms": 150.0, "cost_units": 0.020},
    "gateway_b": {"success_probability": 0.943, "latency_ms": 100.0, "cost_units": 0.025},
    "gateway_c": {"success_probability": 0.986, "latency_ms": 300.0, "cost_units": 0.035},
}


def simulate(policy: str, count: int, seed: int) -> dict[str, float | int | str]:
    rng = random.Random(seed)
    ids = list(GATEWAYS)
    trials = {gateway_id: 0 for gateway_id in ids}
    wins = {gateway_id: 0 for gateway_id in ids}
    total_latency = 0.0
    total_cost = 0.0
    successes = 0
    for index in range(count):
        if policy == "weighted":
            # This is the fixed weighted policy's choice for this demonstration configuration.
            gateway_id = "gateway_a"
        elif policy == "round_robin":
            gateway_id = ids[index % len(ids)]
        elif policy == "ucb1":
            unseen = [item for item in ids if trials[item] == 0]
            if unseen:
                gateway_id = unseen[0]
            else:
                gateway_id = max(
                    ids,
                    key=lambda item: wins[item] / trials[item]
                    + math.sqrt(2 * math.log(max(index, 1)) / trials[item]),
                )
        else:
            raise ValueError(f"Unknown policy: {policy}")
        metrics = GATEWAYS[gateway_id]
        success = rng.random() < metrics["success_probability"]
        trials[gateway_id] += 1
        wins[gateway_id] += int(success)
        successes += int(success)
        total_latency += max(1.0, rng.gauss(metrics["latency_ms"], metrics["latency_ms"] * 0.12))
        total_cost += metrics["cost_units"]
    return {
        "policy": policy,
        "transactions": count,
        "successes": successes,
        "success_rate": successes / count,
        "average_latency_ms": total_latency / count,
        "average_cost_units": total_cost / count,
        **{f"routes_{key}": value for key, value in trials.items()},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--count", type=int, default=5000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", default="benchmarks/policy_comparison.csv")
    args = parser.parse_args()
    if args.count < 3:
        parser.error("count must be at least 3")
    rows = [simulate(policy, args.count, args.seed) for policy in ("weighted", "round_robin", "ucb1")]
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print("Synthetic policy comparison (not production measurements):")
    for row in rows:
        print(
            f"{row['policy']:>12}: success={row['success_rate']:.3%}, "
            f"avg_latency={row['average_latency_ms']:.1f} ms, "
            f"avg_cost={row['average_cost_units']:.4f}"
        )
    print(f"Wrote results to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
