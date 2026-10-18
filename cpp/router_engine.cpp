#include "router_engine.hpp"

#include <algorithm>
#include <cmath>
#include <stdexcept>

namespace routewise {

std::vector<ScoredGateway> rank_gateways(
    const std::vector<GatewayMetrics>& gateways,
    double success_weight,
    double latency_weight,
    double cost_weight,
    double latency_reference_ms,
    double cost_reference_units
) {
    if (success_weight < 0.0 || latency_weight < 0.0 || cost_weight < 0.0) {
        throw std::invalid_argument("Routing weights cannot be negative");
    }
    const double weight_sum = success_weight + latency_weight + cost_weight;
    if (weight_sum <= 0.0) {
        throw std::invalid_argument("At least one routing weight must be positive");
    }
    if (latency_reference_ms <= 0.0 || cost_reference_units <= 0.0) {
        throw std::invalid_argument("Latency and cost reference values must be positive");
    }

    // Normalize weights so they can be edited without accidentally changing score scale.
    success_weight /= weight_sum;
    latency_weight /= weight_sum;
    cost_weight /= weight_sum;

    std::vector<ScoredGateway> ranked;
    ranked.reserve(gateways.size());
    for (const auto& gateway : gateways) {
        if (!gateway.healthy) {
            continue;  // A configured unhealthy gateway is never selected.
        }
        if (gateway.gateway_id.empty() || gateway.name.empty()) {
            throw std::invalid_argument("Gateway ID and name cannot be empty");
        }
        if (gateway.success_rate < 0.0 || gateway.success_rate > 1.0) {
            throw std::invalid_argument("Gateway success rate must be between zero and one");
        }
        if (gateway.latency_ms <= 0.0 || gateway.cost_units < 0.0) {
            throw std::invalid_argument("Gateway latency must be positive and cost cannot be negative");
        }

        const double latency_score = std::max(0.0, 1.0 - gateway.latency_ms / latency_reference_ms);
        const double cost_score = std::max(0.0, 1.0 - gateway.cost_units / cost_reference_units);
        const double score = success_weight * gateway.success_rate
            + latency_weight * latency_score
            + cost_weight * cost_score;
        ranked.push_back(ScoredGateway{gateway, score});
    }

    std::sort(ranked.begin(), ranked.end(), [](const ScoredGateway& left, const ScoredGateway& right) {
        if (std::abs(left.score - right.score) > 1e-12) {
            return left.score > right.score;
        }
        return left.gateway.gateway_id < right.gateway.gateway_id;
    });
    return ranked;
}

}  // namespace routewise
