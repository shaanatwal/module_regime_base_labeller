# Save this file as info_widget.py
from PyQt6.QtWidgets import QLabel
from PyQt6.QtCore import Qt
import pandas as pd

class InfoWidget(QLabel):
    """A floating label to display OHLCV data for a hovered candlestick."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("InfoWidget")
        self.setWindowFlags(
            Qt.WindowType.ToolTip | Qt.WindowType.FramelessWindowHint
        )
        self.hide()

    def update_and_show(self, data_row: pd.Series, pos):
        """
        Formats the data and displays the widget at the given position.
        
        Args:
            data_row (pd.Series): The row from the DataFrame for one candle.
            pos (QPoint): The global position to move the widget to.
        """
        if data_row is None:
            self.hide()
            return
            
        # Format the numbers to 2 decimal places, and volume as an integer
        o = f"{data_row['o']:.2f}"
        h = f"{data_row['h']:.2f}"
        l = f"{data_row['l']:.2f}"
        c = f"{data_row['c']:.2f}"
        
        # Format volume nicely
        vol = data_row['v']
        if vol > 1_000_000: v_str = f"{vol/1_000_000:.2f}M"
        elif vol > 1_000: v_str = f"{vol/1_000:.1f}k"
        else: v_str = str(int(vol))

        # Use HTML for rich text formatting
        text = f"""
        <b style='color:#aaa;'>O:</b> <span style='color:white;'>{o}</span><br>
        <b style='color:#aaa;'>H:</b> <span style='color:white;'>{h}</span><br>
        <b style='color:#aaa;'>L:</b> <span style='color:white;'>{l}</span><br>
        <b style='color:#aaa;'>C:</b> <span style='color:white;'>{c}</span><br>
        <b style='color:#aaa;'>V:</b> <span style='color:white;'>{v_str}</span>
        """
        
        self.setText(text)
        self.adjustSize() # Resize to fit content
        self.move(pos)
        self.show()