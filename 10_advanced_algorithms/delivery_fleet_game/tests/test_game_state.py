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
