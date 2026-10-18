# Start here — RouteWise

Welcome! RouteWise is an educational simulation of intelligent payment gateway routing. It does not connect to real payment processors or move money.

## First run

1. Install Python 3.11 or newer (Python 3.10+ is supported), then open this folder in VS Code.
2. Open a terminal at the folder containing this file.
3. Create and activate a virtual environment:
   - Windows PowerShell: `py -3.11 -m venv .venv` then `\.venv\Scripts\Activate.ps1`
   - Linux/macOS: `python3 -m venv .venv` then `source .venv/bin/activate`
4. Install dependencies: `python -m pip install --upgrade pip` then `pip install -r requirements.txt`.
5. Run tests: `python -m pytest -q`.
6. Start the API: `uvicorn routewise.main:app --reload`.
7. Open `http://127.0.0.1:8000/docs` and try `GET /health`, `GET /gateways`, and `POST /route`.

## Build the native C++ extension later

The API can use a Python fallback while you learn. To use C++, install a C++17 compiler and CMake, then follow the “Build the C++17 / pybind11 extension” section in `README.md`. Do not claim native C++ integration is active until `/health` reports `native_cpp_available: true`.

## Suggested learning order

1. `routewise/schemas.py` — request and response structure.
2. `routewise/config.py` — gateway configuration.
3. `routewise/router.py` — weighted ranking and native wrapper.
4. `routewise/adaptive.py` — UCB1 exploration and feedback.
5. `routewise/database.py` — SQL and transactions.
6. `routewise/service.py` — complete route/feedback workflow.
7. `routewise/api.py` — HTTP endpoints and status codes.
8. `cpp/router_engine.cpp` and `cpp/bindings.cpp` — the compiled engine and Python bridge.

Read `docs/LEARNING_GUIDE.md` while following the code. Then read `docs/INTERVIEW_GUIDE.md` and answer questions in your own words.
