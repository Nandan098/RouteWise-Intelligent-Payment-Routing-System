from __future__ import annotations


def payload(transaction_id="txn-001", amount=1850.0, policy="weighted"):
    return {
        "transaction_id": transaction_id,
        "amount": amount,
        "currency": "INR",
        "policy": policy,
    }


def test_health_and_gateway_list(client):
    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"
    gateways = client.get("/gateways")
    assert gateways.status_code == 200
    assert len(gateways.json()) == 3
    assert "native_cpp_available" in health.json()


def test_weighted_route_returns_explanation_and_persists(client):
    response = client.post("/route", json=payload())
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["gateway_id"] == "gateway_a"
    assert data["policy"] == "weighted"
    assert 0 <= data["routing_score"] <= 1
    assert data["reasons"]
    stored = client.get("/transactions/txn-001")
    assert stored.status_code == 200
    assert stored.json()["gateway_id"] == data["gateway_id"]


def test_same_route_request_is_idempotent(client):
    first = client.post("/route", json=payload()).json()
    second_response = client.post("/route", json=payload())
    assert second_response.status_code == 200
    second = second_response.json()
    assert second["gateway_id"] == first["gateway_id"]
    assert second["idempotent_replay"] is True
    assert client.get("/stats").json()["total_routes"] == 1


def test_reusing_transaction_id_with_different_payload_conflicts(client):
    assert client.post("/route", json=payload()).status_code == 200
    response = client.post("/route", json=payload(amount=999.0))
    assert response.status_code == 409


def test_validation_rejects_invalid_amount_and_unknown_field(client):
    bad_amount = client.post("/route", json=payload(amount=0))
    assert bad_amount.status_code == 422
    unknown = payload()
    unknown["client_supplied_gateway_score"] = 0.99
    assert client.post("/route", json=unknown).status_code == 422


def test_ucb_routing_and_feedback_learning(client):
    first = client.post("/route", json=payload("ucb-001", policy="ucb"))
    assert first.status_code == 200
    gateway_id = first.json()["gateway_id"]
    feedback = client.post("/feedback", json={
        "transaction_id": "ucb-001", "success": True, "actual_latency_ms": 142.5
    })
    assert feedback.status_code == 200
    assert feedback.json()["gateway_id"] == gateway_id
    replay = client.post("/feedback", json={
        "transaction_id": "ucb-001", "success": True, "actual_latency_ms": 142.5
    })
    assert replay.status_code == 200
    assert replay.json()["idempotent_replay"] is True
    stats = client.get("/stats").json()
    assert stats["total_feedback"] == 1
    assert stats["observed_success_rate"] == 1.0


def test_feedback_requires_existing_route_and_conflicting_feedback_is_rejected(client):
    missing = client.post("/feedback", json={
        "transaction_id": "missing", "success": False, "actual_latency_ms": 100
    })
    assert missing.status_code == 404
    client.post("/route", json=payload())
    client.post("/feedback", json={
        "transaction_id": "txn-001", "success": True, "actual_latency_ms": 100
    })
    conflict = client.post("/feedback", json={
        "transaction_id": "txn-001", "success": False, "actual_latency_ms": 100
    })
    assert conflict.status_code == 409


def test_recent_routes_and_stats(client):
    client.post("/route", json=payload("recent-1"))
    client.post("/route", json=payload("recent-2", policy="ucb"))
    assert len(client.get("/routes?limit=10").json()) == 2
    assert client.get("/stats").json()["total_routes"] == 2
