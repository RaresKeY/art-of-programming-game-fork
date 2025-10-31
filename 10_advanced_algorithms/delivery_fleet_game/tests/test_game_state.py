import pytest


def test_purchase_vehicle_updates_balance(sample_vehicle_type):
    from src.models import GameState

    state = GameState(initial_balance=50_000)
    success = state.purchase_vehicle(sample_vehicle_type, "veh_001")

    assert success
    assert pytest.approx(state.balance) == 30_000  # 50k - 20k purchase
    assert len(state.fleet) == 1
    assert state.fleet[0].id == "veh_001"


def test_marketing_upgrade_progression():
    from src.models import GameState

    state = GameState(initial_balance=100_000)
    initial_level = state.marketing_level
    cost = state.get_marketing_cost()

    assert state.upgrade_marketing()
    assert state.marketing_level == initial_level + 1
    assert pytest.approx(state.balance) == 100_000 - cost

    # Spending down balance should prevent further upgrades.
    state.balance = 1000
    assert not state.upgrade_marketing()


def test_execute_routes_records_history(simple_map, sample_vehicle_type, sample_vehicle):
    from src.models import GameState, Package, Route

    state = GameState(initial_balance=10_000)
    pkg_a = Package(id="pkg_a", destination=(10.0, 0.0), volume_m3=3.0, payment=60.0)
    pkg_b = Package(id="pkg_b", destination=(0.0, 12.0), volume_m3=3.5, payment=70.0)
    state.packages_pending = [pkg_a, pkg_b]

    route = Route(
        vehicle=sample_vehicle,
        packages=[pkg_a, pkg_b],
        stops=[pkg_a.destination, pkg_b.destination],
        delivery_map=simple_map,
    )
    state.set_routes([route])

    profit = state.execute_routes(agent_name="TestAgent")

    assert profit > 0
    assert len(state.packages_pending) == 0
    assert len(state.packages_delivered) == 2
    assert len(state.history) == 1
    record = state.history[-1]
    assert record.agent_used == "TestAgent"
    assert record.packages_delivered == 2
    assert record.profit == pytest.approx(profit)
    assert state.balance == pytest.approx(10_000 + profit)
    assert record.popularity_end == state.popularity_score
    assert record.demand_tier == state.current_demand_tier.value
    assert isinstance(record.popularity_delta, int)
    assert record.penalties == pytest.approx(0.0)


def test_penalty_applied_for_undelivered_packages(simple_map, sample_vehicle_type, sample_vehicle):
    from src.models import GameState, Package, Route

    state = GameState(initial_balance=5_000)
    state.missed_delivery_penalty_rate = 0.5

    pkg_delivered = Package(id="pkg_ok", destination=(5.0, 0.0), volume_m3=2.0, payment=200.0)
    pkg_missed = Package(id="pkg_miss", destination=(10.0, 0.0), volume_m3=3.0, payment=150.0)
    state.packages_pending = [pkg_delivered, pkg_missed]

    route = Route(
        vehicle=sample_vehicle,
        packages=[pkg_delivered],
        stops=[pkg_delivered.destination],
        delivery_map=simple_map,
    )
    state.set_routes([route])

    profit = state.execute_routes(agent_name="Manual")

    # Expected: revenue 200, travel cost 10, penalty 75 => profit 115
    assert pytest.approx(profit) == 115.0
    assert state.balance == pytest.approx(5_000 + 115.0)
    assert len(state.packages_pending) == 1
    remaining = state.packages_pending[0]
    assert remaining.id == "pkg_miss"
    record = state.history[-1]
    assert pytest.approx(record.penalties) == 75.0
    assert record.packages_delivered == 1
    assert record.packages_attempted == 2
