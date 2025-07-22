# Save this file as chart_state.py
import pandas as pd
from PyQt6.QtGui import QColor
from PyQt6.QtCore import QPoint
from chart_enums import ChartMode
from style_manager import StyleManager, PEN_STYLE_MAP

class ChartState:
    """A data class to hold the complete state of the chart and its style."""
    def __init__(self, dataframe: pd.DataFrame = None):
        # Core Data
        self.df = dataframe if dataframe is not None else pd.DataFrame()

        # Viewport State
        self.start_bar: int = 0; self.visible_bars: int = 100

        # Interaction State
        self.mode: ChartMode = ChartMode.CURSOR; self.mouse_pos: QPoint | None = None
        self.last_hovered_index: int = -1
        self.is_dragging: bool = False; self.drag_start_pos: QPoint | None = None; self.drag_end_pos: QPoint | None = None
        self.is_panning: bool = False; self.pan_start_pos: QPoint | None = None; self.pan_start_bar: int = 0
        
        # Display Properties
        self.symbol_text: str = ""; self.zoom_factor: float = 1.0
        self.scroll_speed: int = 10; self.price_padding_factor: float = 1.1

        # Load all style settings from the manager
        self.load_style_settings()

    def load_style_settings(self):
        """Loads all style-related settings using the StyleManager."""
        sm = StyleManager()
        # Colors
        self.up_color = QColor(sm.get_value("colors/up_candle"))
        self.down_color = QColor(sm.get_value("colors/down_candle"))
        self.up_wick_color = QColor(sm.get_value("colors/up_wick"))
        self.down_wick_color = QColor(sm.get_value("colors/down_wick"))
        self.up_volume_color = QColor(sm.get_value("colors/up_volume"))
        self.down_volume_color = QColor(sm.get_value("colors/down_volume"))
        
        self.crosshair_color = QColor(sm.get_value("lines/crosshair"))
        self.price_grid_color = QColor(sm.get_value("lines/price_grid"))
        self.time_grid_color = QColor(sm.get_value("lines/time_grid"))
        
        # Line Properties
        self.crosshair_width = int(sm.get_value("props/crosshair_width"))
        self.crosshair_style = PEN_STYLE_MAP[sm.get_value("props/crosshair_style")]
        self.price_grid_width = int(sm.get_value("props/price_grid_width"))
        self.price_grid_style = PEN_STYLE_MAP[sm.get_value("props/price_grid_style")]
        self.time_grid_width = int(sm.get_value("props/time_grid_width"))
        self.time_grid_style = PEN_STYLE_MAP[sm.get_value("props/time_grid_style")]
        
        # Background
        self.bg_mode = sm.get_value("background/mode")
        self.bg_color1 = QColor(sm.get_value("background/color1"))
        self.bg_color2 = QColor(sm.get_value("background/color2"))
        self.bg_gradient_dir = sm.get_value("background/gradient_direction")

        # Other
        self.volume_pane_ratio = float(sm.get_value("other/volume_pane_ratio"))

    def set_data(self, dataframe: pd.DataFrame):
        self.df = dataframe; self.start_bar = 0
        self.visible_bars = 100; self.zoom_factor = 1.0
        
    def get_visible_data(self) -> pd.DataFrame:
        if self.df.empty: return pd.DataFrame()
        return self.df.iloc[self.start_bar : self.start_bar + self.visible_bars]
    
    @property
    def max_start_bar(self) -> int:
        if self.df.empty: return 0
        return max(0, len(self.df) - self.visible_bars)

    def update_start_bar(self, new_start_bar: int):
        self.start_bar = max(0, min(new_start_bar, self.max_start_bar))

    def get_price_range(self, df_slice: pd.DataFrame) -> tuple[float, float]:
        if df_slice.empty: return 0, 1
        min_p = df_slice['l'].min(); max_p = df_slice['h'].max()
        center = (min_p + max_p) / 2
        data_range = max_p - min_p
        display_range = (data_range * self.zoom_factor * self.price_padding_factor) if data_range > 0 else 1
        return center - display_range / 2, display_range