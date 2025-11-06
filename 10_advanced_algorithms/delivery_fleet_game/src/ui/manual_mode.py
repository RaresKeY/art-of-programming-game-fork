"""
Manual Mode Components for Interactive Route Planning.

This module provides interactive UI components that allow users to:
1. Manually assign packages to vehicles
2. Build routes by selecting stops
3. See real-time metrics updates
4. Learn about algorithmic efficiency through hands-on experience
"""

import pygame
import math
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

        # Text - use large fonts with compact spacing
        title_font = pygame.font.SysFont('arial', 30, bold=True)
        value_font = pygame.font.SysFont('arial', 24)
        badge_font = pygame.font.SysFont('arial', 20, bold=True)

        padding = 8
        content_left = self.rect.x + padding
        content_right = self.rect.right - padding
        line_y = self.rect.y + padding

        # ID (shortened)
        id_text = title_font.render(self.package.id[-4:], True, Colors.TEXT_PRIMARY)
        surface.blit(id_text, (content_left, line_y))
        line_y += id_text.get_height() + 6

        # Volume and price on the same row
        volume_text = value_font.render(f"{self.package.volume_m3:.1f} m³", True, Colors.TEXT_SECONDARY)
        surface.blit(volume_text, (content_left, line_y))

        price_text = value_font.render(f"${self.package.payment:.0f}", True, Colors.PROFIT_POSITIVE)
        surface.blit(price_text, (content_right - price_text.get_width(), line_y))
        line_y += value_font.get_height() + 4

        # Priority / rush badges
        badge_x = content_left
        badges_rendered = False
        if self.package.priority >= 3:
            priority_text = badge_font.render(f"P{self.package.priority}", True, Colors.TEXT_ACCENT)
            surface.blit(priority_text, (badge_x, line_y))
            badge_x += priority_text.get_width() + 12
            badges_rendered = True

        if getattr(self.package, 'is_rush', False):
            rush_text = badge_font.render("RUSH", True, Colors.PROFIT_NEGATIVE)
            surface.blit(rush_text, (badge_x, line_y))
            badge_x += rush_text.get_width() + 12
            badges_rendered = True

        if badges_rendered:
            line_y += badge_font.get_height() + 4

        # Assigned indicator
        if self.assigned_vehicle_id:
            assigned_text = badge_font.render(f"Assigned -> {self.assigned_vehicle_id[-4:]}", True, Colors.TEXT_ACCENT)
            surface.blit(assigned_text, (content_left, line_y))


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
        font_header = pygame.font.SysFont('arial', 18, bold=True)
        font_info = pygame.font.SysFont('arial', 14)

        text_x = self.rect.x + 10
        line_y = self.rect.y + 6

        # Line 1: Vehicle name and ID
        name = self.vehicle.vehicle_type.name[:10]
        name_text = font_header.render(f"{name} [{self.vehicle.id[-3:]}]", True, Colors.TEXT_ACCENT)
        surface.blit(name_text, (text_x, line_y))
        line_y += name_text.get_height() + 4

        # Line 2: Capacity and package count inline
        capacity = self.vehicle.vehicle_type.capacity_m3
        current = self.get_current_volume()
        capacity_pct = current / capacity if capacity > 0 else 0

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
        surface.blit(info_text, (text_x, line_y))
        line_y += font_info.get_height() + 2

        # Line 3: Metrics inline (if route exists)
        if self.route_stops:
            profit_color = Colors.PROFIT_POSITIVE if self.total_profit > 0 else Colors.PROFIT_NEGATIVE
            metrics_line = f"D:{self.total_distance:.0f}km  P:${self.total_profit:.0f}"
            metrics_text = font_info.render(metrics_line, True, profit_color)
            surface.blit(metrics_text, (text_x, line_y))
            line_y += font_info.get_height() + 2

        # Capacity bar (aligned to bottom)
        bar_rect = self.capacity_bar.rect
        bar_rect.x = self.rect.x + 10
        bar_rect.y = self.rect.bottom - 34
        bar_rect.width = self.rect.width - 20
        bar_rect.height = 12
        self.capacity_bar.render(surface)

        # Status line anchored near bottom
        status_line = f"Stops: {len(self.route_stops)}" if self.route_stops else "No route yet"
        status_text = font_info.render(status_line, True, Colors.TEXT_SECONDARY)
        status_y = bar_rect.bottom + 4
        surface.blit(status_text, (text_x, status_y))


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
        self.reset_btn = None
        self.map_section_rect: Optional[pygame.Rect] = None
        self._map_inner_rect: Optional[pygame.Rect] = None
        self._map_scale: float = 1.0
        self._map_pad_x: float = 0.0
        self._map_pad_y: float = 0.0
        self._map_package_positions: Dict[str, Tuple[int, int]] = {}
        self.delivery_map: Optional[DeliveryMap] = None
        self.summary_rect: Optional[pygame.Rect] = None
        self.summary_title_font = pygame.font.SysFont('arial', 24, bold=True)
        self.summary_primary_font = pygame.font.SysFont('arial', 18)
        self.summary_secondary_font = pygame.font.SysFont('arial', 15)
        self.section_header_font = pygame.font.SysFont('arial', 16, bold=True)
        self.section_hint_font = pygame.font.SysFont('arial', 13)
        self._package_lookup: Dict[str, Package] = {}
        self.packages_header_height = 42
        self.vehicles_header_height = 32

        # Layout tuning (compact cards, no scrolling)
        self.package_rows_per_page = 2
        self.package_card_height = 112
        self.package_min_card_width = 150
        self.package_spacing_x = 16
        self.package_spacing_y = 14
        self.package_bottom_padding = 18

        self.vehicle_card_height = 100
        self.vehicle_spacing_y = 14
        self.vehicle_bottom_padding = 20

        # Pagination
        self.package_page = 0
        self.vehicle_page = 0
        self.packages_per_page = self.package_rows_per_page * 3  # recalculated per layout
        self.vehicles_per_page = 2

        # Navigation buttons
        self.pkg_prev_btn = None
        self.pkg_next_btn = None
        self.veh_prev_btn = None
        self.veh_next_btn = None

        # Layout sections
        self.packages_section_rect = None
        self.vehicles_section_rect = None

        # Assignment tracking
        self.assignments = {}  # pkg_id -> vehicle_id

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
        self._package_lookup = {pkg.id: pkg for pkg in packages}
        if delivery_map:
            self.delivery_map = delivery_map

        # Reset pagination and selections
        self.package_page = 0
        self.vehicle_page = 0
        self.assignments.clear()
        self.selected_package = None
        self.selected_vehicle = None

        # Layout metrics
        margin_x = 16
        margin_y = 16
        header_height = 52
        nav_button_height = 30
        summary_height = 96
        column_gap = 16
        info_gap = 18

        close_btn_width = 110
        close_btn_height = nav_button_height
        close_btn_x = int(self.rect.right - close_btn_width - margin_x)
        close_btn_y = int(self.rect.y + margin_y // 2)
        self.close_btn = Button(close_btn_x, close_btn_y, close_btn_width, close_btn_height, "Exit Manual")

        content_left = self.rect.x + margin_x
        content_width = self.rect.width - margin_x * 2
        btn_y = self.rect.bottom - nav_button_height - margin_y
        usable_height = self.rect.height - header_height - nav_button_height - margin_y * 2
        summary_top = self.rect.y + header_height
        self.summary_rect = pygame.Rect(content_left, summary_top, content_width, summary_height + 12)

        map_top = self.summary_rect.bottom + 12
        map_width = int(content_width * 0.54)
        info_width = content_width - map_width - column_gap
        if info_width < 220:
            info_width = 220
            map_width = content_width - info_width - column_gap

        info_x = content_left + map_width + column_gap
        packages_height_needed = (
            self.packages_header_height
            + self.package_rows_per_page * self.package_card_height
            + max(0, self.package_rows_per_page - 1) * self.package_spacing_y
            + self.package_bottom_padding
        )
        vehicles_height_needed = (
            self.vehicles_header_height
            + self.vehicles_per_page * self.vehicle_card_height
            + max(0, self.vehicles_per_page - 1) * self.vehicle_spacing_y
            + self.vehicle_bottom_padding
        )
        info_required = packages_height_needed + info_gap + vehicles_height_needed
        map_height = min(usable_height, max(420, info_required))
        self.map_section_rect = pygame.Rect(content_left, map_top, map_width, map_height)

        extra_space = max(0, map_height - info_required)
        packages_top = map_top + extra_space // 2
        vehicles_top = packages_top + packages_height_needed + info_gap

        self.packages_section_rect = pygame.Rect(info_x, packages_top, info_width, packages_height_needed)
        self.vehicles_section_rect = pygame.Rect(info_x, vehicles_top, info_width, vehicles_height_needed)

        # Navigation and action buttons
        section_btn_w = 32
        section_btn_h = 20
        nav_gap = 8

        self.pkg_prev_btn = Button(0, 0, section_btn_w, section_btn_h, "<", self.prev_package_page)
        self.pkg_next_btn = Button(0, 0, section_btn_w, section_btn_h, ">", self.next_package_page)

        self.veh_prev_btn = Button(0, 0, section_btn_w, section_btn_h, "<", self.prev_vehicle_page)
        self.veh_next_btn = Button(0, 0, section_btn_w, section_btn_h, ">", self.next_vehicle_page)

        plan_width = 140
        reset_width = 110
        right_btn_start = self.rect.right - margin_x - plan_width
        self.plan_btn = Button(right_btn_start, btn_y, plan_width, nav_button_height, "Plan Routes")
        self.reset_btn = Button(right_btn_start - reset_width - nav_gap, btn_y, reset_width, nav_button_height, "Clear All")

        # Configure map projection after layout
        self._configure_map_projection()

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

    def _gather_summary_stats(self) -> Dict[str, float]:
        """Compute aggregate statistics for summary display."""
        total_packages = len(self.all_packages)
        assigned_ids = set(self.assignments.keys())
        assigned_packages = [self._package_lookup[pkg_id] for pkg_id in assigned_ids if pkg_id in self._package_lookup]

        assigned_count = len(assigned_packages)
        assigned_volume = sum(pkg.volume_m3 for pkg in assigned_packages)
        assigned_revenue = sum(pkg.payment for pkg in assigned_packages)

        return {
            'total_packages': total_packages,
            'assigned_count': assigned_count,
            'assigned_volume': assigned_volume,
            'assigned_revenue': assigned_revenue,
        }

    def _render_summary(self, surface: pygame.Surface):
        """Render the summary panel at the top of manual mode."""
        if not self.summary_rect:
            return

        pygame.draw.rect(surface, Colors.PANEL_BG, self.summary_rect, border_radius=8)
        pygame.draw.rect(surface, Colors.BORDER_LIGHT, self.summary_rect, 1, border_radius=8)

        stats = self._gather_summary_stats()
        text_x = self.summary_rect.x + 14
        line_y = self.summary_rect.y + 10

        title = self.summary_title_font.render("Manual Planning", True, Colors.TEXT_ACCENT)
        surface.blit(title, (text_x, line_y))
        line_y += title.get_height() + 6

        instruction = self.summary_primary_font.render(
            "Choose a vehicle, then click packages from the list or map.", True, Colors.TEXT_PRIMARY
        )
        surface.blit(instruction, (text_x, line_y))
        line_y += instruction.get_height() + 4

        stats_text = self.summary_secondary_font.render(
            f"Assigned {stats['assigned_count']}/{stats['total_packages']} packages • "
            f"Volume {stats['assigned_volume']:.1f} m³ • Revenue ${stats['assigned_revenue']:,.0f}",
            True,
            Colors.TEXT_SECONDARY,
        )
        surface.blit(stats_text, (text_x, line_y))
        line_y += stats_text.get_height() + 4

        if self.selected_vehicle:
            veh = self.selected_vehicle.vehicle
            current_volume = self.selected_vehicle.get_current_volume()
            capacity = veh.vehicle_type.capacity_m3
            vehicle_line = self.summary_secondary_font.render(
                f"Selected: {veh.vehicle_type.name} {veh.id[-3:]} "
                f"({current_volume:.1f}/{capacity:.1f} m³) • Stops {len(self.selected_vehicle.route_stops)}",
                True,
                Colors.TEXT_PRIMARY,
            )
            surface.blit(vehicle_line, (text_x, line_y))
            line_y += vehicle_line.get_height()
        else:
            hint = self.summary_secondary_font.render(
                "Select a vehicle to begin assigning packages.", True, Colors.TEXT_SECONDARY
            )
            surface.blit(hint, (text_x, line_y))
            line_y += hint.get_height()

        # Bottom padding to keep text away from border
        line_y += 8

    def clear_assignments(self) -> bool:
        """Clear all manual assignments."""
        if not self.assignments:
            return False

        selected_id = self.selected_vehicle.vehicle.id if self.selected_vehicle else None

        self.assignments.clear()
        self.selected_package = None

        # Reset package cards
        for card in self.package_cards:
            card.assigned_vehicle_id = None
            card.selected = False

        # Rebuild vehicle cards to clear metrics
        self._build_vehicle_page(self.delivery_map)

        # Restore vehicle selection if possible
        if selected_id:
            for card in self.vehicle_cards:
                if card.vehicle.id == selected_id:
                    card.selected = True
                    self.selected_vehicle = card
                    break
            else:
                self.selected_vehicle = None
        else:
            self.selected_vehicle = None

        self._build_package_page()
        self._update_action_buttons()
        return True

    def _update_action_buttons(self):
        """Enable/disable action buttons based on current assignments."""
        if self.plan_btn:
            self.plan_btn.enabled = bool(self.assignments)
        if self.reset_btn:
            self.reset_btn.enabled = bool(self.assignments)

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
        """Build package cards for current page."""
        self.package_cards.clear()

        if not self.packages_section_rect:
            return

        spacing_x = self.package_spacing_x
        spacing_y = self.package_spacing_y
        min_card_width = self.package_min_card_width
        rows_per_view = self.package_rows_per_page

        available_width = max(90, self.packages_section_rect.width - 32)
        cols = 3
        while cols > 1:
            potential_width = (available_width - spacing_x * (cols - 1)) // cols
            if potential_width >= min_card_width:
                break
            cols -= 1

        if cols == 1:
            card_width = min(available_width, max(100, available_width))
        else:
            card_width = (available_width - spacing_x * (cols - 1)) // cols

        card_height = self.package_card_height

        # Update pagination based on available columns
        previous_per_page = self.packages_per_page
        self.packages_per_page = max(1, cols * rows_per_view)
        if previous_per_page != self.packages_per_page:
            total_pages = max(1, math.ceil(len(self.all_packages) / self.packages_per_page))
            if self.package_page >= total_pages:
                self.package_page = total_pages - 1

        start_idx = self.package_page * self.packages_per_page
        end_idx = min(start_idx + self.packages_per_page, len(self.all_packages))

        total_width = cols * card_width + spacing_x * (cols - 1)
        start_x = self.packages_section_rect.x + max(16, (self.packages_section_rect.width - total_width) // 2)
        start_y = self.packages_section_rect.y + self.packages_header_height

        for i in range(start_idx, end_idx):
            pkg = self.all_packages[i]
            local_idx = i - start_idx

            row = local_idx // cols
            col = local_idx % cols

            x = start_x + col * (card_width + spacing_x)
            y = start_y + row * (card_height + spacing_y)

            card = PackageCard(pkg, x, y, card_width, card_height)

            if pkg.id in self.assignments:
                card.assigned_vehicle_id = self.assignments[pkg.id]

            self.package_cards.append(card)

        total_pages = max(1, math.ceil(len(self.all_packages) / self.packages_per_page))
        if self.pkg_prev_btn:
            self.pkg_prev_btn.enabled = self.package_page > 0
        if self.pkg_next_btn:
            self.pkg_next_btn.enabled = self.package_page < total_pages - 1

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
        card_width = self.vehicles_section_rect.width - 24
        card_height = self.vehicle_card_height
        spacing_y = self.vehicle_spacing_y
        start_x = self.vehicles_section_rect.x + 12
        start_y = self.vehicles_section_rect.y + self.vehicles_header_height

        for i in range(start_idx, end_idx):
            veh = self.all_vehicles[i]
            local_idx = i - start_idx

            y = start_y + local_idx * (card_height + spacing_y)

            card = VehicleCard(veh, start_x, y, card_width, card_height)

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

        if self.close_btn and self.close_btn.handle_event(event):
            result['action'] = 'close'
            return result

        if self.plan_btn and self.plan_btn.handle_event(event):
            routes = self.get_manual_routes(delivery_map)
            result['action'] = 'plan_routes'
            result['data'] = routes
            return result

        if self.reset_btn and self.reset_btn.handle_event(event):
            cleared = self.clear_assignments()
            result['action'] = 'assignments_cleared'
            result['data'] = cleared
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

        # Handle package card selection
        for pkg_card in self.package_cards:
            if pkg_card.handle_event(event):
                # Deselect other packages
                for other in self.package_cards:
                    if other != pkg_card:
                        other.selected = False

                self.selected_package = pkg_card if pkg_card.selected else None
                self._update_action_buttons()
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
                self._update_action_buttons()
                result['action'] = 'vehicle_selected'
                result['data'] = self.selected_vehicle
                return result

        return result

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

        # Title
        font_title = pygame.font.SysFont('arial', 24, bold=True)
        title_text = font_title.render("MANUAL MODE", True, Colors.TEXT_ACCENT)
        surface.blit(title_text, (self.rect.x + 18, self.rect.y + 10))

        if self.close_btn:
            self.close_btn.render(surface)

        if self.summary_rect:
            self._render_summary(surface)

        if self.map_section_rect:
            self._render_map_section(surface)

        # Render sections
        if self.packages_section_rect:
            self._render_packages_section(surface)

        if self.vehicles_section_rect:
            self._render_vehicles_section(surface)

        # Render primary action buttons
        if self.plan_btn:
            self.plan_btn.render(surface)
        if self.reset_btn:
            self.reset_btn.render(surface)

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

        total_pages = max(1, (len(self.all_packages) + self.packages_per_page - 1) // self.packages_per_page)
        header_text = self.section_header_font.render(
            f"Packages · Page {self.package_page + 1}/{total_pages}",
            True,
            Colors.TEXT_ACCENT,
        )

        header_y = self.packages_section_rect.y + 10
        surface.blit(header_text, (self.packages_section_rect.x + 12, header_y))

        assigned_text = self.section_hint_font.render(
            f"Assigned {len(self.assignments)}", True, Colors.TEXT_SECONDARY
        )
        assigned_x = self.packages_section_rect.right - assigned_text.get_width() - 16
        surface.blit(assigned_text, (assigned_x, header_y))

        if self.pkg_prev_btn and self.pkg_next_btn:
            btn_height = self.pkg_next_btn.rect.height
            header_height = header_text.get_height()
            btn_y = header_y + max(0, (header_height - btn_height) // 2)
            buttons_right = assigned_x - 12
            self.pkg_next_btn.rect.topright = (buttons_right, btn_y)
            self.pkg_prev_btn.rect.topright = (self.pkg_next_btn.rect.left - 8, btn_y)
            self.pkg_prev_btn.render(surface)
            self.pkg_next_btn.render(surface)

        for pkg_card in self.package_cards:
            pkg_card.render(surface)

    def _render_vehicles_section(self, surface: pygame.Surface):
        """Render vehicles section with pagination."""
        # Section background
        pygame.draw.rect(surface, Colors.BG_DARK, self.vehicles_section_rect, border_radius=5)
        pygame.draw.rect(surface, Colors.BORDER_LIGHT, self.vehicles_section_rect, 1, border_radius=5)

        # Section title with page info
        total_pages = max(1, (len(self.all_vehicles) + self.vehicles_per_page - 1) // self.vehicles_per_page)
        title = self.section_header_font.render(
            f"Vehicles · Page {self.vehicle_page + 1}/{total_pages}",
            True,
            Colors.TEXT_ACCENT,
        )
        header_y = self.vehicles_section_rect.y + 10
        surface.blit(title, (self.vehicles_section_rect.x + 12, header_y))

        hint = self.section_hint_font.render(
            "Click to focus a vehicle", True, Colors.TEXT_SECONDARY
        )
        hint_x = self.vehicles_section_rect.right - hint.get_width() - 16
        surface.blit(hint, (hint_x, header_y))

        if self.veh_prev_btn and self.veh_next_btn:
            btn_height = self.veh_next_btn.rect.height
            header_height = title.get_height()
            btn_y = header_y + max(0, (header_height - btn_height) // 2)
            buttons_right = hint_x - 12
            self.veh_next_btn.rect.topright = (buttons_right, btn_y)
            self.veh_prev_btn.rect.topright = (self.veh_next_btn.rect.left - 8, btn_y)
            self.veh_prev_btn.render(surface)
            self.veh_next_btn.render(surface)

        # Render vehicle cards
        for veh_card in self.vehicle_cards:
            veh_card.render(surface)
