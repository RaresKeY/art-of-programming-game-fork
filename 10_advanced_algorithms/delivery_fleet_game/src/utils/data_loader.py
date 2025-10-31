"""
Data loading utilities for JSON configuration files.

This module handles reading and parsing JSON data files for the game.
"""

import json
from pathlib import Path
from typing import Dict, List
from ..models import (
    VehicleType, Vehicle, Package, DeliveryMap,
    Location, GameState, DayHistory
)
from ..core.difficulty import DemandTier


class DataLoader:
    """Handles loading game data from JSON files."""

    def __init__(self, data_dir: Path):
        """
        Initialize data loader.

        Args:
            data_dir: Path to directory containing JSON data files
        """
        self.data_dir = Path(data_dir)

    def load_vehicle_types(self, filename: str = "vehicles.json") -> Dict[str, VehicleType]:
        """
        Load vehicle type definitions from JSON.

        Args:
            filename: Name of vehicles JSON file

        Returns:
            Dictionary mapping vehicle type names to VehicleType objects

        Example JSON structure:
        {
          "vehicle_types": {
            "small_van": {
              "name": "Small Van",
              "capacity_m3": 10,
              "cost_per_km": 0.50,
              "purchase_price": 15000,
              "max_range_km": 200
            }
          }
        }
        """
        filepath = self.data_dir / filename
        with open(filepath, 'r') as f:
            data = json.load(f)

        vehicle_types = {}
        for type_key, type_data in data['vehicle_types'].items():
            vehicle_types[type_key] = VehicleType(
                name=type_data['name'],
                capacity_m3=type_data['capacity_m3'],
                cost_per_km=type_data['cost_per_km'],
                purchase_price=type_data['purchase_price'],
                max_range_km=type_data['max_range_km']
            )

        return vehicle_types

    def load_packages(self, filename: str) -> List[Package]:
        """
        Load packages from JSON file.

        Args:
            filename: Name of packages JSON file (e.g., "packages_day1.json")

        Returns:
            List of Package objects

        Example JSON structure:
        {
          "day": 1,
          "packages": [
            {
              "id": "pkg_001",
              "destination": {"x": 20, "y": 30},
              "volume_m3": 2.5,
              "payment": 45,
              "priority": 1,
              "description": "Electronics"
            }
          ]
        }
        """
        filepath = self.data_dir / filename
        with open(filepath, 'r') as f:
            data = json.load(f)

        packages = []
        for pkg_data in data['packages']:
            dest = pkg_data['destination']
            package = Package(
                id=pkg_data['id'],
                destination=(dest['x'], dest['y']),
                volume_m3=pkg_data['volume_m3'],
                payment=pkg_data['payment'],
                priority=pkg_data.get('priority', 1),
                description=pkg_data.get('description', None),
                is_rush=pkg_data.get('is_rush', False),
                bonus_multiplier=pkg_data.get('bonus_multiplier', 1.0)
            )
            packages.append(package)

        return packages

    def load_map(self, filename: str = "map.json") -> DeliveryMap:
        """
        Load map configuration from JSON.

        Args:
            filename: Name of map JSON file

        Returns:
            DeliveryMap object with locations

        Example JSON structure:
        {
          "width": 100,
          "height": 100,
          "depot": {"x": 0, "y": 0, "name": "Main Depot"},
          "locations": [
            {
              "id": "loc_001",
              "name": "Business District",
              "x": 45,
              "y": 60
            }
          ]
        }
        """
        filepath = self.data_dir / filename
        with open(filepath, 'r') as f:
            data = json.load(f)

        delivery_map = DeliveryMap(
            width=data['width'],
            height=data['height']
        )

        # Set depot (should be at origin)
        depot_data = data.get('depot', {'x': 0, 'y': 0})
        delivery_map.depot = (depot_data['x'], depot_data['y'])

        # Load named locations
        for loc_data in data.get('locations', []):
            location = Location(
                id=loc_data['id'],
                name=loc_data['name'],
                x=loc_data['x'],
                y=loc_data['y']
            )
            delivery_map.add_location(location)

        return delivery_map

    def load_game_state(self, filename: str = "initial_game_state.json",
                       vehicle_types: Dict[str, VehicleType] = None) -> GameState:
        """
        Load saved game state from JSON.

        Args:
            filename: Name of save file
            vehicle_types: Dictionary of available vehicle types

        Returns:
            GameState object

        Example JSON structure:
        {
          "current_day": 1,
          "balance": 100000,
          "fleet": [
            {
              "id": "veh_001",
              "type": "small_van",
              "purchase_day": 0,
              "current_location": {"x": 0, "y": 0}
            }
          ],
          "history": []
        }
        """
        filepath = self.data_dir / filename
        with open(filepath, 'r') as f:
            data = json.load(f)

        game_state = GameState(
            initial_balance=data['balance'],
            start_day=data['current_day']
        )

        game_state.marketing_level = data.get('marketing_level', game_state.marketing_level)
        game_state.popularity_score = data.get('popularity', game_state.popularity_score)
        game_state.last_popularity_delta = data.get('popularity_delta', 0)
        game_state.popularity_history = [game_state.popularity_score]
        game_state.missed_delivery_penalty_rate = data.get('penalty_rate', game_state.missed_delivery_penalty_rate)

        if 'popularity_history' in data and isinstance(data['popularity_history'], list):
            game_state.popularity_history = data['popularity_history'][-20:]  # keep recent slice
            game_state.popularity_score = game_state.popularity_history[-1]

        for record in data.get('history', []):
            history_entry = DayHistory(
                day=record['day'],
                packages_delivered=record['packages_delivered'],
                packages_attempted=record['packages_attempted'],
                revenue=record['revenue'],
                costs=record['costs'],
                profit=record['profit'],
                agent_used=record.get('agent_used', 'Manual'),
                routes_count=record.get('routes_count', 0),
                total_distance=record.get('total_distance', 0.0),
                balance_end=record.get('balance_end', game_state.balance),
                popularity_start=record.get('popularity_start', game_state.popularity_score),
                popularity_end=record.get('popularity_end', game_state.popularity_score),
                popularity_delta=record.get('popularity_delta', 0),
                demand_tier=record.get('demand_tier', DemandTier.CALM.value),
                penalties=record.get('penalties', 0.0),
            )
            game_state.history.append(history_entry)


        # Load fleet
        if vehicle_types:
            for vehicle_data in data.get('fleet', []):
                vehicle_type = vehicle_types[vehicle_data['type']]
                loc = vehicle_data.get('current_location', {'x': 0, 'y': 0})
                vehicle = Vehicle(
                    id=vehicle_data['id'],
                    vehicle_type=vehicle_type,
                    current_location=(loc['x'], loc['y']),
                    purchase_day=vehicle_data.get('purchase_day', 0)
                )
                game_state.add_vehicle(vehicle)

        return game_state

    def save_game_state(self, game_state: GameState, filename: str = "savegame.json") -> None:
        """
        Save current game state to JSON.

        Args:
            game_state: GameState to save
            filename: Name of save file
        """
        filepath = self.data_dir / filename

        data = {
            "current_day": game_state.current_day,
            "balance": game_state.balance,
            "marketing_level": game_state.marketing_level,
            "popularity": game_state.popularity_score,
            "popularity_delta": game_state.last_popularity_delta,
            "popularity_history": game_state.popularity_history[-50:],
            "demand_tier": game_state.current_demand_tier.value,
            "penalty_rate": game_state.missed_delivery_penalty_rate,
            "fleet": [
                {
                    "id": v.id,
                    "type": v.vehicle_type.name.lower().replace(' ', '_'),
                    "purchase_day": v.purchase_day,
                    "current_location": {
                        "x": v.current_location[0],
                        "y": v.current_location[1]
                    }
                }
                for v in game_state.fleet
            ],
            "history": [
                {
                    "day": h.day,
                    "packages_delivered": h.packages_delivered,
                    "packages_attempted": h.packages_attempted,
                    "revenue": h.revenue,
                    "costs": h.costs,
                    "profit": h.profit,
                    "agent_used": h.agent_used,
                    "balance_end": h.balance_end,
                    "popularity_start": h.popularity_start,
                    "popularity_end": h.popularity_end,
                    "popularity_delta": h.popularity_delta,
                    "demand_tier": h.demand_tier,
                    "penalties": getattr(h, 'penalties', 0.0),
                }
                for h in game_state.history
            ]
        }

        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)

    def get_available_package_days(self) -> List[int]:
        """
        Find all available package day files.

        Returns:
            List of day numbers that have package data
        """
        pattern = "packages_day*.json"
        files = sorted(self.data_dir.glob(pattern))
        days = []
        for f in files:
            # Extract day number from filename
            try:
                day_str = f.stem.replace('packages_day', '')
                days.append(int(day_str))
            except ValueError:
                continue
        return days
