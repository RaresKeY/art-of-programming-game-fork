"""
Game state management for the delivery fleet simulation.

This module handles the overall game state, including day progression,
financial tracking, and history logging.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
from .vehicle import Vehicle, VehicleType
from .package import Package
from .route import Route


@dataclass
class DayHistory:
    """
    Records performance metrics for a single day.

    Attributes:
        day: Day number
        packages_delivered: Number of packages successfully delivered
        packages_attempted: Total packages available that day
        revenue: Total revenue earned
        costs: Total operating costs
        profit: Net profit (revenue - costs)
        agent_used: Name of routing agent used
        routes_count: Number of routes executed
        total_distance: Total distance traveled by all vehicles
        balance_end: Company balance at end of day
    """
    day: int
    packages_delivered: int
    packages_attempted: int
    revenue: float
    costs: float
    profit: float
    agent_used: str = "Manual"
    routes_count: int = 0
    total_distance: float = 0.0
    balance_end: float = 0.0

    @property
    def delivery_rate(self) -> float:
        """Calculate percentage of packages successfully delivered."""
        return (self.packages_delivered / self.packages_attempted * 100
                if self.packages_attempted > 0 else 0.0)

    def __str__(self) -> str:
        return (f"Day {self.day}: {self.packages_delivered}/{self.packages_attempted} packages "
                f"(${self.profit:+.2f} profit, ${self.balance_end:.2f} balance)")


class GameState:
    """
    Manages the complete state of the delivery fleet simulation.

    This is the central state manager that tracks:
    - Current game day
    - Financial balance
    - Fleet of vehicles
    - Package inventory (pending, in-transit, delivered)
    - Planned routes
    - Historical performance data
    """

    def __init__(self, initial_balance: float = 100000.0, start_day: int = 1):
        """
        Initialize game state.

        Args:
            initial_balance: Starting company balance in dollars
            start_day: Starting day number (default 1)
        """
        self.current_day: int = start_day
        self.balance: float = initial_balance
        self.fleet: List[Vehicle] = []
        self.packages_pending: List[Package] = []
        self.packages_in_transit: List[Package] = []
        self.packages_delivered: List[Package] = []
        self.current_routes: List[Route] = []
        self.history: List[DayHistory] = []

        # Marketing system
        self.marketing_level: int = 1  # Level 1-5
        self.base_package_volume: float = 25.0  # Base daily m³

    def add_vehicle(self, vehicle: Vehicle) -> None:
        """
        Add a vehicle to the fleet.

        Args:
            vehicle: Vehicle to add
        """
        self.fleet.append(vehicle)

    def purchase_vehicle(self, vehicle_type: VehicleType, vehicle_id: str) -> bool:
        """
        Purchase a new vehicle if balance allows.

        Args:
            vehicle_type: Type of vehicle to purchase
            vehicle_id: Unique ID for the new vehicle

        Returns:
            True if purchase successful, False if insufficient funds
        """
        if self.balance >= vehicle_type.purchase_price:
            self.balance -= vehicle_type.purchase_price
            new_vehicle = Vehicle(
                id=vehicle_id,
                vehicle_type=vehicle_type,
                purchase_day=self.current_day
            )
            self.add_vehicle(new_vehicle)
            return True
        return False

    def load_packages(self, packages: List[Package]) -> None:
        """
        Load new packages for the current day.

        Args:
            packages: List of packages to add to pending queue
        """
        for pkg in packages:
            pkg.received_day = self.current_day
        self.packages_pending.extend(packages)

    def set_routes(self, routes: List[Route]) -> None:
        """
        Set the planned routes for the current day.

        Args:
            routes: List of routes to execute
        """
        self.current_routes = routes

    def execute_routes(self, agent_name: str = "Manual") -> float:
        """
        Execute planned routes and update game state.

        This simulates running the delivery day:
        1. Move packages from pending to in-transit
        2. Calculate costs and revenues
        3. Update balance
        4. Move packages to delivered
        5. Record day history

        Args:
            agent_name: Name of routing algorithm used

        Returns:
            Total profit for the day
        """
        if not self.current_routes:
            print("Warning: No routes to execute")
            return 0.0

        # Calculate totals
        total_revenue = sum(route.total_revenue for route in self.current_routes)
        total_cost = sum(route.total_cost for route in self.current_routes)
        total_profit = total_revenue - total_cost
        total_distance = sum(route.total_distance for route in self.current_routes)

        # Collect delivered packages
        delivered_packages = []
        for route in self.current_routes:
            delivered_packages.extend(route.packages)

        # Update package lists
        packages_attempted = len(self.packages_pending)
        self.packages_delivered.extend(delivered_packages)

        # Remove delivered packages from pending
        delivered_ids = {pkg.id for pkg in delivered_packages}
        self.packages_pending = [pkg for pkg in self.packages_pending
                                if pkg.id not in delivered_ids]

        # Update balance
        self.balance += total_profit

        # Record history
        day_record = DayHistory(
            day=self.current_day,
            packages_delivered=len(delivered_packages),
            packages_attempted=packages_attempted,
            revenue=total_revenue,
            costs=total_cost,
            profit=total_profit,
            agent_used=agent_name,
            routes_count=len(self.current_routes),
            total_distance=total_distance,
            balance_end=self.balance
        )
        self.history.append(day_record)

        return total_profit

    def advance_day(self) -> None:
        """
        Move to the next day.

        Clears current routes and prepares for new day.
        IMPORTANT: Any undelivered packages are cleared (expired/cancelled).
        """
        self.current_day += 1
        self.current_routes = []
        self.packages_in_transit = []
        # Clear pending packages - they expire if not delivered
        self.packages_pending = []

    def get_available_fleet(self) -> List[Vehicle]:
        """
        Get list of available vehicles (copies for planning).

        Returns:
            Copy of fleet list for route planning
        """
        return self.fleet.copy()

    def get_statistics(self) -> Dict:
        """
        Get overall game statistics.

        Returns:
            Dictionary with cumulative stats
        """
        if not self.history:
            return {
                'total_days': 0,
                'total_profit': 0.0,
                'total_packages': 0,
                'avg_daily_profit': 0.0,
                'delivery_rate': 0.0
            }

        total_profit = sum(h.profit for h in self.history)
        total_packages = sum(h.packages_delivered for h in self.history)
        total_attempted = sum(h.packages_attempted for h in self.history)
        avg_daily_profit = total_profit / len(self.history)
        delivery_rate = (total_packages / total_attempted * 100
                        if total_attempted > 0 else 0.0)

        return {
            'total_days': len(self.history),
            'current_day': self.current_day,
            'current_balance': self.balance,
            'total_profit': total_profit,
            'total_packages': total_packages,
            'avg_daily_profit': avg_daily_profit,
            'delivery_rate': delivery_rate,
            'fleet_size': len(self.fleet)
        }

    def is_game_over(self) -> tuple[bool, str]:
        """
        Check if game has ended (win or lose condition).

        Returns:
            Tuple of (game_over: bool, reason: str)
        """
        # Lose condition: bankrupt
        if self.balance < 0:
            return True, "Bankruptcy - Balance below $0"

        # Lose condition: three consecutive losses
        if len(self.history) >= 3:
            recent = self.history[-3:]
            if all(day.profit < 0 for day in recent):
                return True, "Three consecutive days of losses"

        # Win condition: reach day 30 with good balance
        if self.current_day > 30 and self.balance > 200000:
            return True, f"Victory! Reached day 30 with ${self.balance:.2f}"

        return False, ""

    def get_last_day_summary(self) -> Optional[DayHistory]:
        """
        Get the most recent day's performance.

        Returns:
            Last DayHistory record, or None if no history
        """
        return self.history[-1] if self.history else None

    def get_marketing_cost(self) -> float:
        """
        Get cost to upgrade marketing to next level.

        Returns:
            Cost in dollars, or 0 if max level
        """
        costs = {
            1: 20000,   # Level 1→2: $20K
            2: 35000,   # Level 2→3: $35K
            3: 55000,   # Level 3→4: $55K
            4: 80000,   # Level 4→5: $80K
            5: 0        # Max level
        }
        return costs.get(self.marketing_level, 0)

    def get_daily_package_volume(self) -> float:
        """
        Calculate expected daily package volume based on marketing level.

        Returns:
            Expected total volume in m³
        """
        # Volume increases with marketing level
        multipliers = {
            1: 1.0,    # 25m³ base
            2: 1.3,    # 32.5m³
            3: 1.7,    # 42.5m³
            4: 2.2,    # 55m³
            5: 2.8     # 70m³
        }
        return self.base_package_volume * multipliers.get(self.marketing_level, 1.0)

    def upgrade_marketing(self) -> bool:
        """
        Upgrade marketing level if affordable.

        Returns:
            True if upgrade successful, False if not enough funds or max level
        """
        if self.marketing_level >= 5:
            return False  # Max level

        cost = self.get_marketing_cost()
        if self.balance >= cost:
            self.balance -= cost
            self.marketing_level += 1
            return True
        return False

    def get_marketing_info(self) -> dict:
        """
        Get marketing system information.

        Returns:
            Dictionary with marketing stats
        """
        return {
            'level': self.marketing_level,
            'current_volume': self.get_daily_package_volume(),
            'next_level_volume': self.base_package_volume * {
                1: 1.3, 2: 1.7, 3: 2.2, 4: 2.8, 5: 2.8
            }.get(self.marketing_level, 2.8),
            'upgrade_cost': self.get_marketing_cost(),
            'can_afford': self.balance >= self.get_marketing_cost(),
            'is_max_level': self.marketing_level >= 5
        }

    def __str__(self) -> str:
        return (f"Day {self.current_day} | Balance: ${self.balance:.2f} | "
                f"Fleet: {len(self.fleet)} vehicles | "
                f"Pending: {len(self.packages_pending)} packages")

    def __repr__(self) -> str:
        return f"GameState(day={self.current_day}, balance=${self.balance:.2f})"
