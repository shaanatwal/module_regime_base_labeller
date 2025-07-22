from PyQt6.QtWidgets import QLabel
from PyQt6.QtCore import Qt, QPoint
import pandas as pd

class InfoWidget(QLabel):
    """
    A floating, frameless label used to display OHLCV data for a hovered candle.

    This widget is styled via a stylesheet (`#InfoWidget`) and behaves like a
    tooltip, appearing near the mouse cursor to provide contextual information
    without obstructing the view.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("InfoWidget")
        self.setWindowFlags(
            Qt.WindowType.ToolTip | Qt.WindowType.FramelessWindowHint
        )
        self.hide()

    def update_and_show(self, data_row: pd.Series, pos: QPoint):
        """
        Formats the provided data row and displays the widget at the given position.

        Args:
            data_row: The pandas Series from the DataFrame for one candle.
            pos: The global screen position at which to show the widget.
        """
        if data_row is None:
            self.hide()
            return
            
        # Format numbers for consistent display.
        o = f"{data_row['o']:.2f}"
        h = f"{data_row['h']:.2f}"
        l = f"{data_row['l']:.2f}"
        c = f"{data_row['c']:.2f}"
        
        # Format volume into a human-readable string (e.g., 1.23M, 45.1k).
        vol = data_row['v']
        if vol >= 1_000_000:
            v_str = f"{vol / 1_000_000:.2f}M"
        elif vol >= 1_000:
            v_str = f"{vol / 1_000:.1f}k"
        else:
            v_str = str(int(vol))

        # Use rich text (HTML) for colored and structured formatting.
        text = f"""
        <b style='color:#aaa;'>O:</b> <span style='color:white;'>{o}</span><br>
        <b style='color:#aaa;'>H:</b> <span style='color:white;'>{h}</span><br>
        <b style='color:#aaa;'>L:</b> <span style='color:white;'>{l}</span><br>
        <b style='color:#aaa;'>C:</b> <span style='color:white;'>{c}</span><br>
        <b style='color:#aaa;'>V:</b> <span style='color:white;'>{v_str}</span>
        """
        
        self.setText(text)
        self.adjustSize() # Automatically resize the label to fit its new content.
        self.move(pos)
        self.show()