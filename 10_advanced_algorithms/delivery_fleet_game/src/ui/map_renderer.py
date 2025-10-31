"""
Map renderer for visualizing the delivery area, packages, routes, and vehicles.

This module handles all map-related rendering on the Pygame canvas.
"""

import pygame
import math
from typing import Tuple, List, Optional
from ..models import DeliveryMap, Package, Route, Vehicle
from .constants import *
from .font_utils import render_text


class MapRenderer:
    """
    Renders the delivery map with all game elements.

    Handles coordinate transformation from game world (km) to screen pixels.
    """

    def __init__(self, surface: pygame.Surface, delivery_map: DeliveryMap):
        """
        Initialize map renderer.

        Args:
            surface: Pygame surface to draw on
            delivery_map: Game map with world coordinates
        """
        self.surface = surface
        self.delivery_map = delivery_map

        # Calculate coordinate transformation
        self.world_width = delivery_map.width
        self.world_height = delivery_map.height

        # Available drawing area (with padding)
        self.draw_width = MAP_WIDTH - 2 * MAP_PADDING
        self.draw_height = MAP_HEIGHT - 2 * MAP_PADDING

        # Scale factors
        self.scale_x = self.draw_width / self.world_width
        self.scale_y = self.draw_height / self.world_height
        # Use uniform scale to prevent distortion
        self.scale = min(self.scale_x, self.scale_y)

        # Offset to center the map
        self.offset_x = MAP_PADDING + (self.draw_width - self.world_width * self.scale) / 2
        self.offset_y = MAP_PADDING + (self.draw_height - self.world_height * self.scale) / 2

        # Animation state
        self.pulse_time = 0

    def world_to_screen(self, world_pos: Tuple[float, float]) -> Tuple[int, int]:
        """
        Convert world coordinates (km) to screen pixels.

        Args:
            world_pos: (x, y) in kilometers

        Returns:
            (x, y) in screen pixels
        """
        wx, wy = world_pos
        sx = int(wx * self.scale + self.offset_x)
        # Flip Y axis (screen Y increases downward, world Y increases upward)
        sy = int(MAP_HEIGHT - (wy * self.scale + self.offset_y))
        return (sx, sy)

    def screen_to_world(self, screen_pos: Tuple[int, int]) -> Tuple[float, float]:
        """
        Convert screen pixels to world coordinates (km).

        Args:
            screen_pos: (x, y) in screen pixels

        Returns:
            (x, y) in kilometers
        """
        sx, sy = screen_pos
        wx = (sx - self.offset_x) / self.scale
        wy = (MAP_HEIGHT - sy - self.offset_y) / self.scale
        return (wx, wy)

    def render_map_background(self):
        """Draw map background and grid."""
        # Fill background
        self.surface.fill(Colors.MAP_BG)

        if SHOW_GRID:
            self._draw_grid()

        if SHOW_COORDINATES:
            self._draw_axes()

    def _draw_grid(self):
        """Draw subtle grid lines."""
        # Vertical lines
        for x_km in range(0, int(self.world_width) + 1, 10):
            x_screen, _ = self.world_to_screen((x_km, 0))
            _, y_bottom = self.world_to_screen((0, 0))
            _, y_top = self.world_to_screen((0, self.world_height))
            pygame.draw.line(
                self.surface,
                Colors.GRID,
                (x_screen, y_top),
                (x_screen, y_bottom),
                1
            )

        # Horizontal lines
        for y_km in range(0, int(self.world_height) + 1, 10):
            _, y_screen = self.world_to_screen((0, y_km))
            x_left, _ = self.world_to_screen((0, 0))
            x_right, _ = self.world_to_screen((self.world_width, 0))
            pygame.draw.line(
                self.surface,
                Colors.GRID,
                (x_left, y_screen),
                (x_right, y_screen),
                1
            )

    def _draw_axes(self):
        """Draw coordinate axes labels using JetBrains Mono."""
        for x_km in range(0, int(self.world_width) + 1, 20):
            x_screen, y_screen = self.world_to_screen((x_km, 0))
            text = render_text(f"{x_km}", FontSizes.TINY, Colors.TEXT_SECONDARY)
            self.surface.blit(text, (x_screen - text.get_width() // 2, y_screen + 6))

        for y_km in range(0, int(self.world_height) + 1, 20):
            x_screen, y_screen = self.world_to_screen((0, y_km))
            text = render_text(f"{y_km}", FontSizes.TINY, Colors.TEXT_SECONDARY)
            self.surface.blit(text, (x_screen - text.get_width() - 6, y_screen - text.get_height() // 2))

    def render_depot(self, pulse: bool = True):
        """
        Draw the depot marker at origin.

        Args:
            pulse: Whether to animate pulsing effect
        """
        depot_screen = self.world_to_screen(self.delivery_map.depot)

        # Pulsing effect
        if pulse:
            self.pulse_time += 0.05
            radius = DEPOT_RADIUS + int(3 * math.sin(self.pulse_time))
        else:
            radius = DEPOT_RADIUS

        # Outer glow
        pygame.draw.circle(
            self.surface,
            (255, 220, 0, 100),  # Semi-transparent glow
            depot_screen,
            radius + 5,
            0
        )

        # Main circle
        pygame.draw.circle(
            self.surface,
            Colors.DEPOT,
            depot_screen,
            radius,
            0
        )

        # Inner circle
        pygame.draw.circle(
            self.surface,
            Colors.BG_DARK,
            depot_screen,
            radius - 4,
            0
        )

        text = render_text("DEPOT", FontSizes.SMALL, Colors.TEXT_PRIMARY, bold=True)
        text_rect = text.get_rect(center=(depot_screen[0], depot_screen[1] + radius + 16))
        self.surface.blit(text, text_rect)

    def render_package(self, package: Package, status: str = "pending", hover: bool = False):
        """
        Render a package marker.

        Args:
            package: Package to render
            status: "pending", "in_transit", or "delivered"
            hover: Whether mouse is hovering over package
        """
        pos_screen = self.world_to_screen(package.destination)

        # Choose color based on status
        color_map = {
            "pending": Colors.PACKAGE_PENDING,
            "in_transit": Colors.PACKAGE_IN_TRANSIT,
            "delivered": Colors.PACKAGE_DELIVERED
        }
        color = color_map.get(status, Colors.PACKAGE_PENDING)

        # High priority gets red tint
        if package.priority >= 3:
            color = Colors.PACKAGE_PRIORITY_HIGH

        # Radius based on volume (visual indicator of size)
        base_radius = PACKAGE_RADIUS
        radius = int(base_radius + (package.volume_m3 * 0.5))
        radius = min(radius, 12)  # Cap maximum size

        if hover:
            radius = PACKAGE_HOVER_RADIUS

        # Draw package
        pygame.draw.circle(self.surface, color, pos_screen, radius, 0)
        pygame.draw.circle(self.surface, Colors.BORDER_LIGHT, pos_screen, radius, 2)

    def render_packages(self, packages: List[Package], status_map: dict = None):
        """
        Render all packages.

        Args:
            packages: List of packages to render
            status_map: Dict mapping package IDs to status strings
        """
        for pkg in packages:
            status = status_map.get(pkg.id, "pending") if status_map else "pending"
            self.render_package(pkg, status)

    def render_route(self, route: Route, color: Optional[Tuple[int, int, int]] = None,
                    style: str = "solid"):
        """
        Render a delivery route.

        Args:
            route: Route to render
            color: Line color (uses route color if None)
            style: "solid" or "dashed"
        """
        if not route.stops:
            return

        if color is None:
            # Use cycling color based on vehicle index
            color = Colors.ROUTE_COLORS[hash(route.vehicle.id) % len(Colors.ROUTE_COLORS)]

        stops_screen = [self.world_to_screen(stop) for stop in route.stops]
        depot_screen = self.world_to_screen(self.delivery_map.depot)

        # Draw route: depot → stops → depot
        points = [depot_screen] + stops_screen + [depot_screen]

        # Draw lines
        for i in range(len(points) - 1):
            if style == "dashed":
                self._draw_dashed_line(points[i], points[i + 1], color, 3)
            else:
                pygame.draw.line(self.surface, color, points[i], points[i + 1], 3)

        # Draw direction arrows
        self._draw_route_arrows(points, color)

    def _draw_dashed_line(self, start: Tuple[int, int], end: Tuple[int, int],
                          color: Tuple[int, int, int], width: int, dash_length: int = 10):
        """Draw a dashed line."""
        x1, y1 = start
        x2, y2 = end
        dx = x2 - x1
        dy = y2 - y1
        distance = math.sqrt(dx * dx + dy * dy)

        if distance == 0:
            return

        dashes = int(distance / dash_length)
        for i in range(0, dashes, 2):
            start_ratio = i / dashes
            end_ratio = min((i + 1) / dashes, 1.0)
            dash_start = (int(x1 + dx * start_ratio), int(y1 + dy * start_ratio))
            dash_end = (int(x1 + dx * end_ratio), int(y1 + dy * end_ratio))
            pygame.draw.line(self.surface, color, dash_start, dash_end, width)

    def _draw_route_arrows(self, points: List[Tuple[int, int]],
                           color: Tuple[int, int, int]):
        """Draw small arrows indicating route direction."""
        for i in range(len(points) - 1):
            # Draw arrow at midpoint of each segment
            x1, y1 = points[i]
            x2, y2 = points[i + 1]
            mid_x = (x1 + x2) // 2
            mid_y = (y1 + y2) // 2

            # Calculate angle
            angle = math.atan2(y2 - y1, x2 - x1)

            # Draw small triangle
            arrow_size = 8
            points_arrow = [
                (mid_x + arrow_size * math.cos(angle),
                 mid_y + arrow_size * math.sin(angle)),
                (mid_x + arrow_size * math.cos(angle + 2.5),
                 mid_y + arrow_size * math.sin(angle + 2.5)),
                (mid_x + arrow_size * math.cos(angle - 2.5),
                 mid_y + arrow_size * math.sin(angle - 2.5))
            ]
            pygame.draw.polygon(self.surface, color, points_arrow)

    def render_vehicle(self, vehicle: Vehicle, position: Optional[Tuple[float, float]] = None):
        """
        Render a vehicle marker.

        Args:
            vehicle: Vehicle to render
            position: World position (uses vehicle.current_location if None)
        """
        if position is None:
            position = vehicle.current_location

        pos_screen = self.world_to_screen(position)

        # Draw vehicle as small rectangle (truck shape)
        rect_width = VEHICLE_SIZE * 2
        rect_height = VEHICLE_SIZE
        rect = pygame.Rect(
            pos_screen[0] - rect_width // 2,
            pos_screen[1] - rect_height // 2,
            rect_width,
            rect_height
        )

        pygame.draw.rect(self.surface, Colors.VEHICLE_ACTIVE, rect, 0, border_radius=2)
        pygame.draw.rect(self.surface, Colors.BORDER_DARK, rect, 2, border_radius=2)

        # Vehicle ID label
        text = render_text(vehicle.id[-3:], FontSizes.SMALL, Colors.TEXT_PRIMARY)
        text_rect = text.get_rect(center=(pos_screen[0], pos_screen[1] + rect_height + 8))
        self.surface.blit(text, text_rect)

    def render_legend(self):
        """Render an interactive legend explaining map elements."""
        # Legend box in bottom-left corner
        legend_x = 15
        legend_y = MAP_HEIGHT - 160
        legend_width = 200
        legend_height = 145

        # Background
        legend_rect = pygame.Rect(legend_x, legend_y, legend_width, legend_height)
        pygame.draw.rect(self.surface, Colors.PANEL_BG, legend_rect, border_radius=5)
        pygame.draw.rect(self.surface, Colors.BORDER_LIGHT, legend_rect, 2, border_radius=5)

        # Title
        title = render_text("MAP LEGEND", FontSizes.SUBHEADING, Colors.TEXT_ACCENT, bold=True)
        self.surface.blit(title, (legend_x + 12, legend_y + 10))

        y_offset = 30

        def _legend_text(label: str, y: float):
            txt = render_text(label, FontSizes.SMALL, Colors.TEXT_PRIMARY)
            self.surface.blit(txt, (legend_x + 30, legend_y + y - 6))

        pygame.draw.circle(self.surface, Colors.DEPOT, (legend_x + 15, legend_y + y_offset), 8)
        _legend_text("Depot (home base)", y_offset)
        y_offset += 22

        pygame.draw.circle(self.surface, Colors.PACKAGE_PENDING, (legend_x + 15, legend_y + y_offset), 6)
        _legend_text("Package (pending)", y_offset)
        y_offset += 20

        pygame.draw.circle(self.surface, Colors.PACKAGE_DELIVERED, (legend_x + 15, legend_y + y_offset), 6)
        _legend_text("Package (delivered)", y_offset)
        y_offset += 20

        pygame.draw.circle(self.surface, Colors.PACKAGE_PRIORITY_HIGH, (legend_x + 15, legend_y + y_offset), 6)
        _legend_text("High priority", y_offset)
        y_offset += 22

        pygame.draw.line(self.surface, Colors.ROUTE_COLORS[0], (legend_x + 10, legend_y + y_offset), (legend_x + 20, legend_y + y_offset), 3)
        _legend_text("Delivery route", y_offset)
        y_offset += 22

        veh_rect = pygame.Rect(legend_x + 11, legend_y + y_offset - 4, 10, 8)
        pygame.draw.rect(self.surface, Colors.VEHICLE_ACTIVE, veh_rect, border_radius=1)
        _legend_text("Vehicle", y_offset)

        hint = render_text("Tip: hover for details", FontSizes.SMALL, Colors.TEXT_ACCENT)
        self.surface.blit(hint, (legend_x + 12, legend_y + legend_height - 22))

    def get_package_at_mouse(self, mouse_pos: Tuple[int, int], packages: List[Package]) -> Optional[Package]:
        """
        Check if mouse is hovering over a package.

        Args:
            mouse_pos: Screen coordinates of mouse
            packages: List of packages to check

        Returns:
            Package under mouse, or None
        """
        # Adjust for map offset
        map_mouse_x = mouse_pos[0] - MAP_X
        map_mouse_y = mouse_pos[1] - MAP_Y

        if map_mouse_x < 0 or map_mouse_x > MAP_WIDTH or map_mouse_y < 0 or map_mouse_y > MAP_HEIGHT:
            return None

        for pkg in packages:
            pkg_screen = self.world_to_screen(pkg.destination)
            distance = math.sqrt((pkg_screen[0] - map_mouse_x)**2 + (pkg_screen[1] - map_mouse_y)**2)
            if distance < PACKAGE_HOVER_RADIUS + 2:
                return pkg
        return None

    def get_vehicle_at_mouse(self, mouse_pos: Tuple[int, int], vehicles: List[Vehicle]) -> Optional[Vehicle]:
        """
        Check if mouse is hovering over a vehicle.

        Args:
            mouse_pos: Screen coordinates of mouse
            vehicles: List of vehicles to check

        Returns:
            Vehicle under mouse, or None
        """
        # Adjust for map offset
        map_mouse_x = mouse_pos[0] - MAP_X
        map_mouse_y = mouse_pos[1] - MAP_Y

        if map_mouse_x < 0 or map_mouse_x > MAP_WIDTH or map_mouse_y < 0 or map_mouse_y > MAP_HEIGHT:
            return None

        for veh in vehicles:
            veh_screen = self.world_to_screen(veh.current_location)
            rect_width = VEHICLE_SIZE * 2
            rect_height = VEHICLE_SIZE
            rect = pygame.Rect(
                veh_screen[0] - rect_width // 2,
                veh_screen[1] - rect_height // 2,
                rect_width,
                rect_height
            )
            if rect.collidepoint(map_mouse_x, map_mouse_y):
                return veh
        return None

    def render(self):
        """Full render of the map."""
        self.render_map_background()
        self.render_depot()
