from PyQt6.QtGui import QColor
from PyQt6.QtCore import QSettings, Qt

# This dictionary defines the application's default appearance. It serves as
# the "single source of truth" for all style settings. If a setting is not
# found in QSettings, the application will fall back to the value defined here.
# Colors are stored as strings to be compatible with QSettings.
DEFAULT_STYLE_SETTINGS = {
    # Candle & Volume Colors
    "colors/up_candle": QColor(0, 204, 0).name(QColor.NameFormat.HexRgb),
    "colors/down_candle": QColor(204, 0, 0).name(QColor.NameFormat.HexRgb),
    "colors/up_wick": QColor(180, 180, 180).name(QColor.NameFormat.HexRgb),
    "colors/down_wick": QColor(180, 180, 180).name(QColor.NameFormat.HexRgb),
    # Volume colors include an alpha component for semi-transparency.
    "colors/up_volume": QColor(0, 204, 0, 180).name(QColor.NameFormat.HexArgb),
    "colors/down_volume": QColor(204, 0, 0, 180).name(QColor.NameFormat.HexArgb),
    
    # Line Colors (Gridlines, Crosshair)
    "lines/crosshair": QColor(220, 220, 220, 150).name(QColor.NameFormat.HexArgb),
    "lines/price_grid": QColor(80, 80, 80).name(QColor.NameFormat.HexRgb),
    "lines/time_grid": QColor(80, 80, 80).name(QColor.NameFormat.HexRgb),
    
    # Line Properties (Width and Style)
    "props/crosshair_width": 1,
    "props/crosshair_style": "DashLine", # Corresponds to a Qt.PenStyle enum name
    "props/price_grid_width": 1,
    "props/price_grid_style": "DotLine",
    "props/time_grid_width": 1,
    "props/time_grid_style": "DashLine",

    # Chart Background
    "background/mode": "Solid", # Can be "Solid" or "Gradient"
    "background/color1": QColor(25, 25, 25).name(QColor.NameFormat.HexRgb),
    "background/color2": QColor(55, 55, 55).name(QColor.NameFormat.HexRgb), # Used for gradient
    "background/gradient_direction": "Vertical", # Can be "Vertical" or "Horizontal"
    
    # Other Layout Properties
    "other/volume_pane_ratio": 0.25, # The height of the volume pane as a ratio of chart area
}

# Maps human-readable style names (used in settings) to their Qt.PenStyle enum values.
PEN_STYLE_MAP = {
    "SolidLine": Qt.PenStyle.SolidLine,
    "DashLine": Qt.PenStyle.DashLine,
    "DotLine": Qt.PenStyle.DotLine,
    "DashDotLine": Qt.PenStyle.DashDotLine,
}
# A reverse map, which is not used in this project but is good practice to have.
REVERSE_PEN_STYLE_MAP = {v: k for k, v in PEN_STYLE_MAP.items()}

class StyleManager:
    """
    Handles loading, saving, and managing all visual style settings.

    This class acts as a centralized interface to QSettings, providing a
    convenient way to get and set style properties while ensuring that
    a default value is always available. This decouples the rest of the
    application from the specifics of settings persistence.
    """
    def __init__(self):
        # QSettings automatically handles storing data in a platform-appropriate
        # location (e.g., Windows Registry, macOS .plist, Linux .ini).
        self.settings = QSettings()

    def get_value(self, key: str, default_value=None):
        """
        Retrieves a value from QSettings.

        If a specific default_value is not provided, it falls back to the
        master default defined in `DEFAULT_STYLE_SETTINGS`.

        Args:
            key: The key for the setting (e.g., "colors/up_candle").
            default_value: An optional override for the default value.

        Returns:
            The stored value for the key, or the default value if not found.
        """
        if default_value is None:
            default_value = DEFAULT_STYLE_SETTINGS.get(key)
        return self.settings.value(key, default_value)

    def set_value(self, key: str, value):
        """
        Saves a value to QSettings.

        Args:
            key: The key for the setting.
            value: The value to be saved.
        """
        self.settings.setValue(key, value)
        
    def restore_defaults(self):
        """
        Removes all custom style settings from QSettings.

        By removing the keys, the application will fall back to using the
        hard-coded `DEFAULT_STYLE_SETTINGS` values the next time it
        requests them.
        """
        print("Restoring default style settings by removing custom values...")
        for key in DEFAULT_STYLE_SETTINGS.keys():
            self.settings.remove(key)