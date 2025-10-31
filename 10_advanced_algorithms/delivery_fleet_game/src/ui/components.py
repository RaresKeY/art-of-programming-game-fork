"""
UI Components for Pygame interface.

Includes buttons, panels, text displays, and other interactive elements.
"""

import pygame
from typing import Tuple, Optional, Callable
from .constants import *


class Button:
    """
    Interactive button component.

    Handles hover states, clicks, and visual feedback.
    """

    def __init__(self, x: int, y: int, width: int, height: int, text: str,
                 callback: Optional[Callable] = None):
        """
        Initialize button.

        Args:
            x, y: Position
            width, height: Dimensions
            text: Button label
            callback: Function to call on click
        """
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.callback = callback
        self.hovered = False
        self.enabled = True
        self.pressed = False

    def handle_event(self, event: pygame.event.Event) -> bool:
        """
        Handle mouse events.

        Args:
            event: Pygame event

        Returns:
            True if button was clicked
        """
        if not self.enabled:
            return False

        if event.type == pygame.MOUSEMOTION:
            self.hovered = self.rect.collidepoint(event.pos)

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.hovered:
                self.pressed = True

        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self.pressed and self.hovered:
                self.pressed = False
                if self.callback:
                    self.callback()
                return True
            self.pressed = False

        return False

    def render(self, surface: pygame.Surface):
        """Render the button."""
        # Determine color based on state
        if not self.enabled:
            color = Colors.BUTTON_DISABLED
        elif self.pressed:
            color = Colors.BUTTON_ACTIVE
        elif self.hovered:
            color = Colors.BUTTON_HOVER
        else:
            color = Colors.BUTTON_NORMAL

        # Draw button background
        pygame.draw.rect(surface, color, self.rect, border_radius=5)
        pygame.draw.rect(surface, Colors.BORDER_LIGHT, self.rect, 2, border_radius=5)

        # Draw text - Use SysFont for better rendering
        font = pygame.font.SysFont('arial', FontSizes.BODY - 2, bold=True)
        text_color = Colors.TEXT_PRIMARY if self.enabled else Colors.TEXT_SECONDARY
        text_surface = font.render(self.text, True, text_color)
        text_rect = text_surface.get_rect(center=self.rect.center)
        surface.blit(text_surface, text_rect)


class Panel:
    """
    Container panel with border and background.
    """

    def __init__(self, x: int, y: int, width: int, height: int, title: str = ""):
        """
        Initialize panel.

        Args:
            x, y: Position
            width, height: Dimensions
            title: Panel title (optional)
        """
        self.rect = pygame.Rect(x, y, width, height)
        self.title = title

    def render(self, surface: pygame.Surface):
        """Render panel background and border."""
        # Background
        pygame.draw.rect(surface, Colors.PANEL_BG, self.rect, border_radius=8)

        # Border
        pygame.draw.rect(surface, Colors.BORDER_LIGHT, self.rect, 2, border_radius=8)

        # Title - Use SysFont for better rendering
        if self.title:
            font = pygame.font.SysFont('arial', FontSizes.HEADING - 2, bold=True)
            text = font.render(self.title, True, Colors.TEXT_ACCENT)
            text_rect = text.get_rect(center=(self.rect.centerx, self.rect.top + 20))
            surface.blit(text, text_rect)


class TextDisplay:
    """
    Static text display component.
    """

    def __init__(self, x: int, y: int, width: int, font_size: int = FontSizes.BODY):
        """
        Initialize text display.

        Args:
            x, y: Position
            width: Max width for wrapping
            font_size: Font size
        """
        self.x = x
        self.y = y
        self.width = width
        self.font_size = font_size
        self.lines: list[Tuple[str, Tuple[int, int, int]]] = []

    def set_text(self, lines: list[Tuple[str, Optional[Tuple[int, int, int]]]]):
        """
        Set text content.

        Args:
            lines: List of (text, color) tuples
        """
        self.lines = [(text, color or Colors.TEXT_PRIMARY) for text, color in lines]

    def render(self, surface: pygame.Surface):
        """Render text lines."""
        # Use SysFont for better rendering
        font = pygame.font.SysFont('arial', self.font_size)
        y_offset = 0
        line_height = self.font_size + 4

        for text, color in self.lines:
            text_surface = font.render(text, True, color)
            surface.blit(text_surface, (self.x, self.y + y_offset))
            y_offset += line_height


class StatDisplay:
    """
    Displays a labeled statistic value.
    """

    def __init__(self, x: int, y: int, label: str, value: str = "",
                 value_color: Optional[Tuple[int, int, int]] = None):
        """
        Initialize stat display.

        Args:
            x, y: Position
            label: Stat label
            value: Stat value
            value_color: Color for value text
        """
        self.x = x
        self.y = y
        self.label = label
        self.value = value
        self.value_color = value_color or Colors.TEXT_ACCENT

    def set_value(self, value: str, color: Optional[Tuple[int, int, int]] = None):
        """Update displayed value."""
        self.value = value
        if color:
            self.value_color = color

    def render(self, surface: pygame.Surface):
        """Render stat display."""
        # Use SysFont for better rendering
        label_font = pygame.font.SysFont('arial', FontSizes.SMALL - 3)
        value_font = pygame.font.SysFont('arial', FontSizes.HEADING - 2, bold=True)

        # Render label
        label_surf = label_font.render(self.label, True, Colors.TEXT_SECONDARY)
        surface.blit(label_surf, (self.x, self.y))

        # Render value
        value_surf = value_font.render(self.value, True, self.value_color)
        surface.blit(value_surf, (self.x, self.y + 16))


class RadioButton:
    """
    Radio button for single selection within a group.
    """

    def __init__(self, x: int, y: int, label: str, group: str, value: any):
        """
        Initialize radio button.

        Args:
            x, y: Position
            label: Button label
            group: Radio group name (for mutual exclusion)
            value: Value when selected
        """
        self.x = x
        self.y = y
        self.label = label
        self.group = group
        self.value = value
        self.selected = False
        self.hovered = False
        self.radius = 8
        self.enabled = True
        self.extra_text = ""
        self.extra_color = Colors.TEXT_SECONDARY

        # Calculate hit area
        self._update_hit_rect()

    def _update_hit_rect(self):
        """Recalculate hit rect based on current label text."""
        font = pygame.font.SysFont('arial', FontSizes.BODY - 2)
        label_width = font.size(self.label)[0]
        extra_width = font.size(self.extra_text)[0] if self.extra_text else 0
        total_width = label_width + extra_width + self.radius * 2 + 20
        self.hit_rect = pygame.Rect(
            self.x - self.radius,
            self.y - self.radius,
            total_width,
            self.radius * 2 + 4
        )

    def set_enabled(self, enabled: bool) -> None:
        """Enable/disable the radio button."""
        self.enabled = enabled
        if not enabled:
            self.selected = False
            self.hovered = False

    def set_extra(self, text: str, color: Tuple[int, int, int]) -> None:
        """Display auxiliary text next to the label (e.g., profit preview)."""
        self.extra_text = text
        self.extra_color = color
        self._update_hit_rect()

    def handle_event(self, event: pygame.event.Event) -> bool:
        """
        Handle mouse events.

        Returns:
            True if selection changed
        """
        if not self.enabled:
            self.hovered = False
            return False

        if event.type == pygame.MOUSEMOTION:
            self.hovered = self.hit_rect.collidepoint(event.pos)

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.hovered:
                self.selected = True
                return True

        return False

    def render(self, surface: pygame.Surface):
        """Render radio button."""
        # Outer circle
        border_color = Colors.BUTTON_HOVER if self.hovered and self.enabled else Colors.BORDER_LIGHT
        fill_color = Colors.TEXT_ACCENT if self.enabled else Colors.TEXT_SECONDARY
        pygame.draw.circle(surface, border_color, (self.x, self.y), self.radius, 2)

        # Inner filled circle if selected
        if self.selected:
            pygame.draw.circle(surface, fill_color, (self.x, self.y), self.radius - 3)

        # Label - Use SysFont for better rendering
        font = pygame.font.SysFont('arial', FontSizes.BODY - 2)
        label_color = Colors.TEXT_PRIMARY if self.enabled else Colors.TEXT_SECONDARY
        text = font.render(self.label, True, label_color)
        surface.blit(text, (self.x + self.radius + 8, self.y - 8))

        if self.extra_text:
            extra_font = pygame.font.SysFont('arial', FontSizes.SMALL - 1, bold=True)
            extra_surf = extra_font.render(self.extra_text, True, self.extra_color)
            extra_x = self.x + self.radius + 8 + text.get_width() + 8
            surface.blit(extra_surf, (extra_x, self.y - 6))


class Tooltip:
    """
    Hover tooltip display.
    """

    def __init__(self):
        """Initialize tooltip."""
        self.visible = False
        self.text = ""
        self.position = (0, 0)

    def show(self, text: str, position: Tuple[int, int]):
        """
        Show tooltip.

        Args:
            text: Tooltip text
            position: Screen position
        """
        self.visible = True
        self.text = text
        self.position = position

    def hide(self):
        """Hide tooltip."""
        self.visible = False

    def render(self, surface: pygame.Surface):
        """Render tooltip if visible."""
        if not self.visible or not self.text:
            return

        # Use SysFont for better anti-aliased rendering
        font = pygame.font.SysFont('arial', FontSizes.SMALL)
        lines = self.text.split('\n')

        # Calculate tooltip size
        max_width = max(font.size(line)[0] for line in lines)
        line_height = font.get_height() + 2  # Add small spacing between lines
        tooltip_width = max_width + TOOLTIP_PADDING * 2
        tooltip_height = len(lines) * line_height + TOOLTIP_PADDING * 2

        # Position tooltip (avoid going off screen)
        x, y = self.position
        x = min(x, WINDOW_WIDTH - tooltip_width - 10)
        y = min(y, WINDOW_HEIGHT - tooltip_height - 10)

        # Draw background with shadow effect
        shadow_rect = pygame.Rect(x + 2, y + 2, tooltip_width, tooltip_height)
        pygame.draw.rect(surface, (0, 0, 0, 100), shadow_rect, border_radius=5)

        tooltip_rect = pygame.Rect(x, y, tooltip_width, tooltip_height)
        pygame.draw.rect(surface, TOOLTIP_BG, tooltip_rect, border_radius=5)
        pygame.draw.rect(surface, TOOLTIP_BORDER, tooltip_rect, 2, border_radius=5)

        # Draw text
        y_offset = TOOLTIP_PADDING
        for line in lines:
            text_surf = font.render(line, True, Colors.TEXT_PRIMARY)
            surface.blit(text_surf, (x + TOOLTIP_PADDING, y + y_offset))
            y_offset += line_height


class ProgressBar:
    """
    Progress bar for visual feedback.
    """

    def __init__(self, x: int, y: int, width: int, height: int = 20):
        """
        Initialize progress bar.

        Args:
            x, y: Position
            width, height: Dimensions
        """
        self.rect = pygame.Rect(x, y, width, height)
        self.progress = 0.0  # 0.0 to 1.0

    def set_progress(self, progress: float):
        """
        Set progress value.

        Args:
            progress: Value between 0.0 and 1.0
        """
        self.progress = max(0.0, min(1.0, progress))

    def render(self, surface: pygame.Surface):
        """Render progress bar."""
        # Background
        pygame.draw.rect(surface, Colors.BG_DARK, self.rect, border_radius=3)

        # Progress fill
        if self.progress > 0:
            fill_width = int(self.rect.width * self.progress)
            fill_rect = pygame.Rect(
                self.rect.x,
                self.rect.y,
                fill_width,
                self.rect.height
            )
            pygame.draw.rect(surface, Colors.PROFIT_POSITIVE, fill_rect, border_radius=3)

        # Border
        pygame.draw.rect(surface, Colors.BORDER_LIGHT, self.rect, 2, border_radius=3)
