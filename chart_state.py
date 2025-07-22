# Save this file as chart_state.py
import pandas as pd
from PyQt6.QtGui import QColor
from PyQt6.QtCore import QPoint

from chart_enums import ChartMode

class ChartState:
    """A data class to hold the complete state of the chart view."""
    def __init__(self, dataframe: pd.DataFrame = None):
        # Core Data
        self.df = dataframe if dataframe is not None else pd.DataFrame()

        # Viewport State
        self.start_bar: int = 0
        self.visible_bars: int = 100

        # Interaction State
        self.mode: ChartMode = ChartMode.CURSOR
        self.mouse_pos: QPoint | None = None
        self.last_hovered_index: int = -1
        
        # Dragging State
        self.is_dragging: bool = False
        self.drag_start_pos: QPoint | None = None
        self.drag_end_pos: QPoint | None = None

        # Panning State
        self.is_panning: bool = False
        self.pan_start_pos: QPoint | None = None
        self.pan_start_bar: int = 0
        
        # Display & Theming Properties
        self.symbol_text: str = ""
        self.zoom_factor: float = 1.0
        self.scroll_speed: int = 10
        self.volume_pane_ratio: float = 0.25
        self.price_padding_factor: float = 1.1

        # Colors
        self.bg_color: QColor = QColor(25, 25, 25)
        self.up_color: QColor = QColor(0, 204, 0)
        self.down_color: QColor = QColor(204, 0, 0)
        self.separator_color: QColor = QColor(80, 80, 80)
        self.crosshair_color: QColor = QColor(200, 200, 200, 150)

    def set_data(self, dataframe: pd.DataFrame):
        """Resets the state for a new dataset."""
        self.df = dataframe
        self.start_bar = 0
        self.visible_bars = 100
        self.zoom_factor = 1.0
        
    def get_visible_data(self) -> pd.DataFrame:
        """Returns the slice of the dataframe currently visible."""
        if self.df.empty:
            return pd.DataFrame()
        return self.df.iloc[self.start_bar : self.start_bar + self.visible_bars]
    
    @property
    def max_start_bar(self) -> int:
        """Calculates the maximum possible start_bar index."""
        if self.df.empty:
            return 0
        return max(0, len(self.df) - self.visible_bars)

    def update_start_bar(self, new_start_bar: int):
        """Updates the start bar, ensuring it's within valid bounds."""
        self.start_bar = max(0, min(new_start_bar, self.max_start_bar))

    def get_price_range(self, df_slice: pd.DataFrame) -> tuple[float, float]:
        """Calculates the min price and display range for a given data slice."""
        if df_slice.empty:
            return 0, 1
            
        min_price_actual = df_slice['l'].min()
        max_price_actual = df_slice['h'].max()
        center_price = (min_price_actual + max_price_actual) / 2
        data_range = max_price_actual - min_price_actual
        
        display_range = (data_range * self.zoom_factor * self.price_padding_factor) if data_range > 0 else 1
        
        return center_price - display_range / 2, display_range