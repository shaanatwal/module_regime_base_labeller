# Save this file as style_manager.py
from PyQt6.QtGui import QColor
from PyQt6.QtCore import QSettings, Qt

# A dictionary holding the application's default appearance settings.
# This is the "single source of truth" for the default look.
DEFAULT_STYLE_SETTINGS = {
    # Candle & Volume Colors
    "colors/up_candle": QColor(0, 204, 0).name(),
    "colors/down_candle": QColor(204, 0, 0).name(),
    "colors/up_wick": QColor(180, 180, 180).name(),
    "colors/down_wick": QColor(180, 180, 180).name(),
    "colors/up_volume": QColor(0, 204, 0, 180).name(), # Includes alpha
    "colors/down_volume": QColor(204, 0, 0, 180).name(), # Includes alpha
    
    # Line Colors
    "lines/crosshair": QColor(220, 220, 220, 150).name(),
    "lines/price_grid": QColor(80, 80, 80).name(),
    "lines/time_grid": QColor(80, 80, 80).name(),
    
    # Line Properties
    "props/crosshair_width": 1,
    "props/crosshair_style": "DashLine", # Qt.PenStyle enum name
    "props/price_grid_width": 1,
    "props/price_grid_style": "DotLine",
    "props/time_grid_width": 1,
    "props/time_grid_style": "DashLine",

    # Background
    "background/mode": "Solid", # "Solid" or "Gradient"
    "background/color1": QColor(25, 25, 25).name(),
    "background/color2": QColor(55, 55, 55).name(),
    "background/gradient_direction": "Vertical", # "Vertical" or "Horizontal"
    
    # Other
    "other/volume_pane_ratio": 0.25,
}

PEN_STYLE_MAP = {
    "SolidLine": Qt.PenStyle.SolidLine,
    "DashLine": Qt.PenStyle.DashLine,
    "DotLine": Qt.PenStyle.DotLine,
    "DashDotLine": Qt.PenStyle.DashDotLine,
}
REVERSE_PEN_STYLE_MAP = {v: k for k, v in PEN_STYLE_MAP.items()}

class StyleManager:
    """Handles loading, saving, and managing all visual style settings."""
    def __init__(self):
        self.settings = QSettings()

    def get_value(self, key, default_value=None):
        """Retrieves a value from QSettings, using the master default if not provided."""
        if default_value is None:
            default_value = DEFAULT_STYLE_SETTINGS.get(key)
        return self.settings.value(key, default_value)

    def set_value(self, key, value):
        """Saves a value to QSettings."""
        self.settings.setValue(key, value)
        
    def restore_defaults(self):
        """Removes all custom style settings, reverting to the defaults on next load."""
        print("Restoring default style settings...")
        for key in DEFAULT_STYLE_SETTINGS.keys():
            self.settings.remove(key)