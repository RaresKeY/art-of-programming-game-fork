"""
Dynamic package generator for delivery simulation.

Generates packages based on marketing level, day progression, and game state.
Implements intelligent difficulty scaling and geographic clustering.
"""

import random
from typing import List, Tuple, Dict
from ..models.package import Package
from ..models.map import DeliveryMap


class PackageGenerator:
    """
    Generates packages dynamically based on game state and progression.

    Creates realistic package distributions with:
    - Progressive difficulty based on day number
    - Geographic clustering for routing challenges
    - Marketing level integration
    - Reproducible seed-based generation
    """

    # Geographic zones for clustering
    ZONES = {
        'center': {'x': (35, 65), 'y': (35, 65)},
        'north': {'x': (20, 80), 'y': (65, 90)},
        'south': {'x': (20, 80), 'y': (10, 35)},
        'east': {'x': (65, 90), 'y': (20, 80)},
        'west': {'x': (10, 35), 'y': (20, 80)},
    }

    def __init__(self, delivery_map: DeliveryMap, base_seed: int = 42):
        """
        Initialize package generator.

        Args:
            delivery_map: Map for calculating distances and destinations
            base_seed: Base random seed for reproducibility
        """
        self.delivery_map = delivery_map
        self.base_seed = base_seed

    def generate_packages(
        self,
        target_volume: float,
        day: int,
        marketing_level: int = 1,
        modifiers: Dict[str, float] | None = None,
    ) -> List[Package]:
        """
        Generate packages with intelligent difficulty scaling.

        Uses day-based seed for reproducibility (same day = same packages).

        Args:
            target_volume: Target total volume in m³
            day: Current day number (for IDs and difficulty)
            marketing_level: Current marketing level (1-5)
            modifiers: Difficulty modifiers from popularity system

        Returns:
            List of generated packages
        """
        modifiers = modifiers or {}
        volume_multiplier = modifiers.get('volume_multiplier', 1.0)
        priority_bias = modifiers.get('priority_bias', 0.0)
        rush_ratio = modifiers.get('rush_ratio', 0.0)
        reward_multiplier = modifiers.get('reward_multiplier', 1.0)

        target_volume *= volume_multiplier

        # Set day-specific seed for reproducibility
        random.seed(self.base_seed + day)

        # Get difficulty tier based on day
        difficulty = self._get_difficulty_tier(day)

        # Calculate package distribution strategy
        cluster_strategy = self._get_cluster_strategy(day, marketing_level)

        # Generate packages with clustering
        packages = self._generate_clustered_packages(
            target_volume,
            day,
            marketing_level,
            difficulty,
            cluster_strategy,
            priority_bias,
            rush_ratio,
            reward_multiplier,
        )

        # Add strategic outliers based on difficulty
        if difficulty in ['early', 'mid', 'late']:
            packages.extend(
                self._generate_outliers(
                    day,
                    difficulty,
                    target_volume * 0.1,
                    priority_bias,
                    rush_ratio,
                    reward_multiplier,
                )
            )

        # Adjust priorities based on difficulty
        packages = self._adjust_priorities(packages, difficulty)

        total_volume = sum(p.volume_m3 for p in packages)
        print(f"📦 Generated {len(packages)} packages, {total_volume:.1f}m³ (target: {target_volume:.1f}m³)")
        print(f"   Difficulty: {difficulty.upper()} | Clusters: {cluster_strategy}")

        return packages

    def _get_difficulty_tier(self, day: int) -> str:
        """Determine difficulty tier based on day."""
        if day <= 3:
            return 'tutorial'
        elif day <= 7:
            return 'early'
        elif day <= 15:
            return 'mid'
        else:
            return 'late'

    def _get_cluster_strategy(self, day: int, marketing_level: int) -> Dict[str, float]:
        """
        Determine clustering strategy based on day and marketing level.

        Returns dict mapping zone names to % of total packages.
        """
        difficulty = self._get_difficulty_tier(day)

        if difficulty == 'tutorial':
            # Simple: 1-2 zones, easy routing
            return {'center': 0.6, 'north': 0.4}

        elif difficulty == 'early':
            # Introduce 2-3 zones
            return {'center': 0.4, 'north': 0.3, 'south': 0.3}

        elif difficulty == 'mid':
            # 3-4 zones, requires optimization
            if marketing_level <= 2:
                return {'center': 0.3, 'north': 0.25, 'south': 0.25, 'east': 0.2}
            else:
                return {'center': 0.2, 'north': 0.2, 'south': 0.2, 'east': 0.2, 'west': 0.2}

        else:  # late
            # All zones, complex optimization
            return {'center': 0.2, 'north': 0.2, 'south': 0.2, 'east': 0.2, 'west': 0.2}

    def _generate_clustered_packages(
        self,
        target_volume: float,
        day: int,
        marketing_level: int,
        difficulty: str,
        cluster_strategy: Dict[str, float],
        priority_bias: float,
        rush_ratio: float,
        reward_multiplier: float,
    ) -> List[Package]:
        """Generate packages distributed according to cluster strategy."""
        packages = []
        current_volume = 0.0
        package_count = 0

        # Calculate number of packages
        avg_package_size = 2.5
        num_packages = max(8, int(target_volume / avg_package_size))

        # Size distribution varies by difficulty
        size_distribution = self._get_size_distribution(difficulty)

        # Generate packages per zone
        for zone_name, zone_percentage in cluster_strategy.items():
            zone_target_volume = target_volume * zone_percentage
            zone_current_volume = 0.0

            while zone_current_volume < zone_target_volume and package_count < num_packages * 1.5:
                remaining_volume = zone_target_volume - zone_current_volume

                # Choose size
                size_type = self._choose_size_category(size_distribution, remaining_volume)
                volume = self._generate_volume(size_type, size_distribution, remaining_volume)

                # Generate destination in zone
                destination = self._generate_destination_in_zone(zone_name)

                # Calculate payment
                distance = self.delivery_map.distance(self.delivery_map.depot, destination)
                payment = self._calculate_payment(volume, distance)

                # Determine priority (increases with difficulty)
                priority_rate = 0.1 if difficulty == 'tutorial' else 0.15 if difficulty == 'early' else 0.2
                priority_rate = max(0.05, min(0.8, priority_rate + priority_bias))
                priority = 3 if random.random() < priority_rate else 1
                if priority == 3:
                    payment *= 1.5

                is_rush = random.random() < rush_ratio
                if is_rush:
                    payment *= 1.1  # rush premium

                # Create package
                package_id = f"pkg_d{day}_{package_count + 1:03d}"
                description = self._generate_description(volume, distance)

                package = Package(
                    id=package_id,
                    destination=destination,
                    volume_m3=round(volume, 1),
                    payment=round(payment * reward_multiplier, 2),
                    priority=priority,
                    description=description,
                    received_day=day,
                    is_rush=is_rush,
                    bonus_multiplier=reward_multiplier
                )

                packages.append(package)
                zone_current_volume += volume
                current_volume += volume
                package_count += 1

                if zone_current_volume >= zone_target_volume * 0.95:
                    break

        return packages

    def _get_size_distribution(self, difficulty: str) -> List[Tuple]:
        """Get package size distribution based on difficulty."""
        if difficulty == 'tutorial':
            # Easier: more small/medium packages
            return [
                ('small', 1.0, 2.5, 0.5),   # 50% small
                ('medium', 2.5, 4.0, 0.4),  # 40% medium
                ('large', 4.0, 6.0, 0.1),   # 10% large
            ]
        elif difficulty == 'early':
            return [
                ('small', 1.0, 2.5, 0.4),
                ('medium', 2.5, 4.0, 0.4),
                ('large', 4.0, 6.0, 0.2),
            ]
        else:  # mid/late
            # Harder: more large packages, bin packing challenges
            return [
                ('small', 1.0, 2.5, 0.3),
                ('medium', 2.5, 4.0, 0.4),
                ('large', 4.0, 6.0, 0.3),
            ]

    def _generate_outliers(
        self,
        day: int,
        difficulty: str,
        target_volume: float,
        priority_bias: float,
        rush_ratio: float,
        reward_multiplier: float,
    ) -> List[Package]:
        """Generate strategic outlier packages (far from main clusters)."""
        outliers = []

        # Number of outliers based on difficulty
        num_outliers = 1 if difficulty == 'early' else 2 if difficulty == 'mid' else 3

        volume_per_outlier = target_volume / num_outliers if num_outliers > 0 else 0

        for i in range(num_outliers):
            # Generate far destination (corners of map)
            corners = [
                (5, 5), (5, 95), (95, 5), (95, 95),  # Corners
                (10, 50), (90, 50), (50, 10), (50, 90)  # Edges
            ]
            destination = random.choice(corners)

            volume = min(volume_per_outlier, random.uniform(1.5, 3.5))
            distance = self.delivery_map.distance(self.delivery_map.depot, destination)
            payment = self._calculate_payment(volume, distance) * 1.3  # Pay more for outliers
            priority_rate = 0.15 if difficulty == 'early' else 0.22 if difficulty == 'mid' else 0.28
            priority_rate = max(0.05, min(0.85, priority_rate + priority_bias))
            priority = 3 if random.random() < priority_rate else 1
            if priority == 3:
                payment *= 1.5

            is_rush = random.random() < rush_ratio
            if is_rush:
                payment *= 1.15

            package_id = f"pkg_d{day}_outlier_{i + 1}"
            description = self._generate_description(volume, distance)

            outlier = Package(
                id=package_id,
                destination=destination,
                volume_m3=round(volume, 1),
                payment=round(payment * reward_multiplier, 2),
                priority=priority,
                description=f"[OUTLIER] {description}",
                received_day=day,
                is_rush=is_rush,
                bonus_multiplier=reward_multiplier
            )
            outliers.append(outlier)

        return outliers

    def _adjust_priorities(self, packages: List[Package], difficulty: str) -> List[Package]:
        """Adjust package priorities based on difficulty (ensures some high-priority)."""
        if difficulty == 'tutorial':
            # Tutorial: max 1 high priority
            high_priority_count = sum(1 for p in packages if p.priority == 3)
            if high_priority_count > 1:
                # Downgrade excess high-priority packages
                high_priority_packages = [p for p in packages if p.priority == 3]
                for pkg in high_priority_packages[1:]:
                    pkg.priority = 1
                    pkg.payment = pkg.payment / 1.5  # Remove high-priority bonus

        return packages

    def _generate_destination_in_zone(self, zone_name: str) -> Tuple[float, float]:
        """Generate destination within a specific geographic zone."""
        if zone_name not in self.ZONES:
            return self._generate_destination()

        zone = self.ZONES[zone_name]
        x = random.uniform(zone['x'][0], zone['x'][1])
        y = random.uniform(zone['y'][0], zone['y'][1])

        return (round(x, 1), round(y, 1))

    def _choose_size_category(self, distribution: List[Tuple], remaining_volume: float) -> str:
        """Choose package size category based on distribution and remaining volume."""
        # If remaining volume is small, prefer smaller packages
        if remaining_volume < 3.0:
            return 'small'
        elif remaining_volume < 5.0:
            choices = ['small', 'medium']
            return random.choice(choices)

        # Normal distribution-based selection
        rand = random.random()
        cumulative = 0.0
        for size_type, min_vol, max_vol, probability in distribution:
            cumulative += probability
            if rand <= cumulative:
                return size_type

        return 'medium'  # Default

    def _generate_volume(self, size_type: str, distribution: List[Tuple], remaining_volume: float) -> float:
        """Generate volume for a package of given size type."""
        # Find size range
        for st, min_vol, max_vol, _ in distribution:
            if st == size_type:
                # Generate random volume in range, respecting remaining volume
                max_vol = min(max_vol, remaining_volume + 0.5)
                volume = random.uniform(min_vol, max_vol)
                return volume

        return 2.0  # Default

    def _generate_destination(self) -> Tuple[float, float]:
        """Generate random destination on the map."""
        # Cluster destinations in sectors for more realistic routing
        # 70% in main area, 30% in outer areas

        if random.random() < 0.7:
            # Main delivery area (closer to depot)
            x = random.uniform(10, 60)
            y = random.uniform(10, 60)
        else:
            # Outer delivery area
            x = random.uniform(5, 95)
            y = random.uniform(5, 95)

        return (round(x, 1), round(y, 1))

    def _calculate_payment(self, volume: float, distance: float) -> float:
        """
        Calculate payment for package based on volume and distance.

        Payment formula: base_rate * volume + distance_rate * distance
        """
        base_rate = 15.0  # $/m³
        distance_rate = 0.3  # $/km

        payment = base_rate * volume + distance_rate * distance

        # Add randomness (±10%)
        payment *= random.uniform(0.9, 1.1)

        return payment

    def _generate_description(self, volume: float, distance: float) -> str:
        """Generate descriptive text for package."""
        items = [
            "Electronics", "Furniture", "Documents", "Clothing",
            "Hardware", "Books", "Appliances", "Toys",
            "Medical Supplies", "Office Equipment", "Food Items",
            "Auto Parts", "Sports Equipment", "Art Supplies"
        ]

        item = random.choice(items)

        if volume < 2.0:
            size = "Small"
        elif volume < 4.0:
            size = "Medium"
        else:
            size = "Large"

        return f"{size} {item}"
