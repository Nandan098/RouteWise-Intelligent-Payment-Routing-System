# Validation notes for this packaged version

The following checks were performed in the build environment while preparing this project archive:

- Python source compilation passed with `python -m compileall -q routewise dashboard scripts tests`.
- Automated suite passed: `python -m pytest -q` reported **18 passed**.
- The standalone C++17 routing engine compiled with `g++ -std=c++17 -Wall -Wextra -Wpedantic` and a smoke-test executable selected `gateway_a` with score `0.886` from the example candidates.
- A live FastAPI smoke test returned a route, accepted feedback, handled a UCB route, and returned stats.
- A local load-test smoke run completed 30/30 requests. The measured values in that environment are not a claim about the user's machine or a production service.

The pybind11 Python package was not installed in the build environment, and the native extension was therefore **not** built here. The C++ engine source itself compiled successfully, but the actual Python-to-C++ extension must be built on a machine with pybind11, CMake and a C++17 compiler. Until `/health` reports `native_cpp_available: true`, the application uses the Python weighted-routing fallback.
