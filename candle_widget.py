# Save this as candle_widget.py
import pandas as pd
from PyQt6.QtOpenGLWidgets import QOpenGLWidget
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QColor, QPainter, QPen
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

        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def set_data(self, dataframe: pd.DataFrame):
        self.df = dataframe
        self.start_bar = 0
        self.zoom_factor = 1.0
        self.visible_bars = 100 # Reset horizontal zoom on new data
        self.update()

    def keyPressEvent(self, event):
        """Handle keyboard input for navigation."""
        
        # --- Horizontal Panning ---
        if event.key() == Qt.Key.Key_Right:
            new_start = self.start_bar + self.scroll_speed
            if len(self.df) > self.visible_bars:
                self.start_bar = min(new_start, len(self.df) - self.visible_bars)
            self.update()
        elif event.key() == Qt.Key.Key_Left:
            new_start = self.start_bar - self.scroll_speed
            self.start_bar = max(0, new_start)
            self.update()
            
        # --- Vertical (Price) Zooming ---
        elif event.key() == Qt.Key.Key_Plus or event.key() == Qt.Key.Key_Equal:
            self.zoom_factor *= 0.9
            self.update()
        elif event.key() == Qt.Key.Key_Minus:
            self.zoom_factor *= 1.1
            self.update()

        # --- Horizontal (Time) Zooming ---
        elif event.key() == Qt.Key.Key_Up: # Zoom In
            center_bar_index = self.start_bar + self.visible_bars // 2
            new_visible_bars = max(10, int(self.visible_bars * 0.8)) # Min 10 bars
            self.visible_bars = new_visible_bars
            # Recalculate start_bar to keep center locked
            self.start_bar = max(0, center_bar_index - self.visible_bars // 2)
            self.update()
        elif event.key() == Qt.Key.Key_Down: # Zoom Out
            center_bar_index = self.start_bar + self.visible_bars // 2
            new_visible_bars = min(len(self.df), int(self.visible_bars * 1.2)) # Max all bars
            self.visible_bars = new_visible_bars
            self.start_bar = max(0, center_bar_index - self.visible_bars // 2)
            self.update()

        else:
            super().keyPressEvent(event)

    def initializeGL(self):
        glClearColor(0.1, 0.1, 0.1, 1.0)

    def resizeGL(self, w: int, h: int):
        glViewport(0, 0, w, h)

    def paintGL(self):
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
        
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        glOrtho(0, self.visible_bars, min_price, max_price, -1, 1)
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()

        self.draw_candles_gl(visible_df)

        painter = QPainter(self)
        self.draw_axes(painter, min_price, max_price)
        painter.end()


    def draw_candles_gl(self, visible_df):
        glBegin(GL_LINES)
        for i, (index, row) in enumerate(visible_df.iterrows()):
            glColor3f(0.5, 0.5, 0.5)
            glVertex2f(i + 0.5, row['l'])
            glVertex2f(i + 0.5, row['h'])
        glEnd()
        
        glBegin(GL_QUADS)
        for i, (index, row) in enumerate(visible_df.iterrows()):
            if row['c'] >= row['o']:
                glColor3f(0.0, 0.8, 0.0)
            else:
                glColor3f(0.8, 0.0, 0.0)
            
            glVertex2f(i + 0.1, row['o'])
            glVertex2f(i + 0.9, row['o'])
            glVertex2f(i + 0.9, row['c'])
            glVertex2f(i + 0.1, row['c'])
        glEnd()

    def draw_axes(self, painter, min_price, max_price):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor(200, 200, 200), 1))
        
        width = self.width()
        height = self.height()
        price_range = max_price - min_price if max_price > min_price else 1
        
        num_price_lines = 10
        price_step = price_range / num_price_lines
        for i in range(num_price_lines + 1):
            price = min_price + i * price_step
            y = height - int((price - min_price) / price_range * height)
            painter.setPen(QPen(QColor(60, 60, 60), 1))
            painter.drawLine(0, y, width, y)
            painter.setPen(QPen(QColor(200, 200, 200), 1))
            painter.drawText(width - 75, y + 5, 70, 20, Qt.AlignmentFlag.AlignRight, f"{price:.2f}")

        visible_df = self.df.iloc[self.start_bar : self.start_bar + self.visible_bars]
        if visible_df.empty: return
        
        num_time_labels = 10
        bar_step = self.visible_bars // num_time_labels
        
        time_format = '%H:%M'
        if len(visible_df.index) > 1:
            time_delta = visible_df.index[1] - visible_df.index[0]
            if time_delta >= pd.Timedelta(days=1):
                time_format = '%Y-%m-%d'
        
        for i in range(num_time_labels):
            bar_index = i * bar_step
            if bar_index < len(visible_df):
                timestamp = visible_df.index[bar_index]
                x = int((bar_index / self.visible_bars) * width)
                
                time_str = timestamp.strftime(time_format)
                painter.drawText(x - 50, height - 25, 100, 20, Qt.AlignmentFlag.AlignCenter, time_str)