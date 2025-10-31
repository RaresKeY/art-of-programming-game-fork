from pathlib import Path


def test_vehicle_types_loaded(data_loader):
    types = data_loader.load_vehicle_types()

    # Ensure core vehicle types exist with expected stats.
    assert set(types.keys()) >= {"small_van", "medium_truck", "large_truck"}
    small_van = types["small_van"]
    assert small_van.capacity_m3 == 10
    assert small_van.max_range_km == 350


def test_map_configuration_loaded(data_loader):
    delivery_map = data_loader.load_map()

    assert delivery_map.width == 100
    assert delivery_map.height == 100
    # The bundled map defines 8 named locations.
    assert len(delivery_map.locations) == 8
    assert delivery_map.depot == (0, 0)


def test_initial_game_state_loaded(data_loader):
    game_state = data_loader.load_game_state(vehicle_types=data_loader.load_vehicle_types())

    assert game_state.current_day == 1
    assert game_state.balance == 100_000
    # Initial fleet shipped with two vehicles.
    assert len(game_state.fleet) == 2
