# RouteWise beginner learning guide

Follow these steps after the API starts successfully. The goal is to understand what the code does, not only run commands.

## 1. Start with the schemas

Open `routewise/schemas.py`.

- `RouteRequest` defines what a client may send.
- `Field(gt=0, ...)` rejects invalid values such as a zero amount.
- `ConfigDict(extra="forbid")` rejects unrecognized fields, rather than silently accepting client-supplied routing internals.
- `canonical_payload()` gives the idempotency check a stable representation.
- `RoutingPolicy` limits policy to `weighted` or `ucb`.

## 2. Understand the weighted score

Open `routewise/router.py`, then `cpp/router_engine.cpp`.

- A healthy gateway is eligible; an unhealthy one is filtered out.
- Success rate is already between 0 and 1.
- Latency and cost are converted to bounded scores where lower values are better.
- Weights are normalized so a change in their sum does not change the score's scale.
- The candidates are sorted by descending score. Gateway ID breaks ties consistently.

Try changing one weight in `config/gateways.json`, restart the server, and compare `GET /gateways` with new `POST /route` decisions. Keep an untouched copy of the original configuration so you can revert.

## 3. Understand UCB1

Open `routewise/adaptive.py`.

- `sample_count` is the number of outcomes recorded for a gateway.
- `success_rate` is successful feedback divided by total feedback for that gateway.
- The exploration bonus is larger for less-observed gateways.
- An untried gateway is selected for exploration before a repeatedly sampled gateway.

A route request alone does not teach UCB whether the gateway succeeded. You must submit an outcome to `POST /feedback` for the system to record a reward.

## 4. Understand persistence and idempotency

Open `routewise/database.py`, then `routewise/service.py`.

A SQLite transaction groups the duplicate check and insert so concurrent requests cannot both insert the same transaction ID. An identical retry returns the stored response. A different payload using the same ID is rejected.

The database stores a route decision and its simulated outcome separately. This matters because the selected gateway is not the same as the eventual simulated outcome.

## 5. Trace the API

Open `routewise/api.py`.

FastAPI validates the request against a Pydantic schema before calling the endpoint function. The endpoint delegates business logic to `RoutingService`, then maps known errors to HTTP status codes.

Try these in `/docs`:

1. `GET /health`
2. `GET /gateways`
3. `POST /route` using `weighted`
4. Repeat the exact request with the same ID
5. Reuse the ID with a different amount
6. Submit `POST /feedback`
7. Route another transaction using `ucb`
8. Read `GET /stats`

## 6. Understand the C++ binding

`cpp/router_engine.hpp` declares gateway data structures and the ranking function. `router_engine.cpp` implements the algorithm. `bindings.cpp` converts Python dictionaries into C++ structs and converts results back to a Python list of dictionaries.

The extension is optional for initial learning. After compiling, `GET /health` should report `native_cpp_available: true`. If it reports false, the project continues using the Python fallback and the native integration has not yet been verified.

## 7. Understand tests and measurements

- `tests/test_router.py` checks weighted ranking and validation.
- `tests/test_adaptive.py` checks exploration and UCB scoring.
- `tests/test_api.py` tests HTTP behavior, idempotency, feedback, and stats.
- `scripts/compare_policies.py` uses a fixed random seed for reproducible synthetic comparisons.
- `scripts/load_test.py` measures your running API; results depend on your machine and environment.

Never put a benchmark number on your resume unless you personally ran the test and can describe its setup.
