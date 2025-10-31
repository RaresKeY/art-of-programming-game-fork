"""
Game engine for the delivery fleet simulation.

This module contains the main game logic and orchestration.
"""

from pathlib import Path
from typing import Dict, List, Optional
from ..models import GameState, Package, Route, DeliveryMap, VehicleType
from ..utils import DataLoader, calculate_route_metrics
from ..utils.package_generator import PackageGenerator
from .difficulty import DifficultySnapshot


class GameEngine:
    """
    Main game engine that orchestrates the delivery fleet simulation.

    The engine manages:
    - Game state and progression
    - Data loading
    - Agent registration and execution
    - Day cycle management
    """

    def __init__(self, data_dir: Path):
        """
        Initialize game engine.

        Args:
            data_dir: Path to directory containing game data files
        """
        self.data_dir = Path(data_dir)
        self.data_loader = DataLoader(self.data_dir)

        # Load static data
        self.vehicle_types: Dict[str, VehicleType] = {}
        self.delivery_map: Optional[DeliveryMap] = None
        self.game_state: Optional[GameState] = None

        # Agent registry
        self.agents: Dict[str, object] = {}  # Will be populated with RouteAgent instances
        self.current_difficulty: Optional[DifficultySnapshot] = None

        # Initialize data
        self._load_static_data()

    def _load_static_data(self) -> None:
        """Load vehicle types and map configuration."""
        try:
            self.vehicle_types = self.data_loader.load_vehicle_types()
            self.delivery_map = self.data_loader.load_map()
            self.package_generator = PackageGenerator(self.delivery_map)
            print(f"✓ Loaded {len(self.vehicle_types)} vehicle types")
            print(f"✓ Loaded map: {self.delivery_map}")
            print(f"✓ Initialized package generator")
        except FileNotFoundError as e:
            print(f"Error loading data: {e}")
            raise

    def new_game(self) -> None:
        """Start a new game with initial state."""
        self.game_state = self.data_loader.load_game_state(
            "initial_game_state.json",
            self.vehicle_types
        )
        self.current_difficulty = self.game_state.compute_difficulty_snapshot()
        print(f"✓ New game started: {self.game_state}")

    def load_game(self, save_file: str = "savegame.json") -> None:
        """
        Load a saved game.

        Args:
            save_file: Name of save file to load
        """
        self.game_state = self.data_loader.load_game_state(
            save_file,
            self.vehicle_types
        )
        self.current_difficulty = self.game_state.compute_difficulty_snapshot()
        print(f"✓ Game loaded: {self.game_state}")

    def save_game(self, save_file: str = "savegame.json") -> None:
        """
        Save current game state.

        Args:
            save_file: Name of save file
        """
        if not self.game_state:
            print("No game to save!")
            return

        self.data_loader.save_game_state(self.game_state, save_file)
        print(f"✓ Game saved to {save_file}")

    def register_agent(self, name: str, agent: object) -> None:
        """
        Register a routing agent.

        Args:
            name: Agent identifier
            agent: RouteAgent instance
        """
        self.agents[name] = agent
        print(f"✓ Registered agent: {name}")

    def _refresh_difficulty_snapshot(self) -> Optional[DifficultySnapshot]:
        """Rebuild the difficulty snapshot from the current game state."""
        if not self.game_state:
            self.current_difficulty = None
            return None
        snapshot = self.game_state.compute_difficulty_snapshot()
        self.current_difficulty = snapshot
        return snapshot

    def load_day_packages(self, day: Optional[int] = None) -> List[Package]:
        """
        Load or generate packages for a specific day.

        Uses intelligent generation based on day progression and marketing level.
        Static JSON files for days 1-5 are deprecated in favor of reproducible generation.

        Args:
            day: Day number (uses current day if None)

        Returns:
            List of packages for the day
        """
        if day is None:
            day = self.game_state.current_day if self.game_state else 1

        snapshot = self._refresh_difficulty_snapshot()
        modifiers = snapshot.modifiers if snapshot else {}

        target_volume = self.game_state.get_daily_package_volume()
        marketing_level = self.game_state.marketing_level

        tier_label = snapshot.demand_tier.value if snapshot else "Unknown"
        print(
            f"📦 Generating packages for day {day}"
            f" | Marketing Lvl {marketing_level} | Demand: {tier_label}"
        )

        packages = self.package_generator.generate_packages(
            target_volume=target_volume,
            day=day,
            marketing_level=marketing_level,
            modifiers=modifiers,
        )
        return packages

    def start_day(self) -> None:
        """
        Begin a new day by loading packages.
        """
        if not self.game_state:
            print("No active game! Start a new game first.")
            return

        packages = self.load_day_packages()
        self.game_state.load_packages(packages)
        print(f"\n=== Day {self.game_state.current_day} Started ===")
        print(f"Packages to deliver: {len(packages)}")
        print(f"Available fleet: {len(self.game_state.fleet)} vehicles")
        print(f"Current balance: ${self.game_state.balance:,.2f}")
        if self.current_difficulty:
            print(
                f"Popularity {self.current_difficulty.popularity} | "
                f"Demand {self.current_difficulty.demand_tier.value} | "
                f"Challenge {self.current_difficulty.challenge_index:.0f}"
            )

    def test_agent(self, agent_name: str) -> Dict:
        """
        Test an agent's solution without executing.

        Args:
            agent_name: Name of agent to test

        Returns:
            Dictionary with performance metrics
        """
        if agent_name not in self.agents:
            print(f"Agent '{agent_name}' not found!")
            return {}

        if not self.game_state:
            print("No active game!")
            return {}

        print(f"\nTesting {agent_name}...")

        agent = self.agents[agent_name]
        routes = agent.plan_routes(
            self.game_state.packages_pending.copy(),
            self.game_state.get_available_fleet()
        )

        metrics = calculate_route_metrics(routes)
        metrics['agent_name'] = agent_name
        metrics['routes'] = routes  # Include routes for inspection

        return metrics

    def apply_agent_solution(self, agent_name: str) -> bool:
        """
        Apply an agent's solution to the game state.

        Args:
            agent_name: Name of agent to use

        Returns:
            True if successful
        """
        if agent_name not in self.agents:
            print(f"Agent '{agent_name}' not found!")
            return False

        if not self.game_state:
            print("No active game!")
            return False

        agent = self.agents[agent_name]
        routes = agent.plan_routes(
            self.game_state.packages_pending.copy(),
            self.game_state.get_available_fleet()
        )

        # Validate routes
        if not routes:
            print("Agent produced no routes!")
            return False

        invalid_routes = [r for r in routes if not r.is_valid()]
        if invalid_routes:
            print(f"Warning: {len(invalid_routes)} invalid routes!")
            for route in invalid_routes:
                print(f"  - {route.vehicle.id}: {route.get_summary()}")

        self.game_state.set_routes(routes)
        print(f"✓ Applied solution from {agent_name}")
        return True

    def execute_day(self, agent_name: str = "Manual") -> float:
        """
        Execute the current day's routes.

        Args:
            agent_name: Name of agent used (for history tracking)

        Returns:
            Profit for the day
        """
        if not self.game_state:
            print("No active game!")
            return 0.0

        if not self.game_state.current_routes:
            print("No routes planned! Plan routes first.")
            return 0.0

        print(f"\nExecuting day {self.game_state.current_day}...")
        profit = self.game_state.execute_routes(agent_name)

        # Display results
        last_day = self.game_state.get_last_day_summary()
        if last_day:
            print(f"\n=== Day {last_day.day} Complete ===")
            print(f"Delivered: {last_day.packages_delivered}/{last_day.packages_attempted} packages")
            print(f"Revenue: ${last_day.revenue:.2f}")
            print(f"Costs: ${last_day.costs:.2f}")
            print(f"Profit: ${last_day.profit:+.2f}")
            print(f"New Balance: ${last_day.balance_end:,.2f}")
            print(
                f"Popularity: {last_day.popularity_end} "
                f"({last_day.popularity_delta:+}) | Demand: {last_day.demand_tier}"
            )

        # Check game over conditions
        game_over, reason = self.game_state.is_game_over()
        if game_over:
            print(f"\n{'='*50}")
            print(f"GAME OVER: {reason}")
            print(f"{'='*50}")

        # Prepare difficulty for the upcoming day
        self._refresh_difficulty_snapshot()

        return profit

    def advance_to_next_day(self) -> None:
        """Move to the next day."""
        if not self.game_state:
            print("No active game!")
            return

        self.game_state.advance_day()
        print(f"\n→ Advanced to Day {self.game_state.current_day}")

    def purchase_vehicle(self, vehicle_type_name: str) -> bool:
        """
        Purchase a new vehicle.

        Args:
            vehicle_type_name: Type of vehicle to purchase

        Returns:
            True if purchase successful
        """
        if not self.game_state:
            print("No active game!")
            return False

        if vehicle_type_name not in self.vehicle_types:
            print(f"Unknown vehicle type: {vehicle_type_name}")
            print(f"Available types: {list(self.vehicle_types.keys())}")
            return False

        vehicle_type = self.vehicle_types[vehicle_type_name]

        # Generate unique ID
        vehicle_id = f"veh_{len(self.game_state.fleet) + 1:03d}"

        if self.game_state.purchase_vehicle(vehicle_type, vehicle_id):
            print(f"✓ Purchased {vehicle_type.name} for ${vehicle_type.purchase_price:,.2f}")
            print(f"  New balance: ${self.game_state.balance:,.2f}")
            return True
        else:
            print(f"✗ Insufficient funds! Need ${vehicle_type.purchase_price:,.2f}, have ${self.game_state.balance:,.2f}")
            return False

    def get_status(self) -> str:
        """
        Get current game status.

        Returns:
            Formatted status string
        """
        if not self.game_state:
            return "No active game"

        return str(self.game_state)

    def compare_agents(self, agent_names: List[str]) -> Dict[str, Dict]:
        """
        Compare performance of multiple agents.

        Args:
            agent_names: List of agent names to compare

        Returns:
            Dictionary mapping agent names to their metrics
        """
        results = {}

        for agent_name in agent_names:
            if agent_name in self.agents:
                metrics = self.test_agent(agent_name)
                if metrics:
                    results[agent_name] = metrics
            else:
                print(f"Skipping unknown agent: {agent_name}")

        return results

    def __str__(self) -> str:
        return f"GameEngine(agents={len(self.agents)}, state={self.get_status()})"
