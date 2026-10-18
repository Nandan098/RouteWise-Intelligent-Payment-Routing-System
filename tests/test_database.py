from routewise.database import Database


def test_database_initializes_and_stats_are_empty(tmp_path):
    database = Database(tmp_path / "empty.db")
    stats = database.get_stats()
    assert stats == {
        "total_routes": 0,
        "routes_by_gateway": {},
        "total_feedback": 0,
        "observed_success_rate": None,
        "average_actual_latency_ms": None,
    }
