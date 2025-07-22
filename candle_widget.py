# Save this file as candle_widget.py
import pandas as pd
from PyQt6.QtOpenGLWidgets import QOpenGLWidget
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QColor, QPainter, QPen, QFont
from PyQt6.QtCore import Qt, QPoint
from OpenGL.GL import *

class CandleWidget(QOpenGLWidget):
    def __init__(self, dataframe: pd.DataFrame = None, parent=None):
        super().__init__(parent)
        self.df = dataframe if dataframe is not None else pd.DataFrame()
        
        self.visible_bars = 100
        self.start_bar = 0
        self.zoom_factor = 1.0
        self.scroll_speed = 10
        
        # --- Default Colors ---
        self.bg_color = QColor(25, 25, 25)
        self.up_color = QColor(0, 204, 0)
        self.down_color = QColor(204, 0, 0)
        self.separator_color = QColor(80, 80, 80)

        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        
    # --- Color Getters/Setters ---
    def set_background_color(self, color: QColor):
        self.bg_color = color
        self.update()

    def get_background_color(self) -> QColor:
        return self.bg_color
        
    def set_up_color(self, color: QColor):
        self.up_color = color
        self.update()

    def get_up_color(self) -> QColor:
        return self.up_color
        
    def set_down_color(self, color: QColor):
        self.down_color = color
        self.update()

    def get_down_color(self) -> QColor:
        return self.down_color

    def set_data(self, dataframe: pd.DataFrame):
        self.df = dataframe
        self.start_bar = 0
        self.zoom_factor = 1.0
        self.visible_bars = 100
        self.update()

    def keyPressEvent(self, event):
        if self.df.empty:
            super().keyPressEvent(event)
            return

        max_start_bar = max(0, len(self.df) - self.visible_bars)
        
        if event.key() == Qt.Key.Key_Right:
            self.start_bar = min(self.start_bar + self.scroll_speed, max_start_bar)
            self.update()
        elif event.key() == Qt.Key.Key_Left:
            self.start_bar = max(0, self.start_bar - self.scroll_speed)
            self.update()
            
        elif event.key() == Qt.Key.Key_Plus or event.key() == Qt.Key.Key_Equal:
            self.zoom_factor *= 0.9
            self.update()
        elif event.key() == Qt.Key.Key_Minus:
            self.zoom_factor *= 1.1
            self.update()

        elif event.key() == Qt.Key.Key_Up or event.key() == Qt.Key.Key_Down:
            center_bar_index = self.start_bar + self.visible_bars // 2
            
            if event.key() == Qt.Key.Key_Up:
                new_visible_bars = max(10, int(self.visible_bars * 0.8))
            else:
                new_visible_bars = min(len(self.df), int(self.visible_bars * 1.2))

            self.visible_bars = new_visible_bars
            
            new_start_bar = max(0, center_bar_index - self.visible_bars // 2)
            
            new_max_start_bar = max(0, len(self.df) - self.visible_bars)
            self.start_bar = min(new_start_bar, new_max_start_bar)
            
            self.update()

        else:
            super().keyPressEvent(event)

    def initializeGL(self):
        # This is called only once. The background color clear
        # needs to happen in paintGL to allow for dynamic changes.
        pass

    def resizeGL(self, w: int, h: int):
        glViewport(0, 0, w, h)

    def paintGL(self):
        # FIX: Set the clear color here, every time we paint.
        glClearColor(self.bg_color.redF(), self.bg_color.greenF(), self.bg_color.blueF(), 1.0)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        
        if self.df.empty:
            return

        visible_df = self.df.iloc[self.start_bar : self.start_bar + self.visible_bars]
        if visible_df.empty:
            return

        min_price_actual = visible_df['l'].min()
        max_price_actual = visible_df['h'].max()
        
        center_price = (min_price_actual + max_price_actual) / 2
        display_range = (max_price_actual - min_price_actual) * self.zoom_factor if (max_price_actual - min_price_actual) > 0 else 1
        
        min_price = center_price - display_range / 2
        max_price = center_price + display_range / 2
        
        price_range = max_price - min_price
        if price_range <= 1e-9:
            price_range = 1
        
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        glOrtho(0, self.visible_bars, min_price, max_price, -1, 1)
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()

        self.draw_candles_gl(visible_df)

        painter = QPainter(self)
        self.draw_axes_and_separators(painter, min_price, max_price, price_range, visible_df)
        painter.end()


    def draw_candles_gl(self, visible_df):
        glBegin(GL_LINES)
        for i, (index, row) in enumerate(visible_df.iterrows()):
            glColor3f(0.5, 0.5, 0.5) # Wick color
            glVertex2f(i + 0.5, row['l'])
            glVertex2f(i + 0.5, row['h'])
        glEnd()
        
        glBegin(GL_QUADS)
        for i, (index, row) in enumerate(visible_df.iterrows()):
            # Use customizable colors
            if row['c'] >= row['o']:
                up = self.up_color
                glColor3f(up.redF(), up.greenF(), up.blueF())
            else:
                down = self.down_color
                glColor3f(down.redF(), down.greenF(), down.blueF())
            
            glVertex2f(i + 0.1, row['o'])
            glVertex2f(i + 0.9, row['o'])
            glVertex2f(i + 0.9, row['c'])
            glVertex2f(i + 0.1, row['c'])
        glEnd()

    def draw_axes_and_separators(self, painter, min_price, max_price, price_range, visible_df):
        """Draws axes, date display, and day separator lines."""
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        width = self.width()
        height = self.height()
        
        # --- Draw Date Display ---
        if not visible_df.empty:
            local_timestamp = visible_df['t'].iloc[0].tz_convert('America/New_York')
            date_str = local_timestamp.strftime('%Y-%m-%d')
            painter.setFont(QFont('monospace', 10))
            painter.setPen(QPen(QColor(150, 150, 150)))
            painter.drawText(10, 20, date_str)

        # --- Draw Price Axis ---
        num_price_lines = 10
        price_step = price_range / num_price_lines
        for i in range(num_price_lines + 1):
            price = min_price + i * price_step
            y = height - int((price - min_price) / price_range * height)
            
            painter.setPen(QPen(QColor(60, 60, 60), 1))
            painter.drawLine(0, y, width, y)
            
            painter.setFont(QFont('monospace', 9))
            painter.setPen(QPen(QColor(200, 200, 200), 1))
            painter.drawText(width - 75, y + 4, 70, 20, Qt.AlignmentFlag.AlignRight, f"{price:.2f}")
            
        # --- Draw Time Axis and Day Separators ---
        if visible_df.empty: return
        
        num_time_labels = 10
        bar_step = max(1, self.visible_bars // num_time_labels)
        last_date = None
        
        for i, (index, row) in enumerate(visible_df.iterrows()):
            local_timestamp = row['t'].tz_convert('America/New_York')
            current_date = local_timestamp.date()

            # NEW: Draw day separator line
            if last_date is not None and current_date != last_date:
                x = int((i / self.visible_bars) * width)
                pen = QPen(self.separator_color, 1, Qt.PenStyle.DashLine)
                painter.setPen(pen)
                painter.drawLine(x, 0, x, height - 30) # Leave space for time labels
            
            last_date = current_date
            
            # Draw time labels at intervals
            if i % bar_step == 0:
                x = int((i / self.visible_bars) * width)
                time_str = local_timestamp.strftime('%H:%M')
                painter.setPen(QPen(QColor(200, 200, 200)))
                painter.drawText(x - 50, height - 25, 100, 20, Qt.AlignmentFlag.AlignCenter, time_str)