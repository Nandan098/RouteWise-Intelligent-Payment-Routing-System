# Resume bullets — only after you verify each claim

**RouteWise: Intelligent Payment Routing System**  
* C++, Python, FastAPI, SQLite, pybind11, Streamlit

- Engineered a C++17 weighted routing engine to rank simulated payment gateways using configurable success-rate, latency, and cost signals, with a Python fallback for portability.
- Implemented a FastAPI routing service with SQLite persistence, request validation, idempotent transaction IDs, and separate feedback recording for simulated gateway outcomes.
- Added a UCB1 adaptive routing policy, synthetic traffic simulator, and policy-comparison experiment to study exploration versus success-rate optimization.
- Built a Streamlit dashboard and concurrent HTTP load-test script to inspect route decisions and measure throughput and p50/p95/p99 latency under a documented workload.

Only retain the C++/pybind11 claim after successfully building the extension. Add performance numbers only after you run the benchmark and can explain its machine, workload, concurrency, and limitations.
