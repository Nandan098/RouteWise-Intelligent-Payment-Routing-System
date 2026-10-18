#pragma once

#include <string>
#include <vector>

namespace routewise {

struct GatewayMetrics {
    std::string gateway_id;
    std::string name;
    double success_rate;
    double latency_ms;
    double cost_units;
    bool healthy;
};

struct ScoredGateway {
    GatewayMetrics gateway;
    double score;
};

std::vector<ScoredGateway> rank_gateways(
    const std::vector<GatewayMetrics>& gateways,
    double success_weight,
    double latency_weight,
    double cost_weight,
    double latency_reference_ms,
    double cost_reference_units
);

}  // namespace routewise
