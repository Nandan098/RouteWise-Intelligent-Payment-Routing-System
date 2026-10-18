# RouteWise architecture notes

## Request flow

1. `POST /route` receives a `RouteRequest`. Pydantic validates IDs, positive amount, currency and routing policy.
2. `RoutingService.route` serializes a canonical payload and opens a SQLite `BEGIN IMMEDIATE` transaction.
3. If that transaction ID already exists with the same payload, return the prior result. If its payload differs, raise an idempotency conflict (`409`).
4. Weighted routing scores healthy gateways with the native C++ engine if `routewise_cpp` is importable; otherwise the same formula runs in Python. UCB routing ranks gateways using feedback already saved in SQLite.
5. The selected route and explanatory data are inserted atomically into `routes`.
6. `POST /feedback` records a simulated outcome for a previously routed transaction. Future UCB requests can use it.
7. Read APIs query persisted results and aggregates.

## Main modules

- `config.py`: environment settings, gateway data models and JSON configuration validation.
- `schemas.py`: API data contracts and request validation.
- `database.py`: SQL schema, parameterized queries and transaction boundaries.
- `router.py`: weighted routing wrapper and Python fallback.
- `adaptive.py`: UCB1 selection based on observed success outcomes.
- `service.py`: idempotency, policy choice, persistence and feedback flow.
- `api.py`: HTTP routes, response models, status codes and error conversion.
- `cpp/router_engine.cpp`: standalone weighted score computation without HTTP or database dependencies.
- `cpp/bindings.cpp`: conversion between Python dictionaries and C++ structs.

## Key design decisions

### Keep the routing engine separate from HTTP and SQLite

The C++ algorithm accepts metrics and weights and returns a ranking. This makes it easy to test independently and keeps framework details out of performance-sensitive logic.

### Deterministic weighted routing

The same configuration should give the same ranking. That simplifies debugging and makes it easier to reason about policy trade-offs. The score is a relative utility, not a calibrated success probability.

### Feedback-driven UCB

Weighted routing is a baseline based on configured estimates. UCB demonstrates a different idea: the system's historical observations can affect future choices. It requires careful simulation, enough samples, and monitoring because historical feedback is imperfect evidence.

### Idempotency

A unique transaction ID plus a canonical request payload makes retries safe in the simulation. The same request returns the previous route. Reusing the ID for a different payload returns a conflict.

### Limitations

SQLite serializes writes and is not a production-scale distributed store. The project lacks authentication, distributed coordination, a real gateway adapter, and production telemetry. Gateway outcomes are simulated and must not be represented as real-world measurements.
