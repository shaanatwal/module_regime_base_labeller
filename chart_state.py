import pandas as pd
from PyQt6.QtGui import QColor
from PyQt6.QtCore import QPoint
from chart_enums import ChartMode
from style_manager import StyleManager, PEN_STYLE_MAP

class ChartState:
    """
    A data class representing the complete state of the chart at any given time.

    This class acts as a "single source of truth" that brings together all
    aspects of the chart's configuration and user interaction. It holds the
    core data, the current view parameters (pan/zoom), user input state
    (mouse position, mode), and all style/appearance settings.

    Centralizing the state in this class makes it easier to manage, pass around,
    and persist.
    """
    def __init__(self, dataframe: pd.DataFrame = None):
        # --- Core Data ---
        self.df: pd.DataFrame = dataframe if dataframe is not None else pd.DataFrame()

        # --- Viewport State ---
        # The index of the first bar visible on the left side of the chart.
        self.start_bar: int = 0
        # The total number of bars to display across the chart's width.
        self.visible_bars: int = 100

        # --- Interaction State ---
        self.mode: ChartMode = ChartMode.CURSOR
        self.mouse_pos: QPoint | None = None
        self.last_hovered_index: int = -1
        self.is_dragging: bool = False
        self.drag_start_pos: QPoint | None = None
        self.drag_end_pos: QPoint | None = None
        self.is_panning: bool = False
        self.pan_start_pos: QPoint | None = None
        self.pan_start_bar: int = 0
        
        # --- Display Properties ---
        self.symbol_text: str = ""
        # Vertical zoom level for the price axis.
        self.zoom_factor: float = 1.0
        # Padding added above the highest high and below the lowest low.
        self.price_padding_factor: float = 1.1

        # Load all style settings from the persistent StyleManager.
        self.load_style_settings()

    def load_style_settings(self):
        """
        Loads all appearance-related settings from the StyleManager.
        
        This method is called upon initialization and can be called again
        to hot-reload settings if they are changed in the preferences dialog.
        It populates the state object with ready-to-use QColor and Qt.PenStyle
        objects.
        """
        sm = StyleManager()
        # --- Colors ---
        self.up_color = QColor(sm.get_value("colors/up_candle"))
        # FIX: Corrected the typo from get_v_value to get_value.
        self.down_color = QColor(sm.get_value("colors/down_candle"))
        self.up_wick_color = QColor(sm.get_value("colors/up_wick"))
        self.down_wick_color = QColor(sm.get_value("colors/down_wick"))
        self.up_volume_color = QColor(sm.get_value("colors/up_volume"))
        self.down_volume_color = QColor(sm.get_value("colors/down_volume"))
        self.crosshair_color = QColor(sm.get_value("lines/crosshair"))
        self.price_grid_color = QColor(sm.get_value("lines/price_grid"))
        self.time_grid_color = QColor(sm.get_value("lines/time_grid"))
        
        # --- Line Properties ---
        self.crosshair_width = int(sm.get_value("props/crosshair_width"))
        self.crosshair_style = PEN_STYLE_MAP[sm.get_value("props/crosshair_style")]
        self.price_grid_width = int(sm.get_value("props/price_grid_width"))
        self.price_grid_style = PEN_STYLE_MAP[sm.get_value("props/price_grid_style")]
        self.time_grid_width = int(sm.get_value("props/time_grid_width"))
        self.time_grid_style = PEN_STYLE_MAP[sm.get_value("props/time_grid_style")]
        
        # --- Background ---
        self.bg_mode = sm.get_value("background/mode")
        self.bg_color1 = QColor(sm.get_value("background/color1"))
        self.bg_color2 = QColor(sm.get_value("background/color2"))
        self.bg_gradient_dir = sm.get_value("background/gradient_direction")

        # --- Other ---
        self.volume_pane_ratio = float(sm.get_value("other/volume_pane_ratio"))

    def set_data(self, dataframe: pd.DataFrame):
        """Resets the chart's state with a new DataFrame."""
        self.df = dataframe
        # Reset view to the beginning of the new data.
        self.start_bar = 0
        self.visible_bars = 100
        self.zoom_factor = 1.0
        
    def get_visible_data(self) -> pd.DataFrame:
        """Returns a slice of the DataFrame corresponding to the visible bars."""
        if self.df.empty:
            return pd.DataFrame()
        # Slicing the DataFrame is efficient as it returns a view, not a copy.
        return self.df.iloc[self.start_bar : self.start_bar + self.visible_bars]
    
    @property
    def max_start_bar(self) -> int:
        """Calculates the maximum valid value for start_bar."""
        if self.df.empty:
            return 0
        # This prevents panning too far to the right, leaving empty space.
        return max(0, len(self.df) - self.visible_bars)

    def update_start_bar(self, new_start_bar: int):
        """
        Updates the start_bar, ensuring it stays within valid bounds.
        
        Args:
            new_start_bar: The desired new starting bar index.
        """
        # Clamp the value between 0 and the maximum allowed start bar.
        self.start_bar = max(0, min(new_start_bar, self.max_start_bar))

    def get_price_range(self, df_slice: pd.DataFrame) -> tuple[float, float]:
        """
        Calculates the minimum price and price range for the Y-axis of the price pane.
        
        Args:
            df_slice: The DataFrame containing only the visible data.

        Returns:
            A tuple containing (minimum_display_price, total_display_range).
        """
        if df_slice.empty:
            return 0, 1 # Default range if no data
            
        min_p = df_slice['l'].min()
        max_p = df_slice['h'].max()
        
        # Calculate the actual range of data and add padding.
        center = (min_p + max_p) / 2
        data_range = max_p - min_p
        # Ensure range is not zero to avoid division-by-zero errors.
        display_range = (data_range * self.zoom_factor * self.price_padding_factor) if data_range > 0 else 1
        
        # Return the bottom of the display range and the total height of the range.
        return center - display_range / 2, display_range