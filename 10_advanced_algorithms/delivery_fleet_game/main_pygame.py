#!/usr/bin/env python3
"""
Delivery Fleet Management System - Pygame GUI Version (PRODUCTION READY)

Complete, playable game with all features working.

Usage:
    python main_pygame.py
"""

import sys
import pygame
from pathlib import Path
from typing import Optional, List

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.core import GameEngine
from src.agents import GreedyAgent, BacktrackingAgent, PruningBacktrackingAgent, StudentAgent
from src.models import Route
from src.ui.constants import *
from src.ui.map_renderer import MapRenderer
from src.ui.components import Button, Panel, CollapsiblePanel, StatDisplay, RadioButton, Tooltip
from src.ui.font_utils import render_text
from src.ui.manual_mode import ManualModeManager
from src.utils.metrics import calculate_route_metrics


class Modal:
    """Modal dialog for vehicle purchase and other actions."""

    def __init__(self, title: str, width: int = 500, height: int = 400):
        self.title = title
        self.width = width
        self.height = height
        self.visible = False
        self.buttons = []
        self.content_lines = []

        # Center position
        self.x = (WINDOW_WIDTH - width) // 2
        self.y = (WINDOW_HEIGHT - height) // 2
        self.rect = pygame.Rect(self.x, self.y, width, height)

    def show(self, content_lines: list, buttons: list, extra_data=None):
        """Show modal with content and buttons."""
        self.visible = True
        self.content_lines = content_lines
        self.buttons = buttons
        self.extra_data = extra_data or {}

    def hide(self):
        """Hide modal."""
        self.visible = False
        self.buttons = []

    def handle_event(self, event):
        """Handle events for modal buttons."""
        if not self.visible:
            return None

        for button in self.buttons:
            if button.handle_event(event):
                return button.text  # Return which button was clicked
        return None

    def render(self, screen):
        """Render modal."""
        if not self.visible:
            return

        # Darken background
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
        overlay.set_alpha(180)
        overlay.fill((0, 0, 0))
        screen.blit(overlay, (0, 0))

        # Modal background
        pygame.draw.rect(screen, Colors.PANEL_BG, self.rect, border_radius=10)
        pygame.draw.rect(screen, Colors.BORDER_LIGHT, self.rect, 3, border_radius=10)

        # Title - Use SysFont for better rendering
        font_title = pygame.font.SysFont('arial', FontSizes.HEADING, bold=True)
        title_surf = font_title.render(self.title, True, Colors.TEXT_ACCENT)
        title_rect = title_surf.get_rect(center=(self.rect.centerx, self.y + 30))
        screen.blit(title_surf, title_rect)

        # Custom rendering for vehicle purchase modal
        if self.title == "Purchase Vehicle" and len(self.content_lines) == 0:
            self._render_vehicle_modal_content(screen)
        else:
            # Content - Use SysFont for better rendering
            font_body = pygame.font.SysFont('arial', FontSizes.BODY - 2)  # Slightly smaller for modal content
            y_offset = 70
            for line, color in self.content_lines:
                text_surf = font_body.render(line, True, color)
                text_rect = text_surf.get_rect(center=(self.rect.centerx, self.y + y_offset))
                screen.blit(text_surf, text_rect)
                y_offset += 25

        # Buttons
        for button in self.buttons:
            button.render(screen)

    def _render_vehicle_modal_content(self, screen):
        """Custom rendering for vehicle purchase modal."""
        font_medium = pygame.font.SysFont('arial', FontSizes.BODY)
        font_spec = pygame.font.SysFont('arial', FontSizes.SMALL - 1)

        # Display balance at top
        if hasattr(self, 'extra_data') and 'balance' in self.extra_data:
            balance = self.extra_data['balance']
            balance_text = f"Your Balance: ${balance:,.0f}"
            balance_color = Colors.PROFIT_POSITIVE if balance >= 0 else Colors.PROFIT_NEGATIVE
            balance_surf = font_medium.render(balance_text, True, balance_color)
            balance_rect = balance_surf.get_rect(center=(self.rect.centerx, self.y + 75))
            screen.blit(balance_surf, balance_rect)

        # Render vehicle specs below each button (except cancel)
        for button in self.buttons[:-1]:  # Skip cancel button
            if hasattr(button, 'vehicle_info'):
                info = button.vehicle_info

                # Render specs below button
                spec_y = button.rect.y + button.rect.height + 5

                # Affordability status
                if info['can_afford']:
                    status_text = f"✓ Capacity: {info['capacity']:.0f}m³  •  ${info['cost_per_km']:.2f}/km  •  Range: {info['range']:.0f}km"
                    status_color = Colors.TEXT_SECONDARY
                else:
                    status_text = "✗ Insufficient funds"
                    status_color = Colors.PROFIT_NEGATIVE

                spec_surf = font_spec.render(status_text, True, status_color)
                spec_rect = spec_surf.get_rect(center=(self.rect.centerx, spec_y))
                screen.blit(spec_surf, spec_rect)


class DeliveryFleetApp:
    """Main Pygame application - PRODUCTION VERSION."""

    def __init__(self):
        """Initialize the application."""
        pygame.init()
        pygame.display.set_caption("Delivery Fleet Manager - Art of Programming")

        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        self.clock = pygame.time.Clock()
        self.running = True

        # Surfaces
        self.map_surface = pygame.Surface((MAP_WIDTH, MAP_HEIGHT))

        # Initialize game engine
        data_dir = Path(__file__).parent / "data"
        self.engine = GameEngine(data_dir)
        self.map_renderer = MapRenderer(self.map_surface, self.engine.delivery_map)

        # Register agents
        self._register_agents()

        # UI state
        self.selected_agent = "greedy"
        self.tooltip = Tooltip()
        self.warning_message = ""
        self.warning_color = Colors.PROFIT_NEGATIVE

        # Manual mode state
        self.mode = "AUTO"  # "AUTO" or "MANUAL"
        self.manual_mode_manager = None  # Will be created when needed
        self.disabled_agents = {"backtracking"}

        # Modals
        self.vehicle_modal = Modal("Purchase Vehicle", 650, 650)  # Larger for detailed specs
        self.capacity_warning_modal = Modal("⚠️ Insufficient Capacity", 600, 400)
        self.marketing_modal = Modal("📈 Marketing & Package Rate", 650, 450)
        self.day_summary_modal = Modal("📦 Day Summary", 700, 580)  # Increased height for button
        self.comparison_modal = Modal("🎯 Manual vs Algorithm Comparison", 750, 600)

        # Autoplay state defaults (used during UI creation)
        self.autoplay_enabled = False
        self.autoplay_speed = 1
        self.autoplay_timer = 0.0
        self.autoplay_action: Optional[str] = None
        self.speed_button_keys = ['speed1', 'speed2', 'speed3']
        self.auto_plan_deferred = False

        # Create UI
        self._create_ui_components()

        # Game state
        self.planned_routes = []
        self.package_status = {}
        self.agent_metrics_preview = {}
        self.render_routes = []

        # Start new game
        self.engine.new_game()
        self.update_stats()
        self.start_day_flow()

        print("✓ Delivery Fleet Manager Ready!")
        print("✓ Day initialized. Agents ready for planning")

    def _register_agents(self):
        """Register all routing agents."""
        self.engine.register_agent("greedy", GreedyAgent(self.engine.delivery_map))
        self.engine.register_agent("greedy_2opt", GreedyAgent(self.engine.delivery_map, use_2opt=True))
        try:
            from src.agents.agent_r import RAgent

            self.engine.register_agent("agent_r", RAgent(self.engine.delivery_map))
        except Exception as exc:
            print(f"⚠️ Failed to register Agent R: {exc}")
        try:
            from src.agents.agent_r_neural import NeuralRAgent

            self.engine.register_agent("agent_r_neural", NeuralRAgent(self.engine.delivery_map))
        except Exception as exc:
            print(f"⚠️ Failed to register Agent R Neural: {exc}")
        self.engine.register_agent("backtracking", BacktrackingAgent(self.engine.delivery_map, max_packages=12))
        self.engine.register_agent("pruning_backtracking",
                                   PruningBacktrackingAgent(self.engine.delivery_map, max_packages=15))
        self.engine.register_agent("student", StudentAgent(self.engine.delivery_map))
        self.engine.register_agent("student_2opt", StudentAgent(self.engine.delivery_map, use_2opt=True))

    def _create_ui_components(self):
        """Create all UI components with FIXED layout."""

        # FIXED LAYOUT - Everything fits within 1000px height
        SIDEBAR_START = 100  # Below title bar
        self.sidebar_start = SIDEBAR_START
        self.sidebar_right_start = SIDEBAR_START

        left_panel_x = SIDEBAR_X + 10
        left_panel_width = SIDEBAR_WIDTH - 20
        right_panel_x = SIDEBAR_RIGHT_X + 10
        right_panel_width = SECONDARY_SIDEBAR_WIDTH - 20

        # Panels - Carefully calculated to prevent overlaps
        self.stats_panel = CollapsiblePanel(left_panel_x, SIDEBAR_START, left_panel_width, 200, "GAME STATUS")
        self.mode_panel = Panel(left_panel_x, SIDEBAR_START, left_panel_width, 150, "MODE")
        self.agent_panel = CollapsiblePanel(left_panel_x, SIDEBAR_START, left_panel_width, 250, "AGENTS")
        self.custom_agent_panel = CollapsiblePanel(right_panel_x, SIDEBAR_START, right_panel_width, 120, "CUSTOM AGENTS")
        self.controls_panel = Panel(right_panel_x, SIDEBAR_START, right_panel_width, 330, "CONTROLS")

        # Warning message area - positioned below controls panel
        self.warning_rect = pygame.Rect(right_panel_x, SIDEBAR_START, right_panel_width, 80)

        # Stats - Organized in clear rows
        self.stat_col1 = left_panel_x + 15
        stat_col_width = (left_panel_width - 70) // 3
        self.stat_col2 = self.stat_col1 + stat_col_width
        self.stat_col3 = self.stat_col2 + stat_col_width
        self.stats_row_offsets = (40, 95, 145)
        self.stats_divider_offsets = (85, 140)

        # Row 1: Day, Balance, Popularity
        self.day_stat = StatDisplay(self.stat_col1, self.stats_panel.rect.y + self.stats_row_offsets[0], "Day:", "1")
        self.balance_stat = StatDisplay(self.stat_col2, self.stats_panel.rect.y + self.stats_row_offsets[0], "Balance:", "$100K")
        self.popularity_stat = StatDisplay(self.stat_col3, self.stats_panel.rect.y + self.stats_row_offsets[0], "Popularity:", "300")

        # Row 2: Fleet and Packages
        self.fleet_stat = StatDisplay(self.stat_col1, self.stats_panel.rect.y + self.stats_row_offsets[1], "Fleet:", "2 veh")
        self.packages_stat = StatDisplay(self.stat_col2, self.stats_panel.rect.y + self.stats_row_offsets[1], "Pending:", "0")
        self.capacity_stat = StatDisplay(self.stat_col3, self.stats_panel.rect.y + self.stats_row_offsets[1], "Capacity:", "0/0")

        # Row 3: Planned route metrics (visible when routes are planned)
        self.planned_cost_stat = StatDisplay(self.stat_col1, self.stats_panel.rect.y + self.stats_row_offsets[2], "Cost:", "$0")
        self.planned_revenue_stat = StatDisplay(self.stat_col2, self.stats_panel.rect.y + self.stats_row_offsets[2], "Revenue:", "$0")
        self.planned_profit_stat = StatDisplay(self.stat_col3, self.stats_panel.rect.y + self.stats_row_offsets[2], "Profit:", "$0")

        # Store planned metrics
        self.planned_metrics = None

        # Mode toggle buttons - positioned in MODE panel
        mode_btn_x = self.mode_panel.rect.x + 15
        mode_btn_y = self.mode_panel.rect.y + 40
        mode_btn_width = (self.mode_panel.rect.width - 40) // 2
        self.mode_auto_btn = Button(mode_btn_x, mode_btn_y, mode_btn_width, 35, "AUTO", self.on_mode_auto)
        self.mode_manual_btn = Button(mode_btn_x + mode_btn_width + 10, mode_btn_y, mode_btn_width, 35, "MANUAL", self.on_mode_manual)
        self._mode_button_offsets = {
            'mode_auto': (self.mode_auto_btn.rect.x - self.mode_panel.rect.x,
                          self.mode_auto_btn.rect.y - self.mode_panel.rect.y),
            'mode_manual': (self.mode_manual_btn.rect.x - self.mode_panel.rect.x,
                            self.mode_manual_btn.rect.y - self.mode_panel.rect.y)
        }

        self.mode_preview_font = pygame.font.SysFont('arial', 14)
        self.auto_revenue_preview = "—"
        self.manual_revenue_preview = "—"
        self.auto_revenue_color = Colors.TEXT_SECONDARY
        self.manual_revenue_color = Colors.TEXT_SECONDARY
        self._set_auto_preview(None)
        self._set_manual_preview(None)

        # Agent radio buttons - positioned in AGENTS panel
        self.agent_list_top_offset = self.agent_panel.header_height + 10
        self.agent_radio_x = self.agent_panel.rect.x + 25
        radio_y = self.agent_panel.rect.y + self.agent_list_top_offset
        self.agent_radio_spacing = 35
        self.agent_radios = [
            RadioButton(self.agent_radio_x, radio_y, "Greedy", "agent", "greedy"),
            RadioButton(self.agent_radio_x, radio_y + 35, "Greedy+2opt", "agent", "greedy_2opt"),
            RadioButton(self.agent_radio_x, radio_y + 70, "Backtrack", "agent", "backtracking"),
            RadioButton(self.agent_radio_x, radio_y + 105, "Pruning BT", "agent", "pruning_backtracking"),
            RadioButton(self.agent_radio_x, radio_y + 140, "Student Sweep", "agent", "student"),
            RadioButton(self.agent_radio_x, radio_y + 175, "Student Sweep+2opt", "agent", "student_2opt"),
        ]
        self.agent_radios[0].selected = True

        self.custom_agent_list_top_offset = self.custom_agent_panel.header_height + 10
        self.custom_radio_x = self.custom_agent_panel.rect.x + 25
        custom_radio_y = self.custom_agent_panel.rect.y + self.custom_agent_list_top_offset
        self.custom_radio_spacing = 35
        self.custom_agent_radios = [
            RadioButton(self.custom_radio_x, custom_radio_y, "Agent R", "agent", "agent_r"),
            RadioButton(self.custom_radio_x, custom_radio_y + self.custom_radio_spacing, "Agent R Neural", "agent", "agent_r_neural"),
        ]

        for radio in self.agent_radios + self.custom_agent_radios:
            if radio.value in self.disabled_agents:
                radio.set_enabled(False)
                radio.set_extra("Unavailable", Colors.TEXT_SECONDARY)

        self._ensure_valid_agent_selection()

        # Control buttons - positioned in CONTROLS panel
        panel_inner_x = self.controls_panel.rect.x + 15
        panel_inner_y = self.controls_panel.rect.y + 55  # Leave space for panel title
        btn_x = panel_inner_x
        btn_y = panel_inner_y
        btn_width = self.controls_panel.rect.width - 30
        btn_small_width = (btn_width - 10) // 2
        btn_height = 35
        btn_spacing = 38
        speed_btn_width = (btn_width - 20) // 3

        speed_btn_width = 50
        speed_btn_height = 30
        speed_spacing = 10
        autoplay_y = btn_y + btn_spacing * 2
        speed_x_start = btn_x + btn_width - (speed_btn_width * 3 + speed_spacing * 2)

        self.buttons = {
            'buy_vehicle': Button(btn_x, btn_y, btn_width, btn_height, "Buy Vehicle", self.on_buy_vehicle),
            'execute': Button(btn_x, btn_y + btn_spacing, btn_small_width, btn_height, "Execute", self.on_execute_day),
            'next_day': Button(btn_x + btn_small_width + 10, btn_y + btn_spacing, btn_small_width, btn_height, "Next", self.on_next_day),
            'autoplay': Button(btn_x, autoplay_y, btn_width - (speed_btn_width * 3 + speed_spacing * 2 + 20), btn_height, "Auto Play", self.toggle_autoplay),
            'speed1': Button(speed_x_start, autoplay_y + (btn_height - speed_btn_height) // 2, speed_btn_width, speed_btn_height, "1x", lambda: self.set_autoplay_speed(1)),
            'speed2': Button(speed_x_start + (speed_btn_width + speed_spacing), autoplay_y + (btn_height - speed_btn_height) // 2, speed_btn_width, speed_btn_height, "2x", lambda: self.set_autoplay_speed(2)),
            'speed3': Button(speed_x_start + 2 * (speed_btn_width + speed_spacing), autoplay_y + (btn_height - speed_btn_height) // 2, speed_btn_width, speed_btn_height, "3x", lambda: self.set_autoplay_speed(3)),
            'save': Button(btn_x, btn_y + btn_spacing * 4, btn_small_width, btn_height, "Save", self.on_save),
            'load': Button(btn_x + btn_small_width + 10, btn_y + btn_spacing * 4, btn_small_width, btn_height, "Load", self.on_load),
            'marketing': Button(btn_x, btn_y + btn_spacing * 5, btn_width, btn_height, "Marketing", self.on_show_marketing),
        }

        # Store offsets relative to controls panel for reflow
        self._control_button_offsets = {
            name: (button.rect.x - self.controls_panel.rect.x, button.rect.y - self.controls_panel.rect.y)
            for name, button in self.buttons.items()
        }

        # Set initial states
        self.buttons['execute'].enabled = False
        self.buttons['next_day'].enabled = False
        self._refresh_speed_buttons()
        self._reflow_sidebar_layout()
        self._set_mode_button_state(self.mode == "MANUAL")

    # ==================== EVENT HANDLERS ====================

    def _set_mode_button_state(self, manual_active: bool) -> None:
        """Visually indicate which mode is active."""
        if hasattr(self, 'mode_manual_btn'):
            self.mode_manual_btn.pressed = manual_active
        if hasattr(self, 'mode_auto_btn'):
            self.mode_auto_btn.pressed = not manual_active

    def _set_auto_preview(self, metrics: Optional[dict]) -> None:
        """Update the automatic planning revenue preview text."""
        if metrics and metrics.get('total_revenue') is not None:
            revenue = metrics['total_revenue']
            self.auto_revenue_preview = f"${revenue:,.0f}"
            self.auto_revenue_color = Colors.PROFIT_POSITIVE if revenue >= 0 else Colors.PROFIT_NEGATIVE
        else:
            self.auto_revenue_preview = "—"
            self.auto_revenue_color = Colors.TEXT_SECONDARY

    def _set_manual_preview(self, metrics: Optional[dict]) -> None:
        """Update the manual planning revenue preview text."""
        if metrics and metrics.get('total_revenue') is not None:
            revenue = metrics['total_revenue']
            self.manual_revenue_preview = f"${revenue:,.0f}"
            self.manual_revenue_color = Colors.PROFIT_POSITIVE if revenue >= 0 else Colors.PROFIT_NEGATIVE
        else:
            self.manual_revenue_preview = "—"
            self.manual_revenue_color = Colors.TEXT_SECONDARY

    def _panel_effective_height(self, panel: Panel) -> int:
        if isinstance(panel, CollapsiblePanel):
            return panel.header_height if panel.collapsed else panel.full_height
        return panel.rect.height

    def _reflow_sidebar_layout(self) -> None:
        y_left = getattr(self, "sidebar_start", 100)
        y_right = getattr(self, "sidebar_right_start", 100)
        gap = 10

        for panel in (self.stats_panel, self.mode_panel, self.agent_panel):
            panel.rect.y = y_left
            y_left += self._panel_effective_height(panel) + gap

        for panel in (self.custom_agent_panel, self.controls_panel):
            panel.rect.y = y_right
            y_right += self._panel_effective_height(panel) + gap

        # Reposition warning area beneath controls
        self.warning_rect.x = self.controls_panel.rect.x
        self.warning_rect.width = self.controls_panel.rect.width
        self.warning_rect.y = self.controls_panel.rect.y + self.controls_panel.rect.height + 20

        # Update stat display positions
        base_y_row1 = self.stats_panel.rect.y + self.stats_row_offsets[0]
        row2 = self.stats_panel.rect.y + self.stats_row_offsets[1]
        row3 = self.stats_panel.rect.y + self.stats_row_offsets[2]

        for stat in (self.day_stat, self.balance_stat, self.popularity_stat):
            stat.y = base_y_row1
        for stat in (self.fleet_stat, self.packages_stat, self.capacity_stat):
            stat.y = row2
        for stat in (self.planned_cost_stat, self.planned_revenue_stat, self.planned_profit_stat):
            stat.y = row3

        # Update agent radio positions
        agent_base = self.agent_panel.rect.y + self.agent_list_top_offset
        for idx, radio in enumerate(self.agent_radios):
            radio.set_position(self.agent_radio_x, agent_base + idx * self.agent_radio_spacing)

        custom_base = self.custom_agent_panel.rect.y + self.custom_agent_list_top_offset
        for idx, radio in enumerate(self.custom_agent_radios):
            radio.set_position(self.custom_radio_x, custom_base + idx * self.custom_radio_spacing)

        # Reposition mode buttons relative to mode panel
        if self._mode_button_offsets:
            offset_auto = self._mode_button_offsets['mode_auto']
            offset_manual = self._mode_button_offsets['mode_manual']
            self.mode_auto_btn.rect.x = self.mode_panel.rect.x + offset_auto[0]
            self.mode_auto_btn.rect.y = self.mode_panel.rect.y + offset_auto[1]
            self.mode_manual_btn.rect.x = self.mode_panel.rect.x + offset_manual[0]
            self.mode_manual_btn.rect.y = self.mode_panel.rect.y + offset_manual[1]

        # Reposition buttons relative to controls panel
        for name, button in self.buttons.items():
            offset_x, offset_y = self._control_button_offsets[name]
            button.rect.x = self.controls_panel.rect.x + offset_x
            button.rect.y = self.controls_panel.rect.y + offset_y

    def _ensure_valid_agent_selection(self):
        """Select the first available agent if current selection is disabled."""
        all_radios = self.agent_radios + self.custom_agent_radios
        if any(r.value == self.selected_agent and r.enabled for r in all_radios):
            return

        for radio in all_radios:
            radio.selected = False

        for radio in all_radios:
            if radio.enabled:
                radio.selected = True
                self.selected_agent = radio.value
                break

    def _refresh_speed_buttons(self):
        """Update autoplay speed button labels to indicate active selection."""
        labels = {1: "1x", 2: "2x", 3: "3x"}
        for idx, key in enumerate(self.speed_button_keys, start=1):
            button = self.buttons.get(key)
            if not button:
                continue
            if self.autoplay_speed == idx:
                button.text = f"[{labels[idx]}]"
            else:
                button.text = labels[idx]

    def _update_planned_metrics_display(self):
        """Refresh the cost/revenue/profit row based on planned metrics."""
        if self.planned_metrics:
            cost = self.planned_metrics.get('total_cost', 0.0)
            revenue = self.planned_metrics.get('total_revenue', 0.0)
            profit = self.planned_metrics.get('total_profit', 0.0)

            self.planned_cost_stat.set_value(f"${cost:,.0f}", Colors.TEXT_SECONDARY)
            revenue_color = Colors.PROFIT_POSITIVE if revenue >= 0 else Colors.PROFIT_NEGATIVE
            self.planned_revenue_stat.set_value(f"${revenue:,.0f}", revenue_color)
            profit_color = Colors.PROFIT_POSITIVE if profit >= 0 else Colors.PROFIT_NEGATIVE
            self.planned_profit_stat.set_value(f"${profit:,.0f}", profit_color)
        else:
            self.planned_cost_stat.set_value("$0", Colors.TEXT_SECONDARY)
            self.planned_revenue_stat.set_value("$0", Colors.TEXT_SECONDARY)
            self.planned_profit_stat.set_value("$0", Colors.TEXT_SECONDARY)

    def start_day_flow(self):
        """Begin a new day, auto-plan routes when capacity allows."""
        print("\n[UI] Starting day...")
        self.engine.start_day()

        self.render_routes = []
        self.auto_plan_deferred = False
        self._set_auto_preview(None)
        self._set_manual_preview(None)

        if not self.engine.game_state.packages_pending:
            self.show_warning("No packages for this day!", Colors.TEXT_ACCENT)
            return

        self.package_status = {pkg.id: "pending" for pkg in self.engine.game_state.packages_pending}

        total_volume = sum(pkg.volume_m3 for pkg in self.engine.game_state.packages_pending)
        fleet_capacity = sum(v.vehicle_type.capacity_m3 for v in self.engine.game_state.fleet)

        if fleet_capacity <= 0 or total_volume > fleet_capacity:
            if self.mode == "AUTO":
                self.auto_plan_deferred = True
            self.show_day_summary(total_volume, fleet_capacity)
        else:
            if self.mode == "AUTO":
                if self.autoplay_enabled:
                    self.auto_plan_routes(show_feedback=True)
                else:
                    total_volume = sum(pkg.volume_m3 for pkg in self.engine.game_state.packages_pending)
                    fleet_capacity = sum(v.vehicle_type.capacity_m3 for v in self.engine.game_state.fleet)
                    if fleet_capacity <= 0 or total_volume > fleet_capacity:
                        self.auto_plan_deferred = True
                        self.show_day_summary(total_volume, fleet_capacity)
                    else:
                        self.auto_plan_deferred = True
                        self.show_day_preview(total_volume, fleet_capacity)
            else:
                if not self.autoplay_enabled:
                    total_volume = sum(pkg.volume_m3 for pkg in self.engine.game_state.packages_pending)
                    fleet_capacity = sum(v.vehicle_type.capacity_m3 for v in self.engine.game_state.fleet)
                    if fleet_capacity <= 0 or total_volume > fleet_capacity:
                        self.show_day_summary(total_volume, fleet_capacity)
                    else:
                        self.show_day_preview(total_volume, fleet_capacity)
                self.show_warning("Manual mode: build routes then execute.", Colors.TEXT_ACCENT)

        self.update_agent_previews()
        self.update_stats()
        if self.mode == "MANUAL":
            self.buttons['execute'].enabled = True
        else:
            self.buttons['execute'].enabled = bool(self.planned_routes)

    def _simulate_agent_metrics(self, agent_name: str) -> Optional[dict]:
        """Run agent planning without mutating game state to collect metrics."""
        if agent_name not in self.engine.agents:
            return None

        state = self.engine.game_state
        if not state or not state.packages_pending:
            return None

        agent = self.engine.agents[agent_name]
        packages = state.packages_pending.copy()
        fleet = state.get_available_fleet()
        routes = agent.plan_routes(packages, fleet)
        if not routes:
            return None

        metrics = calculate_route_metrics(routes)
        metrics['routes'] = routes
        metrics['agent_name'] = agent_name
        return metrics

    def update_agent_previews(self, metrics_override: Optional[dict] = None) -> None:
        """Update agent radio labels with projected profit values."""
        state = self.engine.game_state
        all_radios = self.agent_radios + self.custom_agent_radios
        if not state or not state.packages_pending:
            self._set_auto_preview(None)
            self.agent_metrics_preview = {}
            for radio in all_radios:
                if radio.value in self.disabled_agents:
                    radio.set_extra("Unavailable", Colors.TEXT_SECONDARY)
                else:
                    radio.set_extra("", Colors.TEXT_SECONDARY)
            return

        previews = {}
        if metrics_override and metrics_override.get('agent_name'):
            previews[metrics_override['agent_name']] = metrics_override

        for radio in all_radios:
            if radio.value in self.disabled_agents or radio.value in previews:
                continue
            metrics = self._simulate_agent_metrics(radio.value)
            if metrics:
                previews[radio.value] = metrics

        self.agent_metrics_preview = previews
        self._set_auto_preview(previews.get(self.selected_agent))

        for radio in all_radios:
            if radio.value in self.disabled_agents:
                radio.set_extra("Unavailable", Colors.TEXT_SECONDARY)
                continue
            metrics = previews.get(radio.value)
            if metrics and metrics.get('total_profit') is not None:
                profit = metrics['total_profit']
                color = Colors.PROFIT_POSITIVE if profit >= 0 else Colors.PROFIT_NEGATIVE
                sign = "+" if profit >= 0 else "-"
                radio.set_extra(f"{sign}${abs(profit):,.0f}", color)
            else:
                radio.set_extra("", Colors.TEXT_SECONDARY)

        self._ensure_valid_agent_selection()

    def auto_plan_routes(self, show_feedback: bool = True):
        """Plan routes using the selected agent in AUTO mode."""
        self.auto_plan_deferred = False
        if not self.engine.game_state or not self.engine.game_state.packages_pending:
            if show_feedback:
                self.show_warning("No packages available to plan!", Colors.TEXT_ACCENT)
            return

        if self.mode == "MANUAL":
            if show_feedback:
                self.show_warning("Switch to AUTO mode to plan automatically.", Colors.TEXT_ACCENT)
            return

        agent_name = self.selected_agent
        if agent_name in self.disabled_agents:
            self.show_warning("Selected agent is unavailable.", Colors.TEXT_ACCENT)
            return

        metrics = self._simulate_agent_metrics(agent_name)
        if metrics and metrics.get('routes'):
            self.planned_routes = metrics['routes']
            self.render_routes = list(self.planned_routes)
            self.planned_metrics = metrics
            self.engine.apply_agent_solution(agent_name)
            self.buttons['execute'].enabled = True
            self._update_planned_metrics_display()
            self._set_auto_preview(metrics)

            profit = metrics['total_profit']
            color = Colors.PROFIT_POSITIVE if profit >= 0 else Colors.PROFIT_NEGATIVE
            self.show_warning(f"Routes planned! Profit: ${profit:.2f}", color if show_feedback else Colors.TEXT_ACCENT)
            self.update_agent_previews(metrics_override=metrics)
        else:
            self.planned_routes = []
            self.planned_metrics = None
            self.engine.game_state.set_routes([])
            self.buttons['execute'].enabled = False
            self.render_routes = []
            self._update_planned_metrics_display()
            self._set_auto_preview(None)
            if show_feedback:
                self.show_warning("No valid routes found!", Colors.PROFIT_NEGATIVE)

    def _maybe_execute_deferred_auto_plan(self, show_feedback: bool = True) -> None:
        """Run deferred auto-planning once blocking modals are closed."""
        if not self.auto_plan_deferred:
            return
        if self.mode != "AUTO":
            self.auto_plan_deferred = False
            return
        self.auto_plan_deferred = False
        self.auto_plan_routes(show_feedback=show_feedback)

    def toggle_autoplay(self):
        """Toggle automatic day progression."""
        if not self.autoplay_enabled:
            if self.mode != "AUTO":
                self.on_mode_auto()
            self.autoplay_enabled = True
            self.autoplay_timer = 0.0
            self.autoplay_action = None
            self.buttons['autoplay'].text = "Stop Auto"
            self.show_warning("Autoplay started.", Colors.TEXT_ACCENT)
        else:
            self.stop_autoplay("Autoplay stopped.")

    def stop_autoplay(self, message: Optional[str] = None, color=Colors.TEXT_ACCENT):
        if not self.autoplay_enabled and not message:
            return
        self.autoplay_enabled = False
        self.autoplay_action = None
        self.autoplay_timer = 0.0
        self.buttons['autoplay'].text = "Auto Play"
        if message:
            self.show_warning(message, color)

    def set_autoplay_speed(self, speed: int):
        speed = max(1, min(3, speed))
        if self.autoplay_speed == speed:
            return
        self.autoplay_speed = speed
        self._refresh_speed_buttons()
        if self.autoplay_enabled:
            self.show_warning(f"Autoplay speed set to {speed}x", Colors.TEXT_ACCENT)

    def _get_autoplay_delay(self) -> float:
        return {1: 1.2, 2: 0.7, 3: 0.4}.get(self.autoplay_speed, 1.0)

    def _determine_autoplay_action(self) -> Optional[str]:
        if not self.engine.game_state:
            return None
        if self.day_summary_modal.visible or self.capacity_warning_modal.visible or self.vehicle_modal.visible:
            return None
        if self.buttons['next_day'].enabled:
            return "next_day"
        if not self.planned_routes:
            return "plan"
        return "execute"

    def _execute_autoplay_action(self, action: str):
        if action == "plan":
            before = len(self.planned_routes)
            self.auto_plan_routes(show_feedback=False)
            if not self.planned_routes or len(self.planned_routes) == before:
                self.stop_autoplay("Autoplay halted: unable to plan routes.", Colors.PROFIT_NEGATIVE)
        elif action == "execute":
            if self.planned_routes:
                self.on_execute_day()
            else:
                self.stop_autoplay("Autoplay halted: no planned routes.", Colors.PROFIT_NEGATIVE)
        elif action == "next_day":
            if self.buttons['next_day'].enabled:
                self.on_next_day()
            else:
                self.stop_autoplay("Autoplay halted: cannot advance day.", Colors.PROFIT_NEGATIVE)

    def _get_manual_mode_rect(self) -> tuple[int, int, int, int]:
        """Calculate the manual mode popup dimensions."""
        margin = 20
        width = max(600, WINDOW_WIDTH - margin * 2)
        height = max(360, WINDOW_HEIGHT - margin * 2)

        if width >= WINDOW_WIDTH:
            width = WINDOW_WIDTH - margin
            margin_x = (WINDOW_WIDTH - width) // 2
        else:
            margin_x = margin

        if height >= WINDOW_HEIGHT:
            height = WINDOW_HEIGHT - margin
            margin_y = (WINDOW_HEIGHT - height) // 2
        else:
            margin_y = margin

        return margin_x, margin_y, int(width), int(height)

    def process_autoplay(self, dt: float):
        if not self.autoplay_enabled:
            return
        if self.day_summary_modal.visible or self.capacity_warning_modal.visible or self.vehicle_modal.visible:
            return

        action = self.autoplay_action or self._determine_autoplay_action()
        if not action:
            return

        if not self.autoplay_action:
            self.autoplay_action = action
            self.autoplay_timer = self._get_autoplay_delay()
            return

        self.autoplay_timer -= dt
        if self.autoplay_timer <= 0:
            action_to_run = self.autoplay_action
            self.autoplay_action = None
            self._execute_autoplay_action(action_to_run)

    def on_mode_auto(self):
        """Switch to AUTO mode."""
        self.mode = "AUTO"
        self._set_mode_button_state(False)
        self._set_manual_preview(None)
        self.show_warning("AUTO mode: algorithms will plan routes", Colors.TEXT_ACCENT)
        if self.manual_mode_manager:
            self.manual_mode_manager.active = False
        if self.engine.game_state and self.engine.game_state.packages_pending:
            self.auto_plan_routes(show_feedback=False)

    def on_mode_manual(self):
        """Switch to MANUAL mode."""
        self.mode = "MANUAL"
        self._set_mode_button_state(True)
        if not self.planned_routes:
            self._set_manual_preview(None)
        self.show_warning("MANUAL mode: Drag packages and build routes yourself!", Colors.TEXT_ACCENT)

        # Initialize manual mode manager if needed
        manual_rect = self._get_manual_mode_rect()
        if not self.manual_mode_manager:
            self.manual_mode_manager = ManualModeManager(*manual_rect, modal=True)
        else:
            self.manual_mode_manager.update_rect(*manual_rect)

        # Setup with current packages and fleet (allow empty lists)
        if self.engine.game_state:
            packages = self.engine.game_state.packages_pending or []
            fleet = self.engine.game_state.fleet or []
            self.manual_mode_manager.setup(packages, fleet, self.engine.delivery_map)
        else:
            self.manual_mode_manager.setup([], [], self.engine.delivery_map)

        self.manual_mode_manager.active = True
        self.buttons['execute'].enabled = True

    def show_day_summary(self, total_volume: float, fleet_capacity: float):
        """Show summary only when capacity is insufficient."""
        state = self.engine.game_state
        shortage = max(0.0, total_volume - fleet_capacity)
        content = [
            (f"Day {state.current_day}: capacity warning", Colors.TEXT_ACCENT),
            ("", Colors.TEXT_PRIMARY),
            (f"Packages volume: {total_volume:.1f} m³", Colors.TEXT_PRIMARY),
            (f"Fleet capacity: {fleet_capacity:.1f} m³", Colors.TEXT_PRIMARY),
            (f"Shortage: {shortage:.1f} m³", Colors.PROFIT_NEGATIVE),
            ("", Colors.TEXT_PRIMARY),
            ("Add more vehicles or continue and risk undelivered packages.", Colors.TEXT_SECONDARY),
        ]

        modal_btn_x = self.day_summary_modal.x + 120
        modal_btn_y = self.day_summary_modal.y + 480
        buttons = [
            Button(modal_btn_x, modal_btn_y, 220, 40, "Buy Vehicles", lambda: self.close_day_summary_and_buy(total_volume, fleet_capacity)),
            Button(
                modal_btn_x + 240,
                modal_btn_y,
                180,
                40,
                "Continue",
                lambda: self.close_day_summary_with_warning(total_volume, fleet_capacity)
                if self.autoplay_enabled
                else self.close_day_summary_manual(total_volume, fleet_capacity),
            ),
        ]

        self.day_summary_modal.show(content, buttons)

    def close_day_summary_and_buy(self, needed: float, available: float):
        """Close day summary and open vehicle purchase."""
        self.day_summary_modal.hide()
        self.on_buy_vehicle()

    def close_day_summary_with_warning(self, needed: float, available: float):
        """Close day summary and show capacity warning."""
        self.day_summary_modal.hide()
        self.show_capacity_warning(needed, available)

    def close_day_summary_manual(self, needed: float, available: float):
        """Close day summary in manual flow and show guidance."""
        self.day_summary_modal.hide()
        self.update_agent_previews()
        if self.mode == "MANUAL":
            self.buttons['execute'].enabled = True
        shortage = needed - available
        if shortage > 0:
            message = (
                f"Manual planning: shortage {shortage:.1f}m³. "
                "Plan carefully or assign fewer packages."
            )
            self.show_warning(message, Colors.TEXT_ACCENT)
        else:
            self.show_warning("Manual planning: review packages and build routes.", Colors.TEXT_ACCENT)
        self._maybe_execute_deferred_auto_plan(show_feedback=True)

    def show_capacity_warning(self, needed: float, available: float):
        """Show warning when capacity is insufficient."""
        deficit = needed - available
        needed_capacity = deficit

        # Suggest vehicle to buy
        suggestion = ""
        for vtype_name, vtype in self.engine.vehicle_types.items():
            if vtype.capacity_m3 >= deficit:
                if vtype.purchase_price <= self.engine.game_state.balance:
                    suggestion = f"Buy {vtype.name} ({vtype.capacity_m3}m³) for ${vtype.purchase_price:,}"
                    break

        content = [
            ("CAPACITY PROBLEM", Colors.PROFIT_NEGATIVE),
            ("", Colors.TEXT_PRIMARY),
            (f"Total packages: {needed:.1f}m³", Colors.TEXT_PRIMARY),
            (f"Fleet capacity: {available:.1f}m³", Colors.TEXT_PRIMARY),
            (f"Shortage: {deficit:.1f}m³", Colors.PROFIT_NEGATIVE),
            ("", Colors.TEXT_PRIMARY),
            ("You need more vehicles!", Colors.TEXT_ACCENT),
            (suggestion if suggestion else "Not enough balance!", Colors.TEXT_SECONDARY),
        ]

        # Create buttons
        modal_btn_y = self.capacity_warning_modal.y + 320
        modal_btn_x = self.capacity_warning_modal.x + 50
        modal_btn_width = 200

        buttons = [
            Button(modal_btn_x, modal_btn_y, modal_btn_width, 40, "Buy Vehicle",
                   lambda: self.close_modal_and_buy()),
            Button(modal_btn_x + 220, modal_btn_y, modal_btn_width, 40, "Continue",
                   lambda: self.close_modal_and_continue()),
        ]

        self.capacity_warning_modal.show(content, buttons)
    def show_day_preview(self, total_volume: float, fleet_capacity: float):
        """Preview upcoming day when capacity is sufficient."""
        state = self.engine.game_state
        utilization_pct = (total_volume / fleet_capacity * 100) if fleet_capacity > 0 else 0

        content = [
            (f"Day {state.current_day}: daily preview", Colors.TEXT_ACCENT),
            ("", Colors.TEXT_PRIMARY),
            (f"Packages volume: {total_volume:.1f} m³", Colors.TEXT_PRIMARY),
            (f"Fleet capacity: {fleet_capacity:.1f} m³", Colors.TEXT_PRIMARY),
            (f"Utilization: {utilization_pct:.0f}% of capacity", Colors.TEXT_SECONDARY),
            ("", Colors.TEXT_PRIMARY),
            ("Plan routes manually or run an agent.", Colors.TEXT_ACCENT),
        ]

        modal_btn_x = self.day_summary_modal.x + 160
        modal_btn_y = self.day_summary_modal.y + 480
        buttons = [
            Button(modal_btn_x, modal_btn_y, 220, 40, "Start Planning", lambda: self._handle_day_preview_continue()),
        ]

        self.day_summary_modal.show(content, buttons)

    def _handle_day_preview_continue(self):
        """Close day preview and trigger deferred auto-planning if required."""
        self.day_summary_modal.hide()
        self._maybe_execute_deferred_auto_plan(show_feedback=True)

    def close_modal_and_buy(self):
        """Close modal and open buy vehicle."""
        self.capacity_warning_modal.hide()
        self.on_buy_vehicle()

    def close_modal_and_continue(self):
        """Close modal and allow player to proceed with current day."""
        self.capacity_warning_modal.hide()
        self.show_warning(
            "Continuing with limited capacity – undelivered orders incur penalties.",
            Colors.PROFIT_NEGATIVE,
        )
        if self.mode == "MANUAL":
            self.buttons['execute'].enabled = True
        self._maybe_execute_deferred_auto_plan(show_feedback=True)

    def on_buy_vehicle(self):
        """Show vehicle purchase modal."""
        # Simplified header - no content lines, we'll draw everything custom
        content = []
        buttons = []

        # Calculate positions
        modal_x = self.vehicle_modal.x
        modal_y = self.vehicle_modal.y

        # Button layout - stacked vertically with proper spacing
        btn_width = 350
        btn_height = 38
        btn_x = modal_x + (self.vehicle_modal.width - btn_width) // 2  # Center buttons

        # Start buttons below the header text we'll draw
        btn_start_y = modal_y + 120
        btn_spacing = 48  # Space between vehicle buttons

        y_pos = btn_start_y

        # Create a button for each vehicle type
        for vtype_name, vtype in self.engine.vehicle_types.items():
            can_afford = vtype.purchase_price <= self.engine.game_state.balance

            # Button text shows key info
            btn_text = f"Buy {vtype.name} - ${vtype.purchase_price:,}"

            btn = Button(btn_x, y_pos, btn_width, btn_height,
                        btn_text,
                        lambda vt=vtype_name: self.purchase_vehicle(vt))
            btn.enabled = can_afford
            buttons.append(btn)

            # Store vehicle info for rendering (we'll draw specs next to/below button)
            btn.vehicle_info = {
                'name': vtype.name,
                'capacity': vtype.capacity_m3,
                'cost_per_km': vtype.cost_per_km,
                'range': vtype.max_range_km,
                'can_afford': can_afford
            }

            y_pos += btn_spacing + btn_height

        # Cancel button at bottom with spacing
        cancel_btn_y = modal_y + self.vehicle_modal.height - 60
        cancel_btn = Button(
            modal_x + (self.vehicle_modal.width - 200) // 2,
            cancel_btn_y,
            200,
            40,
            "Cancel",
            lambda: self._cancel_vehicle_purchase()
        )
        buttons.append(cancel_btn)

        # Pass balance as extra data
        extra_data = {'balance': self.engine.game_state.balance}
        self.vehicle_modal.show(content, buttons, extra_data)

    def _cancel_vehicle_purchase(self):
        """Handle canceling the vehicle modal and resume auto-planning if queued."""
        self.vehicle_modal.hide()
        self._maybe_execute_deferred_auto_plan(show_feedback=False)

    def purchase_vehicle(self, vehicle_type_name: str):
        """Purchase a vehicle."""
        vehicle_type = self.engine.vehicle_types[vehicle_type_name]
        vehicle_id = f"veh_{len(self.engine.game_state.fleet) + 1:03d}"

        if self.engine.game_state.purchase_vehicle(vehicle_type, vehicle_id):
            print(f"✓ Purchased {vehicle_type.name}")
            self.show_warning(f"Purchased {vehicle_type.name}!", Colors.PROFIT_POSITIVE)
            self.update_stats()
            self.vehicle_modal.hide()
            self.update_agent_previews()
            if self.mode == "AUTO":
                self.auto_plan_routes(show_feedback=False)
        else:
            self.show_warning("Not enough funds!", Colors.PROFIT_NEGATIVE)

    def _apply_manual_plan(self, routes: List[Route]) -> None:
        """Apply manual routes as the current plan."""
        if not routes:
            self.show_warning("No routes built! Assign packages before planning.", Colors.PROFIT_NEGATIVE)
            return

        self.mode = "MANUAL"
        self._set_mode_button_state(True)
        self.planned_routes = list(routes)
        self.render_routes = list(routes)
        self.planned_metrics = calculate_route_metrics(routes)
        self.engine.game_state.set_routes(routes)
        self.buttons['execute'].enabled = True
        self.buttons['next_day'].enabled = False
        self._update_planned_metrics_display()
        self._set_manual_preview(self.planned_metrics)

        profit = self.planned_metrics.get('total_profit', 0.0)
        color = Colors.PROFIT_POSITIVE if profit >= 0 else Colors.PROFIT_NEGATIVE
        self.show_warning(f"Manual plan ready! Profit ${profit:,.0f}. Execute when ready.", color)

    def on_execute_day(self):
        """Execute the planned routes or manual plan."""
        if self.mode == "MANUAL":
            if not self.manual_mode_manager:
                self.show_warning("Manual mode not initialized!", Colors.PROFIT_NEGATIVE)
                return
            manual_routes = self.manual_mode_manager.get_manual_routes(self.engine.delivery_map)
            if not manual_routes:
                self.show_warning("No routes built! Assign packages and select stops.", Colors.PROFIT_NEGATIVE)
                return
            self.engine.game_state.set_routes(manual_routes)
            self.planned_routes = manual_routes
        else:
            if not self.planned_routes:
                self.auto_plan_routes(show_feedback=True)
                if not self.planned_routes:
                    return

        print("\n[UI] Executing day...")
        if self.planned_routes:
            self.render_routes = list(self.planned_routes)
        self.engine.execute_day(self.selected_agent)

        for pkg in self.engine.game_state.packages_delivered:
            if pkg.id in self.package_status:
                self.package_status[pkg.id] = "delivered"

        self.planned_routes = []
        self.planned_metrics = None
        self.engine.game_state.set_routes([])
        self._set_manual_preview(None)
        self._set_auto_preview(None)

        self.buttons['execute'].enabled = False
        self.buttons['next_day'].enabled = True
        self._update_planned_metrics_display()
        self.autoplay_action = None

        last_day = self.engine.game_state.get_last_day_summary()
        if last_day:
            profit_color = Colors.PROFIT_POSITIVE if last_day.profit >= 0 else Colors.PROFIT_NEGATIVE
            severity_color = profit_color
            if last_day.popularity_delta < 0:
                severity_color = Colors.PROFIT_NEGATIVE
            elif last_day.popularity_delta > 0 and severity_color != Colors.PROFIT_NEGATIVE:
                severity_color = Colors.PROFIT_POSITIVE

            message = (
                f"Day complete! Profit {last_day.profit:+,.0f} | "
                f"Popularity {last_day.popularity_end} ({last_day.popularity_delta:+}) | "
                f"Demand {last_day.demand_tier}"
            )
            penalties = getattr(last_day, 'penalties', 0.0)
            if last_day.popularity_delta < 0:
                message += " – Reputation slipped, stabilize deliveries!"
            elif last_day.popularity_delta > 10:
                message += " – Demand is surging, prepare your fleet!"
            if penalties > 0:
                message += f" | Penalty -${penalties:,.0f}"
            self.show_warning(message, severity_color)

        self.update_stats()
        self.update_agent_previews()

    def on_next_day(self):
        """Advance to next day."""
        self.engine.advance_to_next_day()
        self.planned_routes = []
        self.planned_metrics = None
        self.package_status = {}
        self.buttons['execute'].enabled = False
        self.buttons['next_day'].enabled = False
        self.autoplay_action = None
        self.start_day_flow()

    def on_save(self):
        """Save game."""
        self.engine.save_game()
        self.show_warning("Game saved!", Colors.TEXT_ACCENT)
    def on_load(self):
        """Load saved game."""
        try:
            self.engine.load_game()
            # Reset UI state
            self.planned_routes = []
            self.planned_metrics = None
            self.package_status = {}

            # Clear planned metrics display
            self.planned_cost_stat.set_value("$0", Colors.TEXT_SECONDARY)
            self.planned_revenue_stat.set_value("$0", Colors.TEXT_SECONDARY)
            self.planned_profit_stat.set_value("$0", Colors.TEXT_SECONDARY)

            # Update stats
            self.update_stats()
            self.buttons['execute'].enabled = False
            self.buttons['next_day'].enabled = False
            self.start_day_flow()
            self.show_warning("Game loaded successfully!", Colors.PROFIT_POSITIVE)
            print(f"✓ Loaded game: Day {self.engine.game_state.current_day}, Balance ${self.engine.game_state.balance:.2f}")
        except FileNotFoundError:
            self.show_warning("No saved game found!", Colors.PROFIT_NEGATIVE)
            print("✗ No savegame.json file found")
        except Exception as e:
            self.show_warning(f"Error loading game!", Colors.PROFIT_NEGATIVE)
            print(f"✗ Error loading game: {e}")


    def on_stats(self):
        """Show statistics."""
        stats = self.engine.game_state.get_statistics()
        print("\n" + "="*50)
        print("GAME STATISTICS")
        print("="*50)
        for key, value in stats.items():
            print(f"{key}: {value}")
        print("="*50)
        self.show_warning("Stats printed to console", Colors.TEXT_ACCENT)

    def on_show_marketing(self):
        """Show marketing upgrade modal."""
        marketing_info = self.engine.game_state.get_marketing_info()

        content = [
            ("MARKETING & PACKAGE RATE", Colors.TEXT_ACCENT),
            ("", Colors.TEXT_PRIMARY),
            (f"Current Level: {marketing_info['level']}/5", Colors.TEXT_PRIMARY),
            (f"Daily Package Volume: {marketing_info['current_volume']:.1f}m³", Colors.PROFIT_POSITIVE),
            ("", Colors.TEXT_PRIMARY),
        ]

        if not marketing_info['is_max_level']:
            next_level = marketing_info['level'] + 1
            next_volume = marketing_info['next_level_volume']
            upgrade_cost = marketing_info['upgrade_cost']

            content.extend([
                (f"Next Level ({next_level}): {next_volume:.1f}m³/day", Colors.TEXT_SECONDARY),
                (f"Upgrade Cost: ${upgrade_cost:,}", Colors.TEXT_SECONDARY),
                ("", Colors.TEXT_PRIMARY),
                ("Higher marketing increases package volume", Colors.TEXT_ACCENT),
                ("   Grow your fleet to handle increased volume", Colors.TEXT_SECONDARY),
            ])
        else:
            content.extend([
                ("🎉 MAX LEVEL REACHED!", Colors.PROFIT_POSITIVE),
                ("You have maximum marketing coverage!", Colors.TEXT_SECONDARY),
            ])

        # Create buttons
        buttons = []
        modal_btn_x = self.marketing_modal.x + 100
        modal_btn_y = self.marketing_modal.y + 360

        if not marketing_info['is_max_level']:
            upgrade_btn = Button(
                modal_btn_x, modal_btn_y, 200, 40,
                f"Upgrade (${marketing_info['upgrade_cost']:,})",
                self.on_upgrade_marketing
            )
            upgrade_btn.enabled = marketing_info['can_afford']
            buttons.append(upgrade_btn)

            close_btn = Button(
                modal_btn_x + 220, modal_btn_y, 200, 40,
                "Close", lambda: self.marketing_modal.hide()
            )
            buttons.append(close_btn)
        else:
            close_btn = Button(
                modal_btn_x + 110, modal_btn_y, 200, 40,
                "Close", lambda: self.marketing_modal.hide()
            )
            buttons.append(close_btn)

        self.marketing_modal.show(content, buttons)

    def on_upgrade_marketing(self):
        """Upgrade marketing level."""
        old_info = self.engine.game_state.get_marketing_info()

        if self.engine.game_state.upgrade_marketing():
            new_info = self.engine.game_state.get_marketing_info()
            print(f"✓ Marketing upgraded to level {new_info['level']}")
            self.show_warning(
                f"Marketing upgraded! Now {new_info['current_volume']:.1f}m³/day",
                Colors.PROFIT_POSITIVE
            )
            self.update_stats()
            self.marketing_modal.hide()
        else:
            self.show_warning("Cannot upgrade marketing!", Colors.PROFIT_NEGATIVE)

    def on_show_comparison(self):
        """Show comparison between manual solution and algorithmic solutions."""
        if self.mode != "MANUAL":
            self.show_warning("Comparison only available in MANUAL mode!", Colors.TEXT_ACCENT)
            return

        if not self.manual_mode_manager:
            self.show_warning("Manual mode not initialized!", Colors.PROFIT_NEGATIVE)
            return

        manual_routes = self.manual_mode_manager.get_manual_routes(self.engine.delivery_map)
        if not manual_routes:
            self.show_warning("Build routes first to compare!", Colors.PROFIT_NEGATIVE)
            return

        # Calculate manual solution metrics
        from src.utils.metrics import calculate_route_metrics
        manual_metrics = calculate_route_metrics(manual_routes)

        # Test all agents
        agent_results = {}
        for agent_name in ["greedy", "greedy_2opt", "backtracking", "pruning_backtracking"]:
            if agent_name in self.engine.agents:
                metrics = self.engine.test_agent(agent_name)
                if metrics:
                    agent_results[agent_name] = metrics

        # Find best algorithmic solution
        best_agent = None
        best_profit = float('-inf')
        for agent_name, metrics in agent_results.items():
            if metrics['total_profit'] > best_profit:
                best_profit = metrics['total_profit']
                best_agent = agent_name

        # Build comparison content
        content = [
            ("🎯 YOUR MANUAL SOLUTION", Colors.TEXT_ACCENT),
            ("", Colors.TEXT_PRIMARY),
            (f"Routes: {len(manual_routes)}", Colors.TEXT_PRIMARY),
            (f"Distance: {manual_metrics['total_distance']:.1f}km", Colors.TEXT_SECONDARY),
            (f"Cost: ${manual_metrics['total_cost']:.0f}", Colors.PROFIT_NEGATIVE),
            (f"Revenue: ${manual_metrics['total_revenue']:.0f}", Colors.PROFIT_POSITIVE),
            (f"Profit: ${manual_metrics['total_profit']:.0f}",
             Colors.PROFIT_POSITIVE if manual_metrics['total_profit'] > 0 else Colors.PROFIT_NEGATIVE),
            ("", Colors.TEXT_PRIMARY),
            ("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", Colors.BORDER_LIGHT),
            ("", Colors.TEXT_PRIMARY),
        ]

        if best_agent:
            best_metrics = agent_results[best_agent]
            profit_diff = best_metrics['total_profit'] - manual_metrics['total_profit']
            profit_pct = (profit_diff / manual_metrics['total_profit'] * 100) if manual_metrics['total_profit'] != 0 else 0

            content.extend([
                (f"🤖 BEST ALGORITHM: {best_agent.upper()}", Colors.TEXT_ACCENT),
                ("", Colors.TEXT_PRIMARY),
                (f"Routes: {len(best_metrics['routes'])}", Colors.TEXT_PRIMARY),
                (f"Distance: {best_metrics['total_distance']:.1f}km", Colors.TEXT_SECONDARY),
                (f"Cost: ${best_metrics['total_cost']:.0f}", Colors.PROFIT_NEGATIVE),
                (f"Revenue: ${best_metrics['total_revenue']:.0f}", Colors.PROFIT_POSITIVE),
                (f"Profit: ${best_metrics['total_profit']:.0f}", Colors.PROFIT_POSITIVE),
                ("", Colors.TEXT_PRIMARY),
                ("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", Colors.BORDER_LIGHT),
                ("", Colors.TEXT_PRIMARY),
            ])

            if profit_diff > 0:
                content.extend([
                    ("📊 ANALYSIS", Colors.TEXT_ACCENT),
                    ("", Colors.TEXT_PRIMARY),
                    (f"Algorithm is ${profit_diff:.0f} more profitable!", Colors.PROFIT_POSITIVE),
                    (f"That's {abs(profit_pct):.1f}% better than your solution", Colors.TEXT_SECONDARY),
                    ("", Colors.TEXT_PRIMARY),
                    ("💡 TIP: Algorithms excel at:", Colors.TEXT_ACCENT),
                    ("  • Minimizing total distance", Colors.TEXT_SECONDARY),
                    ("  • Maximizing capacity usage", Colors.TEXT_SECONDARY),
                    ("  • Finding optimal stop sequences", Colors.TEXT_SECONDARY),
                ])
            elif profit_diff < 0:
                content.extend([
                    ("🎉 EXCELLENT WORK!", Colors.PROFIT_POSITIVE),
                    ("", Colors.TEXT_PRIMARY),
                    (f"Your solution beats the algorithm by ${abs(profit_diff):.0f}!", Colors.PROFIT_POSITIVE),
                    (f"That's {abs(profit_pct):.1f}% better!", Colors.PROFIT_POSITIVE),
                    ("", Colors.TEXT_PRIMARY),
                    ("You have a natural talent for optimization!", Colors.TEXT_ACCENT),
                ])
            else:
                content.extend([
                    ("🎯 PERFECT MATCH!", Colors.PROFIT_POSITIVE),
                    ("", Colors.TEXT_PRIMARY),
                    ("Your solution equals the algorithm!", Colors.TEXT_ACCENT),
                    ("Great optimization skills!", Colors.TEXT_SECONDARY),
                ])

        # Create close button
        modal_btn_x = self.comparison_modal.x + 275
        modal_btn_y = self.comparison_modal.y + 520
        close_btn = Button(modal_btn_x, modal_btn_y, 200, 40, "Close", lambda: self.comparison_modal.hide())

        self.comparison_modal.show(content, [close_btn])

    def show_warning(self, message: str, color):
        """Show warning message."""
        self.warning_message = message
        self.warning_color = color

    def update_stats(self):
        """Update all stat displays."""
        if not self.engine.game_state:
            return

        state = self.engine.game_state

        self.day_stat.set_value(str(state.current_day))

        balance_color = Colors.PROFIT_POSITIVE if state.balance > 0 else Colors.PROFIT_NEGATIVE
        if state.balance >= 1000:
            balance_str = f"${state.balance/1000:.1f}K"
        else:
            balance_str = f"${state.balance:.0f}"
        self.balance_stat.set_value(balance_str, balance_color)

        tier_label = state.current_demand_tier.value if hasattr(state.current_demand_tier, 'value') else str(state.current_demand_tier)
        pop_color = Colors.TEXT_ACCENT
        if state.popularity_score >= 700:
            pop_color = Colors.PROFIT_POSITIVE
        elif state.popularity_score <= 200:
            pop_color = Colors.PROFIT_NEGATIVE
        pop_value = f"{state.popularity_score} ({tier_label})"
        self.popularity_stat.set_value(pop_value, pop_color)

        self.fleet_stat.set_value(f"{len(state.fleet)} veh")
        self.packages_stat.set_value(f"{len(state.packages_pending)}")

        # Capacity
        total_pkg_volume = sum(pkg.volume_m3 for pkg in state.packages_pending) if state.packages_pending else 0
        fleet_capacity = sum(v.vehicle_type.capacity_m3 for v in state.fleet)
        capacity_color = Colors.PROFIT_POSITIVE if total_pkg_volume <= fleet_capacity else Colors.PROFIT_NEGATIVE
        self.capacity_stat.set_value(f"{total_pkg_volume:.0f}/{fleet_capacity:.0f}", capacity_color)
        self._update_planned_metrics_display()

    def update_hover_tooltip(self, mouse_pos):
        """Update tooltip based on mouse position."""
        if not self.engine.game_state:
            self.tooltip.hide()
            return

        # Check packages
        if self.engine.game_state.packages_pending:
            pkg = self.map_renderer.get_package_at_mouse(mouse_pos, self.engine.game_state.packages_pending)
            if pkg:
                status = self.package_status.get(pkg.id, "pending")
                status_text = "DELIVERED" if status == "delivered" else "PENDING"
                tooltip_text = (
                    f"Status: {status_text}\n"
                    f"ID: {pkg.id}\n"
                    f"Volume: {pkg.volume_m3} m³\n"
                    f"Payment: ${pkg.payment}\n"
                    f"Priority: {pkg.priority}"
                )
                if getattr(pkg, 'is_rush', False):
                    tooltip_text += "\nRush order"
                self.tooltip.show(tooltip_text, (mouse_pos[0] + 15, mouse_pos[1] + 15))
                return

        # Check vehicles
        if self.engine.game_state.fleet:
            veh = self.map_renderer.get_vehicle_at_mouse(mouse_pos, self.engine.game_state.fleet)
            if veh:
                tooltip_text = (
                    f"Vehicle: {veh.vehicle_type.name}\n"
                    f"ID: {veh.id}\n"
                    f"Capacity: {veh.vehicle_type.capacity_m3} m³\n"
                    f"Cost: ${veh.vehicle_type.cost_per_km}/km\n"
                    f"Range: {veh.vehicle_type.max_range_km} km"
                )
                self.tooltip.show(tooltip_text, (mouse_pos[0] + 15, mouse_pos[1] + 15))
                return

        # No hover
        self.tooltip.hide()

    # ==================== MAIN LOOP ====================

    def handle_events(self):
        """Handle all events."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    # Close modals first, then quit
                    if self.vehicle_modal.visible:
                        self.vehicle_modal.hide()
                        self._maybe_execute_deferred_auto_plan(show_feedback=False)
                    elif self.capacity_warning_modal.visible:
                        self.capacity_warning_modal.hide()
                        self._maybe_execute_deferred_auto_plan(show_feedback=True)
                    elif self.marketing_modal.visible:
                        self.marketing_modal.hide()
                    elif self.day_summary_modal.visible:
                        self.day_summary_modal.hide()
                        self._maybe_execute_deferred_auto_plan(show_feedback=True)
                    elif self.comparison_modal.visible:
                        self.comparison_modal.hide()
                    elif self.mode == "MANUAL" and self.manual_mode_manager and self.manual_mode_manager.active:
                        self.on_mode_auto()
                        continue
                    else:
                        self.running = False

            # Modal events (priority)
            if self.day_summary_modal.visible:
                self.day_summary_modal.handle_event(event)
                continue  # Don't process other events

            if self.vehicle_modal.visible:
                self.vehicle_modal.handle_event(event)
                continue  # Don't process other events

            if self.capacity_warning_modal.visible:
                self.capacity_warning_modal.handle_event(event)
                continue

            if self.marketing_modal.visible:
                self.marketing_modal.handle_event(event)
                continue

            if self.comparison_modal.visible:
                self.comparison_modal.handle_event(event)
                continue

            manual_overlay_active = (
                self.mode == "MANUAL"
                and self.manual_mode_manager
                and self.manual_mode_manager.active
            )

            if manual_overlay_active:
                result = self.manual_mode_manager.handle_event(event, self.engine.delivery_map)

                if result['action'] == 'package_assigned':
                    pkg = result['data']['package']
                    veh = result['data']['vehicle']
                    self.show_warning(f"Assigned {pkg.id} to {veh.id}", Colors.PROFIT_POSITIVE)

                elif result['action'] == 'capacity_exceeded':
                    veh = result['data']
                    self.show_warning(f"Capacity exceeded for {veh.id}", Colors.PROFIT_NEGATIVE)

                elif result['action'] == 'vehicle_selected':
                    if result['data']:
                        self.show_warning(f"Selected {result['data'].vehicle.id} - Click packages on map", Colors.TEXT_ACCENT)

                elif result['action'] == 'package_selected':
                    card = result['data']
                    if card:
                        pkg_id = card.package.id
                        if self.manual_mode_manager.selected_vehicle:
                            veh = self.manual_mode_manager.selected_vehicle.vehicle
                            self.show_warning(f"{pkg_id[-4:]} ready for {veh.id[-3:]} - press Assign", Colors.TEXT_ACCENT)
                        else:
                            self.show_warning(f"Selected package {pkg_id[-4:]} - choose a vehicle", Colors.TEXT_ACCENT)

                elif result['action'] == 'plan_routes':
                    routes = result.get('data') or []
                    if routes:
                        self.manual_mode_manager.active = False
                        self._apply_manual_plan(routes)
                    else:
                        self.show_warning("Assign packages before planning!", Colors.PROFIT_NEGATIVE)
                    continue

                elif result['action'] == 'assignments_cleared':
                    if result.get('data'):
                        self.show_warning("Cleared manual assignments.", Colors.TEXT_SECONDARY)
                    self._set_manual_preview(None)
                    continue

                elif result['action'] == 'close':
                    self.on_mode_auto()
                    continue

                if event.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP, pygame.MOUSEMOTION, pygame.MOUSEWHEEL):
                    continue

            # Collapsible panels
            toggled = False
            for panel in (self.stats_panel, self.agent_panel, self.custom_agent_panel):
                if isinstance(panel, CollapsiblePanel) and panel.handle_event(event):
                    toggled = True
            if toggled:
                self._reflow_sidebar_layout()
                continue

            # Regular button events
            for button in self.buttons.values():
                button.handle_event(event)

            # Mode toggle buttons
            if not (isinstance(self.mode_panel, CollapsiblePanel) and self.mode_panel.collapsed):
                self.mode_auto_btn.handle_event(event)
                self.mode_manual_btn.handle_event(event)

            # Radio buttons
            if event.type == pygame.MOUSEBUTTONDOWN:
                all_radios = self.agent_radios + self.custom_agent_radios
                if not self.agent_panel.collapsed:
                    for i, radio in enumerate(self.agent_radios):
                        if radio.handle_event(event):
                            for other in all_radios:
                                if other is not radio:
                                    other.selected = False
                            self.selected_agent = radio.value
                            self._set_auto_preview(self.agent_metrics_preview.get(self.selected_agent))
                            if self.mode == "AUTO":
                                self.auto_plan_routes(show_feedback=True)
                            break
                if not self.custom_agent_panel.collapsed:
                    for radio in self.custom_agent_radios:
                        if radio.handle_event(event):
                            for other in all_radios:
                                if other is not radio:
                                    other.selected = False
                            self.selected_agent = radio.value
                            self._set_auto_preview(self.agent_metrics_preview.get(self.selected_agent))
                            if self.mode == "AUTO":
                                self.auto_plan_routes(show_feedback=True)
                            break

            if event.type == pygame.MOUSEMOTION:
                if not self.agent_panel.collapsed:
                    for radio in self.agent_radios:
                        radio.handle_event(event)
                else:
                    for radio in self.agent_radios:
                        radio.hovered = False

                if not self.custom_agent_panel.collapsed:
                    for radio in self.custom_agent_radios:
                        radio.handle_event(event)
                else:
                    for radio in self.custom_agent_radios:
                        radio.hovered = False

                # Check for hover over packages/vehicles
                self.update_hover_tooltip(event.pos)

    def render(self):
        """Render everything."""
        self.screen.fill(Colors.BG_DARK)

        self.render_title_bar()
        self.render_map()
        self.render_sidebar()

        # Render manual mode interface if active
        if self.mode == "MANUAL" and self.manual_mode_manager:
            self.manual_mode_manager.render(self.screen)

        # Modals on top
        self.day_summary_modal.render(self.screen)
        self.vehicle_modal.render(self.screen)
        self.capacity_warning_modal.render(self.screen)
        self.marketing_modal.render(self.screen)
        self.comparison_modal.render(self.screen)

        self.tooltip.render(self.screen)

        pygame.display.flip()

    def update(self, dt: float):
        """Update per-frame systems."""
        self.process_autoplay(dt)

    def render_title_bar(self):
        """Render title bar."""
        title_rect = pygame.Rect(0, 0, WINDOW_WIDTH, TITLE_BAR_HEIGHT)
        pygame.draw.rect(self.screen, Colors.TITLE_BG, title_rect)

        title = render_text("DELIVERY FLEET MANAGER", FontSizes.TITLE, Colors.TEXT_ACCENT, bold=True)
        self.screen.blit(title, (20, 20))

        subtitle = render_text("Art of Programming - Route Optimization", FontSizes.SMALL, Colors.TEXT_SECONDARY)
        self.screen.blit(subtitle, (20, 58))

        # Status - Improved rendering with panel background
        if self.engine.game_state:
            status_x = WINDOW_WIDTH - 280
            status_y = 15

            # Draw background panel for status
            status_panel = pygame.Rect(status_x - 15, status_y - 5, 270, 70)
            pygame.draw.rect(self.screen, Colors.PANEL_BG, status_panel, border_radius=8)
            pygame.draw.rect(self.screen, Colors.BORDER_LIGHT, status_panel, 2, border_radius=8)

            # Day label and value
            day_label = render_text("Day", FontSizes.SMALL, Colors.TEXT_SECONDARY)
            self.screen.blit(day_label, (status_x, status_y))

            day_value = render_text(str(self.engine.game_state.current_day), FontSizes.HEADING, Colors.TEXT_ACCENT, bold=True)
            self.screen.blit(day_value, (status_x, status_y + 18))

            # Balance label and value
            bal_x = status_x + 120
            bal_label = render_text("Balance", FontSizes.SMALL, Colors.TEXT_SECONDARY)
            self.screen.blit(bal_label, (bal_x, status_y))

            bal_color = Colors.PROFIT_POSITIVE if self.engine.game_state.balance >= 0 else Colors.PROFIT_NEGATIVE
            bal_text = f"${self.engine.game_state.balance:,.0f}"
            bal_value = render_text(bal_text, FontSizes.HEADING, bal_color, bold=True)
            self.screen.blit(bal_value, (bal_x, status_y + 18))

    def render_map(self):
        """Render the map."""
        self.map_surface.fill(Colors.MAP_BG)
        self.map_renderer.render_map_background()
        self.map_renderer.render_depot(pulse=True)

        if self.engine.game_state and self.engine.game_state.packages_pending:
            for pkg in self.engine.game_state.packages_pending:
                status = self.package_status.get(pkg.id, "pending")
                self.map_renderer.render_package(pkg, status)

        routes_to_draw = self.planned_routes if self.planned_routes else self.render_routes
        if routes_to_draw:
            for i, route in enumerate(routes_to_draw):
                # Assign distinct color to each route
                route_color = Colors.ROUTE_COLORS[i % len(Colors.ROUTE_COLORS)]
                self.map_renderer.render_route(route, color=route_color, style="solid")

        # Render manual mode routes (for ALL vehicles, not just current page)
        if self.mode == "MANUAL" and self.manual_mode_manager:
            route_data = self.manual_mode_manager.get_all_vehicle_routes_for_rendering(self.engine.delivery_map)
            for i, (veh, packages, stops) in enumerate(route_data):
                # Create a temporary route for rendering
                from src.models.route import Route
                temp_route = Route(
                    vehicle=veh,
                    packages=packages,
                    stops=stops,
                    delivery_map=self.engine.delivery_map
                )
                route_color = Colors.ROUTE_COLORS[i % len(Colors.ROUTE_COLORS)]
                self.map_renderer.render_route(temp_route, color=route_color, style="solid")

        if self.engine.game_state:
            for vehicle in self.engine.game_state.fleet:
                self.map_renderer.render_vehicle(vehicle)

        self.screen.blit(self.map_surface, (MAP_X, MAP_Y))
        map_rect = pygame.Rect(MAP_X, MAP_Y, MAP_WIDTH, MAP_HEIGHT)
        pygame.draw.rect(self.screen, Colors.BORDER_LIGHT, map_rect, 2)

        # Render legend below map
        self.render_map_legend()

    def render_map_legend(self):
        """Render horizontal legend below the map."""
        legend_y = MAP_Y + MAP_HEIGHT + 10
        legend_width = MAP_WIDTH
        legend_height = 70  # Reduced from 80
        legend_x = MAP_X

        # Background
        legend_rect = pygame.Rect(legend_x, legend_y, legend_width, legend_height)
        pygame.draw.rect(self.screen, Colors.PANEL_BG, legend_rect, border_radius=5)
        pygame.draw.rect(self.screen, Colors.BORDER_LIGHT, legend_rect, 2, border_radius=5)

        # Title - Use SysFont for better rendering with smaller size
        font_title = pygame.font.SysFont('arial', 13, bold=True)
        title = font_title.render("MAP LEGEND", True, Colors.TEXT_ACCENT)
        self.screen.blit(title, (legend_x + 10, legend_y + 6))

        # Legend items in 2 rows, 3 columns - Smaller font
        font_small = pygame.font.SysFont('arial', 12)

        # Column 1
        x_col1 = legend_x + 15
        y_row1 = legend_y + 28
        y_row2 = legend_y + 48

        # Depot
        pygame.draw.circle(self.screen, Colors.DEPOT, (x_col1, y_row1), 5)
        text = font_small.render("Depot", True, Colors.TEXT_PRIMARY)
        self.screen.blit(text, (x_col1 + 10, y_row1 - 5))

        # Pending
        pygame.draw.circle(self.screen, Colors.PACKAGE_PENDING, (x_col1, y_row2), 4)
        text = font_small.render("Pending", True, Colors.TEXT_PRIMARY)
        self.screen.blit(text, (x_col1 + 10, y_row2 - 5))

        # Column 2
        x_col2 = legend_x + 135

        # Delivered
        pygame.draw.circle(self.screen, Colors.PACKAGE_DELIVERED, (x_col2, y_row1), 4)
        text = font_small.render("Delivered", True, Colors.TEXT_PRIMARY)
        self.screen.blit(text, (x_col2 + 10, y_row1 - 5))

        # High priority
        pygame.draw.circle(self.screen, Colors.PACKAGE_PRIORITY_HIGH, (x_col2, y_row2), 4)
        text = font_small.render("Priority", True, Colors.TEXT_PRIMARY)
        self.screen.blit(text, (x_col2 + 10, y_row2 - 5))

        # Column 3
        x_col3 = legend_x + 260

        # Route
        pygame.draw.line(self.screen, Colors.ROUTE_COLORS[0],
                        (x_col3, y_row1), (x_col3 + 18, y_row1), 2)
        # Arrow
        pygame.draw.polygon(self.screen, Colors.ROUTE_COLORS[0], [
            (x_col3 + 18, y_row1),
            (x_col3 + 14, y_row1 - 3),
            (x_col3 + 14, y_row1 + 3)
        ])
        text = font_small.render("Route", True, Colors.TEXT_PRIMARY)
        self.screen.blit(text, (x_col3 + 24, y_row1 - 5))

        # Vehicle
        veh_rect = pygame.Rect(x_col3 + 2, y_row2 - 3, 10, 7)
        pygame.draw.rect(self.screen, Colors.VEHICLE_ACTIVE, veh_rect, border_radius=1)
        text = font_small.render("Vehicle", True, Colors.TEXT_PRIMARY)
        self.screen.blit(text, (x_col3 + 24, y_row2 - 5))

        # Column 4 - Hint (more compact)
        x_col4 = legend_x + 420
        hint_font = pygame.font.SysFont('arial', 11)
        hint1 = hint_font.render("💡 Hover packages/vehicles", True, Colors.TEXT_ACCENT)
        hint2 = hint_font.render("   for details", True, Colors.TEXT_ACCENT)
        self.screen.blit(hint1, (x_col4, y_row1 - 5))
        self.screen.blit(hint2, (x_col4, y_row2 - 5))

    def render_sidebar(self):
        """Render sidebar."""
        # Panels
        self.stats_panel.render(self.screen)
        self.mode_panel.render(self.screen)
        self.agent_panel.render(self.screen)
        self.custom_agent_panel.render(self.screen)
        self.controls_panel.render(self.screen)

        if not self.stats_panel.collapsed:
            self.day_stat.render(self.screen)
            self.balance_stat.render(self.screen)
            self.popularity_stat.render(self.screen)

            divider_y = self.stats_panel.rect.y + 85
            pygame.draw.line(self.screen, Colors.BORDER_LIGHT,
                            (self.stats_panel.rect.x + 15, divider_y),
                            (self.stats_panel.rect.x + self.stats_panel.rect.width - 15, divider_y), 1)

            self.fleet_stat.render(self.screen)
            self.packages_stat.render(self.screen)
            self.capacity_stat.render(self.screen)

            divider_y2 = self.stats_panel.rect.y + 140
            pygame.draw.line(self.screen, Colors.BORDER_LIGHT,
                            (self.stats_panel.rect.x + 15, divider_y2),
                            (self.stats_panel.rect.x + self.stats_panel.rect.width - 15, divider_y2), 1)

            self.planned_cost_stat.render(self.screen)
            self.planned_revenue_stat.render(self.screen)
            self.planned_profit_stat.render(self.screen)

        # Mode toggle buttons
        if not isinstance(self.mode_panel, CollapsiblePanel) or not self.mode_panel.collapsed:
            self.mode_auto_btn.render(self.screen)
            self.mode_manual_btn.render(self.screen)

            # Highlight selected mode
            if self.mode == "AUTO":
                highlight_rect = pygame.Rect(
                    self.mode_auto_btn.rect.x - 2,
                    self.mode_auto_btn.rect.y - 2,
                    self.mode_auto_btn.rect.width + 4,
                    self.mode_auto_btn.rect.height + 4
                )
            else:
                highlight_rect = pygame.Rect(
                    self.mode_manual_btn.rect.x - 2,
                    self.mode_manual_btn.rect.y - 2,
                    self.mode_manual_btn.rect.width + 4,
                    self.mode_manual_btn.rect.height + 4
                )
            pygame.draw.rect(self.screen, Colors.TEXT_ACCENT, highlight_rect, 3, border_radius=7)

            auto_surface = self.mode_preview_font.render(self.auto_revenue_preview, True, self.auto_revenue_color)
            manual_surface = self.mode_preview_font.render(self.manual_revenue_preview, True, self.manual_revenue_color)
            auto_x = self.mode_auto_btn.rect.centerx - auto_surface.get_width() // 2
            auto_y = self.mode_auto_btn.rect.bottom + 6
            manual_x = self.mode_manual_btn.rect.centerx - manual_surface.get_width() // 2
            manual_y = self.mode_manual_btn.rect.bottom + 6
            self.screen.blit(auto_surface, (auto_x, auto_y))
            self.screen.blit(manual_surface, (manual_x, manual_y))

        # Standard agent radios
        if not self.agent_panel.collapsed:
            for radio in self.agent_radios:
                radio.render(self.screen)

        if not self.custom_agent_panel.collapsed:
            for radio in self.custom_agent_radios:
                radio.render(self.screen)

        # Buttons
        for button in self.buttons.values():
            button.render(self.screen)

        # Warning message
        if self.warning_message:
            font = pygame.font.Font(None, FontSizes.SMALL)
            # Word wrap
            words = self.warning_message.split()
            lines = []
            current_line = ""
            for word in words:
                test_line = current_line + " " + word if current_line else word
                if font.size(test_line)[0] < self.warning_rect.width - 20:
                    current_line = test_line
                else:
                    lines.append(current_line)
                    current_line = word
            if current_line:
                lines.append(current_line)

            y_offset = self.warning_rect.y + 10
            for line in lines:
                text = font.render(line, True, self.warning_color)
                text_rect = text.get_rect(center=(self.warning_rect.centerx, y_offset))
                self.screen.blit(text, text_rect)
                y_offset += 20

    def run(self):
        """Main game loop."""
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0
            self.handle_events()
            self.update(dt)
            self.render()

        pygame.quit()
        print("\nThank you for playing!")


def main():
    """Entry point."""
    try:
        app = DeliveryFleetApp()
        app.run()
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        pygame.quit()


if __name__ == "__main__":
    main()
