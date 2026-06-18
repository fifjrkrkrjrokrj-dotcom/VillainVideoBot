"""
Telethon button styling system with auto-pattern monkeypatch.

Port from Villainaddbot/utils.py — ports styled_button(), style_keyboard(),
and TelegramClient monkeypatch for automatic button styling.

Pattern: danger (row 0) → primary (row 1) → success (row 2) → repeat
"""

import logging
from telethon import Button
from telethon import TelegramClient

logger = logging.getLogger(__name__)


def styled_button(text: str, callback_data: str, style: str = "primary"):
    """
    Creates an inline button with style support.
    Falls back gracefully for older Telethon versions.

    Args:
        text: Button display text
        callback_data: Callback data for button press
        style: Color style - "primary" (blue), "danger" (red), "success" (green)

    Returns:
        Button: Styled Telethon Button object with style attached
    """
    try:
        return Button.inline(text, data=callback_data, style=style)
    except TypeError:
        btn = Button.inline(text, data=callback_data)
        try:
            btn.style = style
        except AttributeError:
            setattr(btn, "style", style)
        return btn


SMART_STYLES = {
    "destructive": {"keywords": ["delete", "stop", "cancel", "reject", "remove", "block", "danger", "clear"],
                    "style": "danger"},
    "constructive": {"keywords": ["start", "approve", "accept", "confirm", "verify", "purchase", "unlock", "join",
                                   "subscribe"],
                     "style": "success"},
}


def detect_smart_style(text: str) -> str | None:
    """Detect if button text suggests a destructive or constructive action."""
    lower = text.lower()
    for category in ("destructive", "constructive"):
        for kw in SMART_STYLES[category]["keywords"]:
            if kw in lower:
                return SMART_STYLES[category]["style"]
    return None


def style_keyboard(buttons):
    """
    Automatically styles keyboard buttons in a repeating pattern.

    Pattern: danger (red) → primary (blue) → success (green) → repeat

    Smart detection: buttons with destructive keywords stay "danger",
    constructive keywords stay "success", overriding the pattern.

    Args:
        buttons: Single button, 1D list, or 2D grid of buttons

    Returns:
        Styled buttons in the same format as input
    """
    if not buttons:
        return buttons

    was_single = not isinstance(buttons, (list, tuple))
    was_1d = False

    if was_single:
        grid = [[buttons]]
    elif buttons and not isinstance(buttons[0], (list, tuple)):
        was_1d = True
        grid = [list(buttons)]
    else:
        grid = [list(row) for row in buttons]

    styles = ["danger", "primary", "success"]

    for row_idx, row in enumerate(grid):
        pattern_style = styles[row_idx % len(styles)]

        for btn in row:
            if not hasattr(btn, "text"):
                continue

            smart_style = detect_smart_style(btn.text)
            chosen_style = smart_style if smart_style else pattern_style

            try:
                from telethon.tl.types import KeyboardButtonStyle

                icon = None
                existing = getattr(btn, "style", None)
                if existing and hasattr(existing, "icon"):
                    icon = existing.icon

                style_map = {
                    "primary": KeyboardButtonStyle(bg_primary=True, icon=icon),
                    "danger": KeyboardButtonStyle(bg_danger=True, icon=icon),
                    "success": KeyboardButtonStyle(bg_success=True, icon=icon),
                }
                btn.style = style_map.get(chosen_style)
            except (ImportError, AttributeError, TypeError):
                try:
                    btn.style = chosen_style
                except AttributeError:
                    setattr(btn, "style", chosen_style)

    if was_single:
        return grid[0][0]
    if was_1d:
        return grid[0]
    return grid


orig_send_message = TelegramClient.send_message
orig_edit_message = TelegramClient.edit_message
orig_send_file = TelegramClient.send_file


async def patched_send_message(self, entity, message=None, *args, **kwargs):
    if "buttons" in kwargs:
        kwargs["buttons"] = style_keyboard(kwargs["buttons"])
    return await orig_send_message(self, entity, message, *args, **kwargs)


async def patched_edit_message(self, entity, message=None, *args, **kwargs):
    if "buttons" in kwargs:
        kwargs["buttons"] = style_keyboard(kwargs["buttons"])
    return await orig_edit_message(self, entity, message, *args, **kwargs)


async def patched_send_file(self, entity, file, *args, **kwargs):
    if "buttons" in kwargs:
        kwargs["buttons"] = style_keyboard(kwargs["buttons"])
    return await orig_send_file(self, entity, file, *args, **kwargs)


TelegramClient.send_message = patched_send_message
TelegramClient.edit_message = patched_edit_message
TelegramClient.send_file = patched_send_file

logger.info("Button styling monkeypatch applied: TelegramClient.send_message, edit_message, send_file")
