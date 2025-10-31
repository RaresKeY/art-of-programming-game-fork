"""
UI Constants and Configuration for Pygame interface.

Defines colors, fonts, layout dimensions, and other visual constants.
"""

# Layout Dimensions
MAP_WIDTH = 800
MAP_HEIGHT = 600
MAP_X = 0
MAP_Y = 100  # Below title bar

SIDEBAR_WIDTH = 400
SIDEBAR_X = MAP_WIDTH
SIDEBAR_GAP = 20
SECONDARY_SIDEBAR_WIDTH = 400
SIDEBAR_RIGHT_X = SIDEBAR_X + SIDEBAR_WIDTH + SIDEBAR_GAP

# Window Dimensions
WINDOW_WIDTH = MAP_WIDTH + SIDEBAR_WIDTH + SIDEBAR_GAP + SECONDARY_SIDEBAR_WIDTH
WINDOW_HEIGHT = 1000  # Back to standard, will use scrolling for manual mode if needed
FPS = 60

TITLE_BAR_HEIGHT = 100
METRICS_BAR_HEIGHT = 100
METRICS_BAR_Y = 700

# Panel Dimensions
STATS_PANEL_HEIGHT = 200
AGENT_PANEL_HEIGHT = 300
CONTROLS_PANEL_HEIGHT = 200

# Map Settings
MAP_PADDING = 40  # Padding around map edges
GRID_SPACING = 50  # Pixels between grid lines

# Colors
class Colors:
    """Color palette for the application."""

    # Background
    BG_DARK = (25, 30, 40)
    BG_LIGHT = (245, 247, 250)
    PANEL_BG = (45, 52, 65)
    TITLE_BG = (35, 42, 55)

    # Map
    DEPOT = (255, 200, 0)           # Golden yellow
    GRID = (60, 70, 85)             # Subtle grid
    MAP_BG = (35, 40, 50)           # Map background

    # Packages
    PACKAGE_PENDING = (100, 150, 255)   # Blue
    PACKAGE_DELIVERED = (50, 200, 100)  # Green
    PACKAGE_IN_TRANSIT = (255, 200, 100)  # Orange
    PACKAGE_PRIORITY_HIGH = (255, 100, 100)  # Red

    # Routes (cycling colors for different vehicles)
    ROUTE_COLORS = [
        (255, 100, 100),  # Red
        (100, 200, 255),  # Blue
        (100, 255, 150),  # Green
        (255, 200, 100),  # Orange
        (200, 100, 255),  # Purple
        (255, 255, 100),  # Yellow
    ]

    # Vehicles
    VEHICLE_ACTIVE = (255, 220, 0)     # Gold
    VEHICLE_IDLE = (150, 150, 150)     # Grey

    # UI Elements
    BUTTON_NORMAL = (60, 120, 200)
    BUTTON_HOVER = (80, 150, 230)
    BUTTON_ACTIVE = (40, 100, 180)
    BUTTON_DISABLED = (80, 85, 95)

    TEXT_PRIMARY = (240, 245, 250)
    TEXT_SECONDARY = (180, 190, 200)
    TEXT_ACCENT = (100, 200, 255)
    TEXT_DARK = (30, 35, 45)

    # Stats
    PROFIT_POSITIVE = (50, 200, 100)
    PROFIT_NEGATIVE = (255, 80, 80)
    NEUTRAL = (200, 200, 200)

    # Borders
    BORDER_LIGHT = (80, 90, 105)
    BORDER_DARK = (20, 25, 35)


# Font Sizes
class FontSizes:
    """Font size constants."""
    TITLE = 32         # Larger title
    HEADING = 22       # Larger headings
    SUBHEADING = 18    # Larger subheadings
    BODY = 18          # Even larger body text
    SMALL = 16         # Larger for tooltips/legend (was 14)
    TINY = 12          # Slightly larger tiny text


# Animation Settings
ANIMATION_SPEED = 100  # km/h for vehicle movement
COUNTER_ANIMATION_SPEED = 0.05  # Speed for number counting animations

# Package Display
PACKAGE_RADIUS = 6  # Pixel radius for package markers
PACKAGE_HOVER_RADIUS = 10  # Enlarged on hover

# Depot Display
DEPOT_RADIUS = 15
DEPOT_PULSE_RANGE = (15, 20)  # Min/max for pulsing animation

# Vehicle Display
VEHICLE_SIZE = 12  # Size of vehicle icon/marker

# Button Settings
BUTTON_PADDING = 10
BUTTON_MARGIN = 8
BUTTON_HEIGHT = 40

# Tooltip Settings
TOOLTIP_BG = (50, 55, 65)
TOOLTIP_BORDER = (100, 110, 125)
TOOLTIP_PADDING = 8
TOOLTIP_DELAY = 500  # milliseconds before showing tooltip

# Grid Settings
SHOW_GRID = True
SHOW_COORDINATES = True  # Show km coordinates on axes

# Z-Index (rendering order)
Z_MAP_BG = 0
Z_GRID = 1
Z_ROUTES = 2
Z_PACKAGES = 3
Z_VEHICLES = 4
Z_DEPOT = 5
Z_UI = 10
Z_TOOLTIP = 20
