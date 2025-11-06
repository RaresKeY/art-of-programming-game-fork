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
        font_id = pygame.font.SysFont('arial', 12, bold=True)
        font_info = pygame.font.SysFont('arial', 10)

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
        font_header = pygame.font.SysFont('arial', 12, bold=True)
        font_info = pygame.font.SysFont('arial', 10)

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

    def __init__(self, x: int, y: int, width: int, height: int, modal: bool = False):
        """
        Initialize manual mode manager.

        Args:
            x, y: Position of manual mode panel
            width, height: Dimensions
        """
        self.rect = pygame.Rect(x, y, width, height)
        self.active = False
        self.is_modal = modal

        # All items
        self.all_packages: List[Package] = []
        self.all_vehicles: List[Vehicle] = []

        # UI elements (current page only)
        self.package_cards: List[PackageCard] = []
        self.vehicle_cards: List[VehicleCard] = []
        self.selected_vehicle: Optional[VehicleCard] = None
        self.selected_package: Optional[PackageCard] = None
        self.close_btn = None
        self.plan_btn = None
        self.map_section_rect: Optional[pygame.Rect] = None
        self._map_inner_rect: Optional[pygame.Rect] = None
        self._map_scale: float = 1.0
        self._map_pad_x: float = 0.0
        self._map_pad_y: float = 0.0
        self._map_package_positions: Dict[str, Tuple[int, int]] = {}
        self.delivery_map: Optional[DeliveryMap] = None

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
        self.base_packages_y = 0
        self.base_vehicles_y = 0

        # Instructions
        self.instruction_text = "Select vehicle → Click package (list or mini-map) to assign"

    def update_rect(self, x: int, y: int, width: int, height: int):
        """Update the manual mode panel geometry."""
        self.rect.update(x, y, width, height)

    def setup(self, packages: List[Package], vehicles: List[Vehicle], delivery_map: Optional[DeliveryMap] = None):
        """
        Setup manual mode with current packages and vehicles.

        Args:
            packages: Available packages
            vehicles: Fleet vehicles
            delivery_map: Map reference for scaling preview
        """
        # Store all items
        self.all_packages = packages
        self.all_vehicles = vehicles
        if delivery_map:
            self.delivery_map = delivery_map

        # Reset pagination
        self.package_page = 0
        self.vehicle_page = 0
        self.assignments.clear()

        # Reset selections
        self.selected_package = None
        self.selected_vehicle = None

        # Define layout sections
        header_height = 32
        nav_button_height = 25
        close_btn_width = 110
        close_btn_height = 26
        close_btn_x = int(self.rect.right - close_btn_width - 12)
        close_btn_y = int(self.rect.y + 6)
        self.close_btn = Button(close_btn_x, close_btn_y, close_btn_width, close_btn_height, "Exit Manual")

        # Content area metrics
        top_margin = header_height + 10
        bottom_margin = 10
        btn_y = self.rect.y + self.rect.height - nav_button_height - bottom_margin
        content_top = self.rect.y + top_margin
        content_bottom = btn_y - 10
        content_height = max(140, content_bottom - content_top)

        # Column widths (map | packages | vehicles)
        left_margin = 10
        right_margin = 10
        column_gap = 10
        usable_width = self.rect.width - left_margin - right_margin - 2 * column_gap
        map_width = max(180, int(usable_width * 0.38))
        packages_width = max(160, int(usable_width * 0.32))
        vehicles_width = usable_width - map_width - packages_width

        if vehicles_width < 150:
            deficit = 150 - vehicles_width
            map_width = max(160, map_width - deficit // 2)
            packages_width = max(150, packages_width - deficit // 2)
            vehicles_width = usable_width - map_width - packages_width
            vehicles_width = max(140, vehicles_width)

        self.map_section_rect = pygame.Rect(
            self.rect.x + left_margin,
            content_top,
            map_width,
            content_height
        )

        self.packages_section_rect = pygame.Rect(
            self.map_section_rect.right + column_gap,
            content_top,
            packages_width,
            content_height
        )

        self.vehicles_section_rect = pygame.Rect(
            self.packages_section_rect.right + column_gap,
            content_top,
            vehicles_width,
            content_height
        )

        # Reset map helpers
        self._configure_map_projection()

        # Reset scroll
        self.content_scroll_offset = 0
        self.max_content_scroll = max(0, self.packages_section_rect.height - 260)
        self.base_packages_y = self.packages_section_rect.y
        self.base_vehicles_y = self.vehicles_section_rect.y

        # Create navigation buttons for packages
        btn_w = 70
        btn_h = 22
        pkg_btn_x = self.packages_section_rect.x

        self.pkg_prev_btn = Button(pkg_btn_x, btn_y, btn_w, btn_h, "< Prev", self.prev_package_page)
        self.pkg_next_btn = Button(pkg_btn_x + btn_w + 5, btn_y, btn_w, btn_h, "Next >", self.next_package_page)
        self.assign_btn = Button(pkg_btn_x + 2 * btn_w + 20, btn_y, btn_w + 30, btn_h, "Assign")

        # Create navigation buttons for vehicles
        veh_btn_x = self.vehicles_section_rect.x
        self.veh_prev_btn = Button(veh_btn_x, btn_y, btn_w, btn_h, "< Prev", self.prev_vehicle_page)
        self.veh_next_btn = Button(veh_btn_x + btn_w + 5, btn_y, btn_w, btn_h, "Next >", self.next_vehicle_page)

        # Plan button to finalize manual layout
        plan_btn_width = btn_w + 30
        plan_btn_x = self.rect.right - plan_btn_width - 12
        self.plan_btn = Button(plan_btn_x, btn_y, plan_btn_width, btn_h, "Plan")

        # Build current pages
        self._build_package_page()
        self._build_vehicle_page(delivery_map=self.delivery_map)
        self._update_action_buttons()

    def _configure_map_projection(self):
        """Prepare mini-map projection values based on current layout."""
        self._map_inner_rect = None
        self._map_package_positions = {}

        if not self.delivery_map or not self.map_section_rect:
            return

        inner = self.map_section_rect.inflate(-16, -16)
        inner.width = max(40, inner.width)
        inner.height = max(40, inner.height)
        self._map_inner_rect = inner

        map_width = max(1.0, float(self.delivery_map.width))
        map_height = max(1.0, float(self.delivery_map.height))

        draw_width = inner.width
        draw_height = inner.height
        scale = min(draw_width / map_width, draw_height / map_height)
        self._map_scale = scale

        pad_x = (draw_width - map_width * scale) / 2
        pad_y = (draw_height - map_height * scale) / 2
        self._map_pad_x = pad_x
        self._map_pad_y = pad_y
        self._update_action_buttons()

    def _update_action_buttons(self):
        """Enable/disable action buttons based on current assignments."""
        if self.plan_btn:
            self.plan_btn.enabled = bool(self.assignments)

    def _map_world_to_screen(self, point: Tuple[float, float]) -> Optional[Tuple[int, int]]:
        """Convert map coordinates to mini-map screen coordinates."""
        if not self._map_inner_rect or not self.delivery_map:
            return None

        wx, wy = point
        sx = self._map_inner_rect.x + self._map_pad_x + wx * self._map_scale
        sy = self._map_inner_rect.y + self._map_inner_rect.height - self._map_pad_y - wy * self._map_scale
        return int(sx), int(sy)

    def _get_package_at_screen_pos(self, screen_pos: Tuple[int, int]) -> Optional[Package]:
        """Find the package closest to the given screen position on the mini-map."""
        if not self._map_inner_rect:
            return None

        mouse_x, mouse_y = screen_pos
        if not self._map_inner_rect.collidepoint(mouse_x, mouse_y):
            return None

        closest_pkg = None
        closest_dist_sq = float("inf")

        for pkg in self.all_packages:
            screen_point = self._map_world_to_screen(pkg.destination)
            if not screen_point:
                continue
            dx = screen_point[0] - mouse_x
            dy = screen_point[1] - mouse_y
            dist_sq = dx * dx + dy * dy
            if dist_sq < closest_dist_sq:
                closest_dist_sq = dist_sq
                closest_pkg = pkg

        # Require click to be reasonably close
        if closest_pkg and closest_dist_sq <= 18 * 18:
            return closest_pkg
        return None

    def _ensure_package_visible(self, package: Package):
        """Switch pagination so the given package card is visible."""
        try:
            index = next(i for i, pkg in enumerate(self.all_packages) if pkg.id == package.id)
        except StopIteration:
            return

        page = index // self.packages_per_page
        if page != self.package_page:
            self.package_page = page
            self._build_package_page()

    def _select_package(self, package: Package) -> Optional[PackageCard]:
        """Select the package card corresponding to the given package."""
        self._ensure_package_visible(package)
        selected_card = None

        for card in self.package_cards:
            if card.package.id == package.id:
                card.selected = True
                selected_card = card
            else:
                card.selected = False

        self.selected_package = selected_card
        if selected_card:
            selected_card.selected = True
        return selected_card
    def _build_package_page(self):
        """Build package cards for current page (3x3 grid)."""
        self.package_cards.clear()

        start_idx = self.package_page * self.packages_per_page
        end_idx = min(start_idx + self.packages_per_page, len(self.all_packages))

        # 3x3 grid layout
        cols = 3
        spacing_x = 8
        spacing_y = 10
        available_width = max(90, self.packages_section_rect.width - 16)
        card_width = max(90, (available_width - spacing_x * (cols - 1)) // cols)
        card_height = 70
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
            self._build_vehicle_page(delivery_map=self.delivery_map)

    def next_vehicle_page(self):
        """Go to next vehicle page."""
        total_pages = (len(self.all_vehicles) + self.vehicles_per_page - 1) // self.vehicles_per_page
        if self.vehicle_page < total_pages - 1:
            self.vehicle_page += 1
            self._build_vehicle_page(delivery_map=self.delivery_map)

    def assign_selected(self, delivery_map: Optional[DeliveryMap] = None):
        """
        Assign selected package to selected vehicle.

        Args:
            delivery_map: Delivery map for calculating metrics
        """
        if delivery_map is None:
            delivery_map = self.delivery_map
        if delivery_map is None:
            return False

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
                self._update_action_buttons()

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

        if self.close_btn and self.close_btn.handle_event(event):
            result['action'] = 'close'
            return result

        if self.plan_btn and self.plan_btn.handle_event(event):
            routes = self.get_manual_routes(delivery_map)
            result['action'] = 'plan_routes'
            result['data'] = routes
            return result

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.map_section_rect and self.map_section_rect.collidepoint(event.pos):
                pkg = self._get_package_at_screen_pos(event.pos)
                if pkg:
                    if self.selected_vehicle:
                        assigned_vehicle_id = self.assignments.get(pkg.id)
                        if assigned_vehicle_id and assigned_vehicle_id != self.selected_vehicle.vehicle.id:
                            self._select_package(pkg)
                            result['action'] = 'package_selected'
                            result['data'] = self.selected_package
                            return result

                        if self.assign_package_from_map(pkg, delivery_map):
                            result['action'] = 'package_assigned'
                            result['data'] = {
                                'package': pkg,
                                'vehicle': self.selected_vehicle.vehicle
                            }
                        else:
                            if pkg.id in self.assignments:
                                self._select_package(pkg)
                                result['action'] = 'package_selected'
                                result['data'] = self.selected_package
                            else:
                                result['action'] = 'capacity_exceeded'
                                result['data'] = self.selected_vehicle.vehicle
                        return result
                    else:
                        selected_card = self._select_package(pkg)
                        result['action'] = 'package_selected'
                        result['data'] = selected_card
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
        if self.packages_section_rect:
            self.packages_section_rect.y = self.base_packages_y - self.content_scroll_offset

        if self.vehicles_section_rect:
            self.vehicles_section_rect.y = self.base_vehicles_y - self.content_scroll_offset

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
            self.selected_package = None
            self._update_action_buttons()

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

        if self.is_modal:
            # Dim the background when presented as a modal popup
            overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 180))
            surface.blit(overlay, (0, 0))

            # Draw a subtle shadow behind the panel for depth
            shadow_rect = self.rect.inflate(12, 12)
            shadow_surface = pygame.Surface((shadow_rect.width, shadow_rect.height), pygame.SRCALPHA)
            pygame.draw.rect(shadow_surface, (0, 0, 0, 120), shadow_surface.get_rect(), border_radius=10)
            surface.blit(shadow_surface, (shadow_rect.x, shadow_rect.y))

        # Background panel
        pygame.draw.rect(surface, Colors.PANEL_BG, self.rect, border_radius=8)
        pygame.draw.rect(surface, Colors.BORDER_LIGHT, self.rect, 2, border_radius=8)

        # Title and instructions
        font_title = pygame.font.SysFont('arial', 16, bold=True)
        font_small = pygame.font.SysFont('arial', 11)

        title_text = font_title.render("MANUAL MODE", True, Colors.TEXT_ACCENT)
        surface.blit(title_text, (self.rect.x + 10, self.rect.y + 8))

        inst_text = font_small.render(self.instruction_text, True, Colors.TEXT_SECONDARY)
        surface.blit(inst_text, (self.rect.x + 120, self.rect.y + 12))

        # Show scroll hint if scrollable
        if self.max_content_scroll > 0:
            scroll_hint = font_small.render("(Scroll with mouse wheel)", True, Colors.TEXT_ACCENT)
            surface.blit(scroll_hint, (self.rect.x + self.rect.width - 140, self.rect.y + 12))

        if self.close_btn:
            self.close_btn.render(surface)

        if self.map_section_rect:
            self._render_map_section(surface)

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
        if self.plan_btn:
            self.plan_btn.render(surface)

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

    def _render_map_section(self, surface: pygame.Surface):
        """Render mini-map preview for manual assignment."""
        if not self.map_section_rect or not self.delivery_map:
            return

        pygame.draw.rect(surface, Colors.BG_DARK, self.map_section_rect, border_radius=5)
        pygame.draw.rect(surface, Colors.BORDER_LIGHT, self.map_section_rect, 1, border_radius=5)

        if not self._map_inner_rect:
            return

        pygame.draw.rect(surface, Colors.MAP_BG, self._map_inner_rect, border_radius=6)

        font_header = pygame.font.SysFont('arial', 13, bold=True)
        font_label = pygame.font.SysFont('arial', 10)
        header = font_header.render("MAP PREVIEW", True, Colors.TEXT_ACCENT)
        surface.blit(header, (self.map_section_rect.x + 8, self.map_section_rect.y + 6))

        # Draw depot
        depot_pos = self._map_world_to_screen(self.delivery_map.depot)
        if depot_pos:
            pygame.draw.circle(surface, Colors.DEPOT, depot_pos, 6)
            pygame.draw.circle(surface, Colors.BORDER_LIGHT, depot_pos, 2)
            depot_label = font_label.render("Depot", True, Colors.TEXT_PRIMARY)
            surface.blit(depot_label, (depot_pos[0] - depot_label.get_width() // 2, depot_pos[1] + 8))

        # Draw assigned routes for selected vehicle
        if self.selected_vehicle and self.selected_vehicle.route_stops:
            route_points = [self._map_world_to_screen(stop) for stop in self.selected_vehicle.route_stops]
            route_points = [pt for pt in route_points if pt]
            depot_point = depot_pos
            if depot_point:
                points = [depot_point] + route_points + [depot_point]
            else:
                points = route_points

            if len(points) >= 2:
                pygame.draw.lines(surface, Colors.TEXT_ACCENT, False, points, 2)

        # Draw packages
        self._map_package_positions = {}
        for pkg in self.all_packages:
            pos = self._map_world_to_screen(pkg.destination)
            if not pos:
                continue
            self._map_package_positions[pkg.id] = pos

            assigned_vehicle_id = self.assignments.get(pkg.id)
            is_selected_pkg = self.selected_package and self.selected_package.package.id == pkg.id

            if assigned_vehicle_id:
                if self.selected_vehicle and self.selected_vehicle.vehicle.id == assigned_vehicle_id:
                    color = Colors.TEXT_ACCENT
                else:
                    color = Colors.BORDER_LIGHT
            else:
                color = Colors.PACKAGE_PENDING

            radius = 6 if is_selected_pkg else 4
            pygame.draw.circle(surface, color, pos, radius)
            pygame.draw.circle(surface, Colors.BORDER_DARK, pos, 1)

            if is_selected_pkg:
                pygame.draw.circle(surface, Colors.TEXT_ACCENT, pos, radius + 3, 1)

            label = font_label.render(pkg.id[-3:], True, Colors.TEXT_PRIMARY)
            surface.blit(label, (pos[0] - label.get_width() // 2, pos[1] - 14))

    def _render_packages_section(self, surface: pygame.Surface):
        """Render packages section with pagination."""
        # Section background
        pygame.draw.rect(surface, Colors.BG_DARK, self.packages_section_rect, border_radius=5)
        pygame.draw.rect(surface, Colors.BORDER_LIGHT, self.packages_section_rect, 1, border_radius=5)

        # Section title with page info
        font_header = pygame.font.SysFont('arial', 12, bold=True)
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
        font_header = pygame.font.SysFont('arial', 12, bold=True)
        total_pages = max(1, (len(self.all_vehicles) + self.vehicles_per_page - 1) // self.vehicles_per_page)
        title = font_header.render(
            f"VEHICLES (Page {self.vehicle_page + 1}/{total_pages})",
            True, Colors.TEXT_ACCENT
        )
        surface.blit(title, (self.vehicles_section_rect.x + 5, self.vehicles_section_rect.y - 15))

        # Render vehicle cards
        for veh_card in self.vehicle_cards:
            veh_card.render(surface)
