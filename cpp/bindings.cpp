#include "router_engine.hpp"

#include <cmath>

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

namespace py = pybind11;

PYBIND11_MODULE(routewise_cpp, module) {
    module.doc() = "Native C++ weighted payment gateway routing engine";
    module.def(
        "rank_gateways",
        [](const py::list& rows,
           double success_weight,
           double latency_weight,
           double cost_weight,
           double latency_reference_ms,
           double cost_reference_units) {
            std::vector<routewise::GatewayMetrics> gateways;
            gateways.reserve(rows.size());
            for (const auto item : rows) {
                const auto row = py::cast<py::dict>(item);
                gateways.push_back(routewise::GatewayMetrics{
                    py::cast<std::string>(row["gateway_id"]),
                    py::cast<std::string>(row["name"]),
                    py::cast<double>(row["success_rate"]),
                    py::cast<double>(row["latency_ms"]),
                    py::cast<double>(row["cost_units"]),
                    py::cast<bool>(row["healthy"]),
                });
            }
            const auto ranked = routewise::rank_gateways(
                gateways,
                success_weight,
                latency_weight,
                cost_weight,
                latency_reference_ms,
                cost_reference_units
            );
            py::list result;
            for (const auto& item : ranked) {
                py::dict output;
                output["gateway_id"] = item.gateway.gateway_id;
                output["name"] = item.gateway.name;
                output["score"] = std::round(item.score * 1'000'000.0) / 1'000'000.0;
                output["success_rate"] = item.gateway.success_rate;
                output["latency_ms"] = item.gateway.latency_ms;
                output["cost_units"] = item.gateway.cost_units;
                result.append(output);
            }
            return result;
        },
        py::arg("gateways"),
        py::arg("success_weight"),
        py::arg("latency_weight"),
        py::arg("cost_weight"),
        py::arg("latency_reference_ms"),
        py::arg("cost_reference_units")
    );
}
