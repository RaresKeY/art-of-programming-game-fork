"""
Package model for delivery items.

This module defines the Package entity representing items to be delivered.
"""

from dataclasses import dataclass
from typing import Tuple, Optional


@dataclass
class Package:
    """
    Represents a package to be delivered.

    Attributes:
        id: Unique package identifier
        destination: Delivery location as (x, y) coordinates
        volume_m3: Package volume in cubic meters
        payment: Revenue received for delivering this package
        priority: Delivery priority (1=low, 5=high)
        description: Optional description of package contents
        received_day: Game day when package was received (default 0)
    """
    id: str
    destination: Tuple[float, float]
    volume_m3: float
    payment: float
    priority: int = 1
    description: Optional[str] = None
    received_day: int = 0
    is_rush: bool = False
    bonus_multiplier: float = 1.0

    def __lt__(self, other: 'Package') -> bool:
        """
        Compare packages by priority for sorting.
        Higher priority values come first (reverse order).

        Args:
            other: Another package to compare with

        Returns:
            True if this package has higher priority than other
        """
        return self.priority > other.priority

    def __str__(self) -> str:
        desc = f" - {self.description}" if self.description else ""
        return (f"Package {self.id}: {self.volume_m3}m³ to {self.destination}, "
                f"pays ${self.payment} (Priority {self.priority}){desc}")

    def __repr__(self) -> str:
        return f"Package(id='{self.id}', vol={self.volume_m3}, pay=${self.payment})"

    @property
    def value_density(self) -> float:
        """
        Calculate payment per cubic meter (value density).
        Useful for optimization heuristics.

        Returns:
            Payment per m³ ratio
        """
        return self.payment / self.volume_m3 if self.volume_m3 > 0 else 0.0
