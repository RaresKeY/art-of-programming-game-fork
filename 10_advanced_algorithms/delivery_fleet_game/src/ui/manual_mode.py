"""
Manual Mode Components for Interactive Route Planning.

This module provides interactive UI components that allow users to:
1. Manually assign packages to vehicles
2. Build routes by selecting stops
3. See real-time metrics updates
4. Learn about algorithmic efficiency through hands-on experience
"""

import pygame
from typing import List, Optional, Tuple, Dict
from ..models import Package, Vehicle, Route
from ..models.map import DeliveryMap
from .constants import *
from .components import Button, ProgressBar


class PackageCard:
    """
    Compact, clickable package card.
    Shows only essential info: ID, volume, price.
    """

    def __init__(self, package: Package, x: int, y: int, width: int = 100, height: int = 65):
        """
        Initialize package card.

        Args:
            package: The package data
            x, y: Position
            width, height: Dimensions (very compact)
        """
        self.package = package
        self.rect = pygame.Rect(x, y, width, height)
        self.hovered = False
        self.selected = False
        self.assigned_vehicle_id = None

    def handle_event(self, event: pygame.event.Event) -> bool:
        """
        Handle mouse events.

        Returns:
            True if clicked
        """
        if event.type == pygame.MOUSEMOTION:
            self.hovered = self.rect.collidepoint(event.pos)

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.hovered:
                self.selected = not self.selected
                return True

        return False

    def render(self, surface: pygame.Surface):
        """Render the package card (ultra-compact)."""
        # Background color
        if self.package.priority >= 3:
            bg_color = Colors.PACKAGE_PRIORITY_HIGH
        else:
            bg_color = Colors.PACKAGE_PENDING

        # Dim if assigned
        if self.assigned_vehicle_id:
            bg_color = tuple(c // 2 for c in bg_color)

        pygame.draw.rect(surface, bg_color, self.rect, border_radius=4)

        # Border (thicker if selected)
        if self.selected:
            border_color = Colors.TEXT_ACCENT
            border_width = 3
        elif self.hovered:
            border_color = Colors.TEXT_ACCENT
            border_width = 2
        else:
            border_color = Colors.BORDER_LIGHT
            border_width = 1

        pygame.draw.rect(surface, border_color, self.rect, border_width, border_radius=4)

        # Text - very compact
        font_id = pygame.font.SysFont('arial', 9, bold=True)
        font_info = pygame.font.SysFont('arial', 8)

        # ID (shortened)
        id_text = font_id.render(self.package.id[-4:], True, Colors.TEXT_PRIMARY)
        surface.blit(id_text, (self.rect.x + 5, self.rect.y + 4))

        # Volume
        vol_text = font_info.render(f"{self.package.volume_m3:.1f}m³", True, Colors.TEXT_SECONDARY)
        surface.blit(vol_text, (self.rect.x + 5, self.rect.y + 18))

        # Price
        price_text = font_info.render(f"${self.package.payment:.0f}", True, Colors.PROFIT_POSITIVE)
        surface.blit(price_text, (self.rect.x + 5, self.rect.y + 30))

        # Priority badge
        if self.package.priority >= 3:
            badge_text = font_info.render(f"P{self.package.priority}", True, Colors.TEXT_ACCENT)
            surface.blit(badge_text, (self.rect.x + 5, self.rect.y + 42))

        if getattr(self.package, 'is_rush', False):
            rush_text = font_info.render("RUSH", True, Colors.PROFIT_NEGATIVE)
            surface.blit(rush_text, (self.rect.x + 50, self.rect.y + 42))

        # Assigned indicator
        if self.assigned_vehicle_id:
            assigned_text = font_info.render(f"→V{self.assigned_vehicle_id[-2:]}", True, Colors.TEXT_ACCENT)
            surface.blit(assigned_text, (self.rect.x + 5, self.rect.y + 54))


class VehicleCard:
    """
    Compact, clickable vehicle card.
    Shows vehicle info inline with capacity bar.
    """

    def __init__(self, vehicle: Vehicle, x: int, y: int, width: int = 220, height: int = 90):
        """
        Initialize vehicle card.

        Args:
            vehicle: The vehicle data
            x, y: Position
            width, height: Dimensions (compact inline layout)
        """
        self.vehicle = vehicle
        self.rect = pygame.Rect(x, y, width, height)
        self.assigned_packages: List[Package] = []
        self.route_stops: List[Tuple[float, float]] = []
        self.hovered = False
        self.selected = False

        # Create capacity bar
        self.capacity_bar = ProgressBar(x + 8, y + 55, width - 16, 10)

        # Metrics
        self.total_distance = 0.0
        self.total_cost = 0.0
        self.total_revenue = 0.0
        self.total_profit = 0.0

    def get_current_volume(self) -> float:
        """Get total volume of assigned packages."""
        return sum(pkg.volume_m3 for pkg in self.assigned_packages)

    def can_add_package(self, package: Package) -> bool:
        """Check if package can be added without exceeding capacity."""
        return self.get_current_volume() + package.volume_m3 <= self.vehicle.vehicle_type.capacity_m3

    def add_package(self, package: Package) -> bool:
        """
        Add package to vehicle if capacity allows.

        Returns:
            True if package was added
        """
        if self.can_add_package(package):
            self.assigned_packages.append(package)
            self._update_capacity_bar()
            return True
        return False

    def remove_package(self, package: Package):
        """Remove package from vehicle."""
        if package in self.assigned_packages:
            self.assigned_packages.remove(package)
            self._update_capacity_bar()

    def _update_capacity_bar(self):
        """Update capacity bar based on current load."""
        capacity = self.vehicle.vehicle_type.capacity_m3
        current = self.get_current_volume()
        progress = current / capacity if capacity > 0 else 0
        self.capacity_bar.set_progress(progress)

    def calculate_metrics(self, delivery_map: DeliveryMap):
        """
        Calculate route metrics based on assigned packages and stops.

        Args:
            delivery_map: Map for distance calculations
        """
        if not self.route_stops:
            self.total_distance = 0.0
            self.total_cost = 0.0
            self.total_revenue = sum(pkg.payment for pkg in self.assigned_packages)
            self.total_profit = self.total_revenue
            return

        # Calculate distance
        distance = 0.0
        depot = delivery_map.depot

        # Depot to first stop
        distance += delivery_map.distance(depot, self.route_stops[0])

        # Between stops
        for i in range(len(self.route_stops) - 1):
            distance += delivery_map.distance(self.route_stops[i], self.route_stops[i + 1])

        # Last stop to depot
        distance += delivery_map.distance(self.route_stops[-1], depot)

        self.total_distance = distance
        self.total_cost = self.vehicle.calculate_trip_cost(distance)
        self.total_revenue = sum(pkg.payment for pkg in self.assigned_packages)
        self.total_profit = self.total_revenue - self.total_cost

    def handle_event(self, event: pygame.event.Event) -> bool:
        """
        Handle mouse events.

        Returns:
            True if card was clicked
        """
        if event.type == pygame.MOUSEMOTION:
            self.hovered = self.rect.collidepoint(event.pos)

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.hovered:
                self.selected = not self.selected
                return True

        return False

    def render(self, surface: pygame.Surface):
        """Render the vehicle card (compact inline format)."""
        # Background
        bg_color = Colors.PANEL_BG if not self.selected else Colors.BUTTON_HOVER
        pygame.draw.rect(surface, bg_color, self.rect, border_radius=4)

        # Border
        if self.selected:
            border_color = Colors.TEXT_ACCENT
            border_width = 3
        elif self.hovered:
            border_color = Colors.TEXT_ACCENT
            border_width = 2
        else:
            border_color = Colors.BORDER_LIGHT
            border_width = 1

        pygame.draw.rect(surface, border_color, self.rect, border_width, border_radius=4)

        # Fonts
        font_header = pygame.font.SysFont('arial', 10, bold=True)
        font_info = pygame.font.SysFont('arial', 8)

        # Line 1: Vehicle name and ID
        name = self.vehicle.vehicle_type.name[:10]  # Max 10 chars
        name_text = font_header.render(f"{name} [{self.vehicle.id[-3:]}]", True, Colors.TEXT_ACCENT)
        surface.blit(name_text, (self.rect.x + 6, self.rect.y + 5))

        # Line 2: Capacity and package count inline
        capacity = self.vehicle.vehicle_type.capacity_m3
        current = self.get_current_volume()
        capacity_pct = current / capacity if capacity > 0 else 0

        # Color based on capacity usage
        if capacity_pct > 1.0:
            capacity_color = Colors.PROFIT_NEGATIVE
        elif capacity_pct > 0.8:
            capacity_color = Colors.TEXT_ACCENT
        else:
            capacity_color = Colors.TEXT_SECONDARY

        info_line = f"{current:.1f}/{capacity:.1f}m³  •  {len(self.assigned_packages)} pkg"
        if capacity_pct > 1.0:
            info_line += "  ⚠️"

        info_text = font_info.render(info_line, True, capacity_color)
        surface.blit(info_text, (self.rect.x + 6, self.rect.y + 20))

        # Line 3: Metrics inline (if route exists)
        if self.route_stops:
            profit_color = Colors.PROFIT_POSITIVE if self.total_profit > 0 else Colors.PROFIT_NEGATIVE
            metrics_line = f"D:{self.total_distance:.0f}km  P:${self.total_profit:.0f}"
            metrics_text = font_info.render(metrics_line, True, profit_color)
            surface.blit(metrics_text, (self.rect.x + 6, self.rect.y + 34))

        # Capacity bar
        self.capacity_bar.render(surface)

        # Status line
        status_line = f"Stops: {len(self.route_stops)}" if self.route_stops else "No route yet"
        status_text = font_info.render(status_line, True, Colors.TEXT_SECONDARY)
        surface.blit(status_text, (self.rect.x + 6, self.rect.y + 70))


class ManualModeManager:
    """
    Manages the manual mode interface and interactions.

    Uses pagination for packages and vehicles to avoid UI flooding.
    """

    def __init__(self, x: int, y: int, width: int, height: int):
        """
        Initialize manual mode manager.

        Args:
            x, y: Position of manual mode panel
            width, height: Dimensions
        """
        self.rect = pygame.Rect(x, y, width, height)
        self.active = False

        # All items
        self.all_packages: List[Package] = []
        self.all_vehicles: List[Vehicle] = []

        # UI elements (current page only)
        self.package_cards: List[PackageCard] = []
        self.vehicle_cards: List[VehicleCard] = []
        self.selected_vehicle: Optional[VehicleCard] = None
        self.selected_package: Optional[PackageCard] = None

        # Pagination
        self.package_page = 0
        self.vehicle_page = 0
        self.packages_per_page = 9  # 3x3 grid
        self.vehicles_per_page = 2

        # Navigation buttons
        self.pkg_prev_btn = None
        self.pkg_next_btn = None
        self.veh_prev_btn = None
        self.veh_next_btn = None
        self.assign_btn = None  # Assign selected package to selected vehicle

        # Layout sections
        self.packages_section_rect = None
        self.vehicles_section_rect = None

        # Assignment tracking
        self.assignments = {}  # pkg_id -> vehicle_id

        # Panel scrolling (for when content is taller than available height)
        self.content_scroll_offset = 0
        self.max_content_scroll = 0

        # Instructions
        self.instruction_text = "Select vehicle → Click package (here or on map) to assign"

    def setup(self, packages: List[Package], vehicles: List[Vehicle]):
        """
        Setup manual mode with current packages and vehicles.

        Args:
            packages: Available packages
            vehicles: Fleet vehicles
        """
        # Store all items
        self.all_packages = packages
        self.all_vehicles = vehicles

        # Reset pagination
        self.package_page = 0
        self.vehicle_page = 0
        self.assignments.clear()

        # Define layout sections
        header_height = 30
        nav_button_height = 25

        # Calculate ideal content height
        ideal_pkg_section_height = 250  # Ideal height for 3 rows of packages
        ideal_nav_height = nav_button_height

        # Total ideal height
        ideal_total_height = header_height + ideal_pkg_section_height + ideal_nav_height

        # Available height
        available_content_height = self.rect.height - header_height - nav_button_height - 10

        # If ideal is larger than available, we'll need scrolling
        self.max_content_scroll = max(0, ideal_pkg_section_height - available_content_height)

        # Store base positions (before scroll offset)
        self.base_section_y = self.rect.y + header_height

        # Packages section (left side, ~65% width)
        pkg_section_width = int(self.rect.width * 0.65)
        self.packages_section_rect = pygame.Rect(
            self.rect.x + 5,
            self.base_section_y,
            pkg_section_width - 10,
            min(ideal_pkg_section_height, available_content_height)
        )

        # Vehicles section (right side, ~35% width)
        veh_section_width = int(self.rect.width * 0.35)
        self.vehicles_section_rect = pygame.Rect(
            self.rect.x + pkg_section_width + 5,
            self.base_section_y,
            veh_section_width - 10,
            min(ideal_pkg_section_height, available_content_height)
        )

        # Reset scroll
        self.content_scroll_offset = 0

        # Create navigation buttons for packages
        btn_y = self.rect.y + self.rect.height - nav_button_height
        btn_w = 60
        btn_h = 20
        pkg_btn_x = self.packages_section_rect.x

        self.pkg_prev_btn = Button(pkg_btn_x, btn_y, btn_w, btn_h, "< Prev", self.prev_package_page)
        self.pkg_next_btn = Button(pkg_btn_x + btn_w + 5, btn_y, btn_w, btn_h, "Next >", self.next_package_page)
        self.assign_btn = Button(pkg_btn_x + 2 * btn_w + 15, btn_y, btn_w + 20, btn_h, "Assign", self.assign_selected)

        # Create navigation buttons for vehicles
        veh_btn_x = self.vehicles_section_rect.x
        self.veh_prev_btn = Button(veh_btn_x, btn_y, btn_w, btn_h, "< Prev", self.prev_vehicle_page)
        self.veh_next_btn = Button(veh_btn_x + btn_w + 5, btn_y, btn_w, btn_h, "Next >", self.next_vehicle_page)

        # Build current pages
        self._build_package_page()
        self._build_vehicle_page(delivery_map=None)  # No delivery_map during setup

    def _build_package_page(self):
        """Build package cards for current page (3x3 grid)."""
        self.package_cards.clear()

        start_idx = self.package_page * self.packages_per_page
        end_idx = min(start_idx + self.packages_per_page, len(self.all_packages))

        # 3x3 grid layout
        card_width = 105
        card_height = 70
        spacing_x = 10
        spacing_y = 10
        start_x = self.packages_section_rect.x + 8
        start_y = self.packages_section_rect.y + 8

        for i in range(start_idx, end_idx):
            pkg = self.all_packages[i]
            local_idx = i - start_idx

            row = local_idx // 3
            col = local_idx % 3

            x = start_x + col * (card_width + spacing_x)
            y = start_y + row * (card_height + spacing_y)

            card = PackageCard(pkg, x, y, card_width, card_height)
            card.base_y = y  # Store base position for scrolling

            # Check if assigned
            if pkg.id in self.assignments:
                card.assigned_vehicle_id = self.assignments[pkg.id]

            self.package_cards.append(card)

        # Update button states
        total_pages = (len(self.all_packages) + self.packages_per_page - 1) // self.packages_per_page
        if self.pkg_prev_btn:
            self.pkg_prev_btn.enabled = self.package_page > 0
        if self.pkg_next_btn:
            self.pkg_next_btn.enabled = self.package_page < total_pages - 1

        # Apply scroll offset
        self._apply_scroll_offset()

    def _build_vehicle_page(self, delivery_map: Optional[DeliveryMap] = None):
        """
        Build vehicle cards for current page (2 vehicles).

        Args:
            delivery_map: Optional delivery map for calculating metrics
        """
        self.vehicle_cards.clear()

        start_idx = self.vehicle_page * self.vehicles_per_page
        end_idx = min(start_idx + self.vehicles_per_page, len(self.all_vehicles))

        # Vertical stacking
        card_width = self.vehicles_section_rect.width - 16
        card_height = 95
        spacing_y = 10
        start_x = self.vehicles_section_rect.x + 8
        start_y = self.vehicles_section_rect.y + 8

        for i in range(start_idx, end_idx):
            veh = self.all_vehicles[i]
            local_idx = i - start_idx

            y = start_y + local_idx * (card_height + spacing_y)

            card = VehicleCard(veh, start_x, y, card_width, card_height)
            card.base_y = y  # Store base position for scrolling

            # Assign packages properly using add_package method
            for pkg_id, veh_id in self.assignments.items():
                if veh_id == veh.id:
                    # Find package
                    pkg = next((p for p in self.all_packages if p.id == pkg_id), None)
                    if pkg:
                        card.add_package(pkg)  # Use add_package to update capacity bar
                        # Add destination to route if not already there
                        if pkg.destination not in card.route_stops:
                            card.route_stops.append(pkg.destination)

            # Calculate metrics if we have a delivery map and route stops
            if delivery_map and card.route_stops:
                card.calculate_metrics(delivery_map)

            # Keep selected state if this is the selected vehicle
            if self.selected_vehicle and self.selected_vehicle.vehicle.id == veh.id:
                card.selected = True
                self.selected_vehicle = card  # Update reference to new card

            self.vehicle_cards.append(card)

        # Update button states
        total_pages = (len(self.all_vehicles) + self.vehicles_per_page - 1) // self.vehicles_per_page
        if self.veh_prev_btn:
            self.veh_prev_btn.enabled = self.vehicle_page > 0
        if self.veh_next_btn:
            self.veh_next_btn.enabled = self.vehicle_page < total_pages - 1

        # Apply scroll offset
        self._apply_scroll_offset()

    def prev_package_page(self):
        """Go to previous package page."""
        if self.package_page > 0:
            self.package_page -= 1
            self._build_package_page()

    def next_package_page(self):
        """Go to next package page."""
        total_pages = (len(self.all_packages) + self.packages_per_page - 1) // self.packages_per_page
        if self.package_page < total_pages - 1:
            self.package_page += 1
            self._build_package_page()

    def prev_vehicle_page(self):
        """Go to previous vehicle page."""
        if self.vehicle_page > 0:
            self.vehicle_page -= 1
            self._build_vehicle_page(delivery_map=None)

    def next_vehicle_page(self):
        """Go to next vehicle page."""
        total_pages = (len(self.all_vehicles) + self.vehicles_per_page - 1) // self.vehicles_per_page
        if self.vehicle_page < total_pages - 1:
            self.vehicle_page += 1
            self._build_vehicle_page(delivery_map=None)

    def assign_selected(self, delivery_map: DeliveryMap):
        """
        Assign selected package to selected vehicle.

        Args:
            delivery_map: Delivery map for calculating metrics
        """
        if self.selected_package and self.selected_vehicle:
            pkg = self.selected_package.package
            veh = self.selected_vehicle.vehicle

            # Check if already assigned
            if pkg.id in self.assignments:
                return False

            # Check capacity
            if self.selected_vehicle.can_add_package(pkg):
                # Add to assignments
                self.assignments[pkg.id] = veh.id

                # Add package to vehicle card
                self.selected_vehicle.add_package(pkg)

                # Add destination to route stops
                if pkg.destination not in self.selected_vehicle.route_stops:
                    self.selected_vehicle.route_stops.append(pkg.destination)

                # Calculate metrics
                self.selected_vehicle.calculate_metrics(delivery_map)

                # Update UI
                self.selected_package.assigned_vehicle_id = veh.id
                self.selected_package.selected = False
                self.selected_package = None

                # Rebuild package page to show assignment
                self._build_package_page()

                return True
            else:
                # Capacity exceeded
                return False

        return False

    def handle_event(self, event: pygame.event.Event, delivery_map: DeliveryMap) -> Dict:
        """
        Handle events for manual mode interactions.

        Args:
            event: Pygame event
            delivery_map: Map for calculations

        Returns:
            Dictionary with action results
        """
        result = {'action': None, 'data': None}

        # Handle mouse wheel scrolling over the manual mode panel
        if event.type == pygame.MOUSEWHEEL:
            mouse_pos = pygame.mouse.get_pos()
            if self.rect.collidepoint(mouse_pos):
                scroll_amount = event.y * 20  # Scroll speed
                self.content_scroll_offset = max(0, min(self.max_content_scroll,
                                                        self.content_scroll_offset - scroll_amount))
                # Apply the new scroll offset
                self._apply_scroll_offset()
                return result

        # Handle navigation buttons
        if self.pkg_prev_btn and self.pkg_prev_btn.handle_event(event):
            return result
        if self.pkg_next_btn and self.pkg_next_btn.handle_event(event):
            return result
        if self.veh_prev_btn and self.veh_prev_btn.handle_event(event):
            return result
        if self.veh_next_btn and self.veh_next_btn.handle_event(event):
            return result

        # Handle assign button
        if self.assign_btn and self.assign_btn.handle_event(event):
            if self.selected_package and self.selected_vehicle:
                # Store references before they get cleared
                pkg = self.selected_package.package
                veh = self.selected_vehicle.vehicle

                if self.assign_selected(delivery_map):
                    result['action'] = 'package_assigned'
                    result['data'] = {
                        'package': pkg,
                        'vehicle': veh
                    }
                else:
                    result['action'] = 'capacity_exceeded'
                    result['data'] = veh
            return result

        # Handle package card selection
        for pkg_card in self.package_cards:
            if pkg_card.handle_event(event):
                # Deselect other packages
                for other in self.package_cards:
                    if other != pkg_card:
                        other.selected = False

                self.selected_package = pkg_card if pkg_card.selected else None
                result['action'] = 'package_selected'
                result['data'] = self.selected_package
                return result

        # Handle vehicle card selection
        for veh_card in self.vehicle_cards:
            if veh_card.handle_event(event):
                # Deselect others
                for other in self.vehicle_cards:
                    if other != veh_card:
                        other.selected = False

                self.selected_vehicle = veh_card if veh_card.selected else None
                result['action'] = 'vehicle_selected'
                result['data'] = self.selected_vehicle
                return result

        return result

    def _apply_scroll_offset(self):
        """Apply the current scroll offset to all content."""
        # Update section positions
        if self.packages_section_rect and hasattr(self, 'base_section_y'):
            self.packages_section_rect.y = self.base_section_y - self.content_scroll_offset

        if self.vehicles_section_rect and hasattr(self, 'base_section_y'):
            self.vehicles_section_rect.y = self.base_section_y - self.content_scroll_offset

        # Update package card positions
        for card in self.package_cards:
            if hasattr(card, 'base_y'):
                card.rect.y = card.base_y - self.content_scroll_offset

        # Update vehicle card positions and their capacity bars
        for card in self.vehicle_cards:
            if hasattr(card, 'base_y'):
                card.rect.y = card.base_y - self.content_scroll_offset
                # Update capacity bar position too
                card.capacity_bar.rect.y = card.rect.y + 55

    def assign_package_from_map(self, package: Package, delivery_map: DeliveryMap) -> bool:
        """
        Assign a package clicked on the map to the selected vehicle.

        Args:
            package: Package to assign
            delivery_map: Delivery map for calculating metrics

        Returns:
            True if assignment was successful
        """
        if not self.selected_vehicle:
            return False

        # Check if package is already assigned
        if package.id in self.assignments:
            return False  # Already assigned

        if self.selected_vehicle.can_add_package(package):
            # Add to assignments
            self.assignments[package.id] = self.selected_vehicle.vehicle.id

            # Add package to selected vehicle card
            self.selected_vehicle.add_package(package)

            # Add destination to route stops if not already there
            if package.destination not in self.selected_vehicle.route_stops:
                self.selected_vehicle.route_stops.append(package.destination)

            # Calculate metrics for the updated route
            self.selected_vehicle.calculate_metrics(delivery_map)

            # Update package cards to show assignment
            self._build_package_page()

            return True

        return False

    def add_stop_to_selected_vehicle(self, location: Tuple[float, float], delivery_map: DeliveryMap) -> bool:
        """
        Add a stop to the currently selected vehicle's route.

        Args:
            location: (x, y) coordinates of the stop
            delivery_map: Map for calculations

        Returns:
            True if stop was added
        """
        if not self.selected_vehicle:
            return False

        # Check if this location corresponds to an assigned package
        valid_locations = {pkg.destination for pkg in self.selected_vehicle.assigned_packages}

        if location in valid_locations:
            if location not in self.selected_vehicle.route_stops:
                self.selected_vehicle.route_stops.append(location)
                self.selected_vehicle.calculate_metrics(delivery_map)
                return True

        return False

    def get_all_vehicle_routes_for_rendering(self, delivery_map: DeliveryMap) -> List[Tuple[Vehicle, List[Package], List[Tuple[float, float]]]]:
        """
        Get route data for ALL vehicles (not just current page) for rendering on map.

        Returns:
            List of (vehicle, packages, stops) tuples
        """
        routes_data = []

        for veh in self.all_vehicles:
            # Get all packages assigned to this vehicle
            assigned_pkgs = []
            route_stops = []

            for pkg_id, veh_id in self.assignments.items():
                if veh_id == veh.id:
                    pkg = next((p for p in self.all_packages if p.id == pkg_id), None)
                    if pkg:
                        assigned_pkgs.append(pkg)
                        if pkg.destination not in route_stops:
                            route_stops.append(pkg.destination)

            if assigned_pkgs and route_stops:
                routes_data.append((veh, assigned_pkgs, route_stops))

        return routes_data

    def get_manual_routes(self, delivery_map: DeliveryMap) -> List[Route]:
        """
        Build Route objects from manual assignments for ALL vehicles.

        Args:
            delivery_map: Map for distance and cost calculations

        Returns:
            List of manually created routes
        """
        routes = []

        for veh in self.all_vehicles:
            # Get all packages assigned to this vehicle
            assigned_pkgs = []
            route_stops = []

            for pkg_id, veh_id in self.assignments.items():
                if veh_id == veh.id:
                    pkg = next((p for p in self.all_packages if p.id == pkg_id), None)
                    if pkg:
                        assigned_pkgs.append(pkg)
                        if pkg.destination not in route_stops:
                            route_stops.append(pkg.destination)

            if assigned_pkgs and route_stops:
                # Create route
                from ..models.route import Route
                route = Route(
                    vehicle=veh,
                    packages=assigned_pkgs.copy(),
                    stops=route_stops.copy(),
                    delivery_map=delivery_map
                )
                routes.append(route)

        return routes

    def render(self, surface: pygame.Surface):
        """Render the manual mode interface."""
        if not self.active:
            return

        # Background panel
        pygame.draw.rect(surface, Colors.PANEL_BG, self.rect, border_radius=8)
        pygame.draw.rect(surface, Colors.BORDER_LIGHT, self.rect, 2, border_radius=8)

        # Title and instructions
        font_title = pygame.font.SysFont('arial', 12, bold=True)
        font_small = pygame.font.SysFont('arial', 8)

        title_text = font_title.render("MANUAL MODE", True, Colors.TEXT_ACCENT)
        surface.blit(title_text, (self.rect.x + 10, self.rect.y + 8))

        inst_text = font_small.render(self.instruction_text, True, Colors.TEXT_SECONDARY)
        surface.blit(inst_text, (self.rect.x + 120, self.rect.y + 12))

        # Show scroll hint if scrollable
        if self.max_content_scroll > 0:
            scroll_hint = font_small.render("(Scroll with mouse wheel)", True, Colors.TEXT_ACCENT)
            surface.blit(scroll_hint, (self.rect.x + self.rect.width - 140, self.rect.y + 12))

        # Render sections
        if self.packages_section_rect:
            self._render_packages_section(surface)

        if self.vehicles_section_rect:
            self._render_vehicles_section(surface)

        # Render navigation buttons
        if self.pkg_prev_btn:
            self.pkg_prev_btn.render(surface)
        if self.pkg_next_btn:
            self.pkg_next_btn.render(surface)
        if self.assign_btn:
            self.assign_btn.render(surface)
        if self.veh_prev_btn:
            self.veh_prev_btn.render(surface)
        if self.veh_next_btn:
            self.veh_next_btn.render(surface)

        # Render scroll indicators
        if self.max_content_scroll > 0:
            # Scrollbar on right side
            scrollbar_x = self.rect.right - 8
            scrollbar_top = self.rect.y + 30
            scrollbar_height = self.rect.height - 60

            # Track
            track_rect = pygame.Rect(scrollbar_x, scrollbar_top, 6, scrollbar_height)
            pygame.draw.rect(surface, Colors.BG_DARK, track_rect, border_radius=3)

            # Thumb (indicates current position)
            if self.max_content_scroll > 0:
                thumb_height = max(20, int(scrollbar_height * (scrollbar_height / (scrollbar_height + self.max_content_scroll))))
                thumb_y = scrollbar_top + int((scrollbar_height - thumb_height) * (self.content_scroll_offset / self.max_content_scroll))
                thumb_rect = pygame.Rect(scrollbar_x, thumb_y, 6, thumb_height)
                pygame.draw.rect(surface, Colors.TEXT_ACCENT, thumb_rect, border_radius=3)

    def _render_packages_section(self, surface: pygame.Surface):
        """Render packages section with pagination."""
        # Section background
        pygame.draw.rect(surface, Colors.BG_DARK, self.packages_section_rect, border_radius=5)
        pygame.draw.rect(surface, Colors.BORDER_LIGHT, self.packages_section_rect, 1, border_radius=5)

        # Section title with page info
        font_header = pygame.font.SysFont('arial', 10, bold=True)
        total_pages = max(1, (len(self.all_packages) + self.packages_per_page - 1) // self.packages_per_page)
        # title = font_header.render(
        #     f"PACKAGES (Page {self.package_page + 1}/{total_pages})",
        #     True, Colors.TEXT_ACCENT
        # )
        # surface.blit(title, (self.packages_section_rect.x + 5, self.packages_section_rect.y - 15))

        # Render package cards
        for pkg_card in self.package_cards:
            pkg_card.render(surface)

    def _render_vehicles_section(self, surface: pygame.Surface):
        """Render vehicles section with pagination."""
        # Section background
        pygame.draw.rect(surface, Colors.BG_DARK, self.vehicles_section_rect, border_radius=5)
        pygame.draw.rect(surface, Colors.BORDER_LIGHT, self.vehicles_section_rect, 1, border_radius=5)

        # Section title with page info
        font_header = pygame.font.SysFont('arial', 10, bold=True)
        total_pages = max(1, (len(self.all_vehicles) + self.vehicles_per_page - 1) // self.vehicles_per_page)
        title = font_header.render(
            f"VEHICLES (Page {self.vehicle_page + 1}/{total_pages})",
            True, Colors.TEXT_ACCENT
        )
        surface.blit(title, (self.vehicles_section_rect.x + 5, self.vehicles_section_rect.y - 15))

        # Render vehicle cards
        for veh_card in self.vehicle_cards:
            veh_card.render(surface)
