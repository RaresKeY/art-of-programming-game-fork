"""
Font helpers for the Delivery Fleet Pygame UI.

Provides a light-weight wrapper around pygame.font to keep text rendering
consistent across modules while avoiding repeated font construction.
"""

from functools import lru_cache
from typing import Tuple

import pygame


DEFAULT_FONT_FAMILY = "arial"


@lru_cache(maxsize=32)
def _get_font(size: int, bold: bool = False, italic: bool = False) -> pygame.font.Font:
    """Return a cached pygame font with the given style."""
    return pygame.font.SysFont(DEFAULT_FONT_FAMILY, size, bold=bold, italic=italic)


def render_text(
    text: str,
    size: int,
    color: Tuple[int, int, int],
    *,
    bold: bool = False,
    italic: bool = False,
) -> pygame.Surface:
    """
    Render a text surface using the shared font settings.

    Args:
        text: Text to render.
        size: Font size in points.
        color: RGB tuple.
        bold: Whether to render text in bold.
        italic: Whether to render text in italic.

    Returns:
        Pygame Surface with rendered text.
    """
    font = _get_font(size, bold=bold, italic=italic)
    return font.render(text, True, color)
