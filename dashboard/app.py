"""Minimal Python dashboard for the RouteWise HTTP API."""
from __future__ import annotations

import os

import pandas as pd
import requests
import streamlit as st

BASE_URL = os.getenv("ROUTEWISE_API_URL", "http://127.0.0.1:8000").rstrip("/")

st.set_page_config(page_title="RouteWise", page_icon="↗", layout="wide")
st.title("RouteWise — Intelligent Payment Routing")
st.caption("Educational simulation only. This dashboard does not send or process real payments.")

try:
    health = requests.get(f"{BASE_URL}/health", timeout=3)
    health.raise_for_status()
    status = health.json()
    st.success(f"API connected · native C++ extension: {'available' if status['native_cpp_available'] else 'Python fallback'}")
except requests.RequestException:
    st.error(f"Cannot connect to {BASE_URL}. Start the API before using the dashboard.")
    st.stop()

left, right = st.columns([1, 1])
with left:
    st.subheader("Route a simulated transaction")
    with st.form("route_form"):
        transaction_id = st.text_input("Transaction ID", value="demo-txn-001")
        amount = st.number_input("Amount", min_value=0.01, max_value=1_000_000_000.0, value=1850.0, step=50.0)
        currency = st.selectbox("Currency", ["INR", "USD", "EUR"])
        policy = st.selectbox("Routing policy", ["weighted", "ucb"], help="UCB learns from feedback recorded below.")
        route_submitted = st.form_submit_button("Select gateway", type="primary")
    if route_submitted:
        payload = {"transaction_id": transaction_id, "amount": amount, "currency": currency, "policy": policy}
        try:
            response = requests.post(f"{BASE_URL}/route", json=payload, timeout=10)
            if response.ok:
                st.session_state["last_route"] = response.json()
            else:
                st.error(f"Route request failed ({response.status_code}): {response.text}")
        except requests.RequestException as exc:
            st.error(f"API request failed: {exc}")

with right:
    st.subheader("Latest route")
    route_result = st.session_state.get("last_route")
    if route_result:
        st.metric("Selected gateway", route_result["gateway_name"])
        a, b, c = st.columns(3)
        a.metric("Expected success", f"{route_result['expected_success_rate']:.1%}")
        b.metric("Expected latency", f"{route_result['expected_latency_ms']:.0f} ms")
        c.metric("Cost units", f"{route_result['estimated_cost_units']:.4f}")
        st.write("**Why this gateway?**")
        for reason in route_result["reasons"]:
            st.write(f"- {reason}")

st.divider()
st.subheader("Record a simulated outcome")
route_for_feedback = st.session_state.get("last_route")
with st.form("feedback_form"):
    feedback_transaction_id = st.text_input(
        "Transaction ID for feedback",
        value=route_for_feedback["transaction_id"] if route_for_feedback else "",
    )
    outcome = st.selectbox("Simulated outcome", ["Success", "Failure"])
    actual_latency = st.number_input("Observed latency (ms)", min_value=1.0, max_value=600000.0, value=160.0, step=5.0)
    feedback_submitted = st.form_submit_button("Save outcome feedback")
if feedback_submitted:
    try:
        response = requests.post(
            f"{BASE_URL}/feedback",
            json={
                "transaction_id": feedback_transaction_id,
                "success": outcome == "Success",
                "actual_latency_ms": actual_latency,
            },
            timeout=10,
        )
        if response.ok:
            st.success("Outcome recorded. UCB routing can use this feedback for future selection.")
        else:
            st.error(f"Feedback failed ({response.status_code}): {response.text}")
    except requests.RequestException as exc:
        st.error(f"API request failed: {exc}")

st.divider()
st.subheader("Gateway health and feedback")
try:
    gateway_response = requests.get(f"{BASE_URL}/gateways", timeout=5)
    gateway_response.raise_for_status()
    gateways = pd.DataFrame(gateway_response.json())
    st.dataframe(gateways, use_container_width=True, hide_index=True)
    stats_response = requests.get(f"{BASE_URL}/stats", timeout=5)
    stats_response.raise_for_status()
    stats = stats_response.json()
    col1, col2, col3 = st.columns(3)
    col1.metric("Recorded routes", stats["total_routes"])
    col2.metric("Feedback records", stats["total_feedback"])
    col3.metric(
        "Observed success rate",
        f"{stats['observed_success_rate']:.1%}" if stats["observed_success_rate"] is not None else "N/A",
    )
    recent_response = requests.get(f"{BASE_URL}/routes?limit=20", timeout=5)
    recent_response.raise_for_status()
    recent_routes = recent_response.json()
    if recent_routes:
        st.subheader("Recent routes")
        st.dataframe(pd.DataFrame(recent_routes), use_container_width=True, hide_index=True)
except requests.RequestException as exc:
    st.warning(f"Could not load analytics: {exc}")
