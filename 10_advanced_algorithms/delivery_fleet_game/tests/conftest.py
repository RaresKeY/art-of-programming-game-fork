"""
Shared pytest fixtures for Delivery Fleet game tests.
"""

import sys
from pathlib import Path
import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]

# Ensure the project root is on sys.path so `src` imports work in tests.
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture(scope="session")
def project_root() -> Path:
    """Return the root directory of the delivery fleet project."""
    return PROJECT_ROOT


@pytest.fixture(scope="session")
def data_dir(project_root: Path) -> Path:
    """Path to the bundled JSON data directory."""
    return project_root / "data"


@pytest.fixture(scope="session")
def data_loader(data_dir: Path):
    """Shared DataLoader instance for tests."""
    from src.utils import DataLoader

    return DataLoader(data_dir)


@pytest.fixture
def game_engine(data_dir: Path):
    """Fresh GameEngine instance per test with initial game loaded."""
    from src.core import GameEngine

    engine = GameEngine(data_dir)
    engine.new_game()
    return engine


@pytest.fixture
def simple_map():
    """Utility map for geometry-focused tests."""
    from src.models import DeliveryMap

    delivery_map = DeliveryMap(width=100, height=100)
    delivery_map.depot = (0.0, 0.0)
    return delivery_map


@pytest.fixture
def sample_vehicle_type():
    """Lightweight vehicle type for isolated model tests."""
    from src.models import VehicleType

    return VehicleType(
        name="Test Van",
        capacity_m3=12.0,
        cost_per_km=1.0,
        purchase_price=20000.0,
        max_range_km=300.0,
    )


@pytest.fixture
def sample_vehicle(sample_vehicle_type):
    """Vehicle bound to the sample vehicle type."""
    from src.models import Vehicle

    return Vehicle(id="veh_test", vehicle_type=sample_vehicle_type)
