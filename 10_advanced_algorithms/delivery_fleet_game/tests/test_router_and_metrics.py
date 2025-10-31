import math

import pytest


def test_nearest_neighbor_orders_points(simple_map):
    from src.core import Router

    points = [(5, 0), (5, 5), (0, 6), (12, 2)]
    ordered = Router.nearest_neighbor_tsp(points, simple_map.depot, simple_map)

    assert set(ordered) == set(points)
    # First point should be the closest one to the depot (5,0) with distance 5.
    assert ordered[0] == (5, 0)


def test_two_opt_does_not_increase_distance(simple_map):
    from src.core import Router

    # Intentional zig-zag ordering to encourage 2-opt improvement.
    initial_route = [(0, 30), (30, -5), (5, 30), (-30, -5)]
    original_distance = Router.calculate_route_distance(initial_route, simple_map)

    optimized = Router.two_opt_improvement(initial_route, simple_map, max_iterations=50)
    optimized_distance = Router.calculate_route_distance(optimized, simple_map)

    assert set(optimized) == set(initial_route)
    assert optimized_distance <= original_distance + 1e-6


def test_route_metrics_aggregate_values(simple_map, sample_vehicle, sample_vehicle_type):
    from src.models import Package, Route
    from src.utils.metrics import calculate_route_metrics

    pkg1 = Package(id="pkg1", destination=(10.0, 0.0), volume_m3=2.0, payment=60.0)
    pkg2 = Package(id="pkg2", destination=(10.0, 10.0), volume_m3=3.0, payment=70.0)
    route = Route(
        vehicle=sample_vehicle,
        packages=[pkg1, pkg2],
        stops=[pkg1.destination, pkg2.destination],
        delivery_map=simple_map,
    )

    metrics = calculate_route_metrics([route])

    assert metrics["vehicles_used"] == 1
    assert metrics["packages_delivered"] == 2
    assert metrics["total_revenue"] == pytest.approx(pkg1.payment + pkg2.payment)
    assert metrics["total_cost"] == pytest.approx(route.total_cost)
    assert metrics["total_profit"] == pytest.approx(route.profit)
    assert metrics["avg_capacity_utilization"] > 0
    assert metrics["avg_efficiency"] == pytest.approx(route.efficiency)
