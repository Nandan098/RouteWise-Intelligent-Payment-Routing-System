# RouteWise interview guide

## 30-second explanation

RouteWise is a simulated payment-routing system built with C++ and Python. It selects among configured payment gateways based on success rate, latency and cost, records the decision in SQLite, and exposes the workflow through FastAPI. It supports a deterministic weighted policy and a UCB1 adaptive policy that learns from simulated outcome feedback. The C++ ranking engine is exposed to Python through pybind11, with a Python fallback for environments where the extension has not been built.

## Two-minute explanation

A route request reaches FastAPI and is validated through Pydantic. The routing service checks whether the transaction ID has already been used. An identical retry returns the saved decision; a changed payload using the same ID is rejected. For weighted routing, each healthy gateway receives a normalized score combining expected success, latency and cost. The ranking can run in the C++17 extension or equivalent Python fallback. For UCB routing, the service reads previous feedback and chooses an untried gateway first; after each gateway has been sampled, it ranks them using empirical success rate plus an exploration bonus. The selected route is saved in SQLite, and a separate feedback endpoint records the simulated result. The dashboard and statistics endpoints display those decisions. This is an educational simulation rather than a real payment processor.

## Common questions and sample answers

### 1. Why did you build RouteWise?
To explore payment orchestration and the trade-off between choosing a gateway from known metrics and adapting based on observed outcomes. It connects algorithm design to a real systems problem without attempting real transactions.

### 2. Why use C++?
The weighted scoring function is isolated and simple to implement in C++17. It demonstrates native code integration and provides a place to benchmark a compiled engine. I would not claim it is faster without a fair measured comparison.

### 3. Why use Python too?
Python is productive for API development, SQLite orchestration, simulation scripts, tests and dashboards. pybind11 provides a Python interface to the C++ ranking function.

### 4. How does weighted routing work?
Each healthy gateway gets `w_success * success_rate + w_latency * latency_score + w_cost * cost_score`. The latency and cost signals are normalized so lower latency and cost receive higher scores. The highest score wins.

### 5. Is the weighted score a probability of success?
No. It is a policy utility score. Even though one input is a success-rate estimate, adding normalized latency and cost scores means the final utility is not a calibrated probability.

### 6. Why normalize the weights?
Weights can be written with different totals by configuration. Dividing each weight by the sum keeps their relative influence while making the combined weights sum to one.

### 7. What is the limitation of weighted routing?
Its choice depends on configured estimates and weights. If they are stale or do not represent current transaction conditions, it can consistently choose a poor route.

### 8. What is UCB1?
Upper Confidence Bound is a multi-armed bandit policy. It combines observed reward with an exploration bonus, so an option with fewer observations can be selected to learn more about its performance.

### 9. What reward does RouteWise use for UCB?
A simulated successful route gives reward 1 and a failure gives reward 0. The current implementation maximizes observed success rate with exploration; it does not directly optimize latency and cost in UCB mode.

### 10. Why try unobserved gateways first?
There is no empirical reward estimate for an untried gateway. Exploring it allows the policy to gather evidence rather than permanently ignoring it due to a missing observation.

### 11. Why is feedback a separate endpoint?
The routing decision occurs before a simulated outcome is known. Separating route selection and outcome recording makes that lifecycle explicit and allows later adaptive decisions to use feedback.

### 12. What if gateway metrics change over time?
Static configured metrics can become stale, and ordinary UCB can react slowly to non-stationary behavior. A production design could use rolling windows, time-decayed rewards, circuit breakers and fresh health telemetry.

### 13. How does idempotency work?
The service stores a canonical request payload under a unique transaction ID. An identical repeated request returns the existing result. The same ID with different content returns HTTP 409.

### 14. Why store request JSON?
It lets the service distinguish a retry from an accidental or malicious reuse of the transaction identifier with changed fields.

### 15. What does SQLite transaction handling protect?
The service performs the idempotency check and route insert in a write transaction, reducing the chance that concurrent requests both create the same transaction. `BEGIN IMMEDIATE` also serializes competing write operations.

### 16. Would SQLite work at production scale?
Not for the high write volume and multi-instance requirements of a payment platform. It is a simple local database for this demo. Production could require a shared transactional database, explicit concurrency strategy, partitioning, and durable event processing.

### 17. What happens if the C++ extension is unavailable?
The router wrapper uses the Python weighted-ranking implementation with the same formula. `/health` reports whether the compiled extension is active so the implementation path is visible.

### 18. How would you prove the C++ version is faster?
Benchmark both implementations on identical candidate sets, repeat trials, warm them up, report distributions, check that results match, and account for Python-to-C++ conversion overhead. I would not infer speed from language choice alone.

### 19. What does p95 latency mean?
It is the latency value at or below which 95% of measured requests completed. p99 does the same for 99% and highlights the tail. Measurements must specify workload, concurrency, machine and whether startup is included.

### 20. How does the load test work?
It creates requests with unique IDs, sends them concurrently to the local API, records request durations and status codes, and reports throughput and latency percentiles. The reported numbers depend on the environment.

### 21. How do you test reliability?
Automated tests check validation, no-feedback exploration, feedback recording, retries, conflicts, route retrieval and aggregate statistics. More extensive work could inject timeouts and unavailable gateways in the simulator.

### 22. Is the gateway cost real money?
No. It is a fictional relative cost unit for comparing policies. I would never describe it as an actual merchant fee.

### 23. Is this connected to a real payment provider?
No. It selects among simulated gateways and records simulated feedback. It does not process or authorize payments.

### 24. What are the security gaps?
The demo lacks authentication, authorization, rate limiting and production secrets management. It is intended to bind to localhost during local development and should not be exposed publicly as-is.

### 25. What would you improve next?
Add better failure simulation and circuit breaker state, rolling feedback windows, confidence-interval comparisons, observability, authentication, and a PostgreSQL-backed multi-process design. I would compare the results against a baseline before claiming an improvement.

## Resume claims checklist

Only claim these items after verifying them yourself:

- [ ] C++17 extension builds and `native_cpp_available()` returns true.
- [ ] Weighted route decisions are executed and persisted.
- [ ] UCB routing changes based on recorded outcomes.
- [ ] Identical route retries return the previous route.
- [ ] Reusing a transaction ID with different input is rejected.
- [ ] API tests pass locally.
- [ ] Dashboard talks to the live API.
- [ ] Synthetic comparison and load tests have been run.
- [ ] Any performance figures quote your actual workload and measurements.
