# Save this file as candle_widget.py
import pandas as pd
from PyQt6.QtOpenGLWidgets import QOpenGLWidget
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QColor, QPainter, QPen, QFont, QBrush
from PyQt6.QtCore import Qt, QPoint, pyqtSignal, QRectF
from OpenGL.GL import *
import numpy as np

class CandleWidget(QOpenGLWidget):
    # NEW: Define signals to communicate hover events
    barHovered = pyqtSignal(object, QPoint) # object will be the data row, QPoint is mouse pos
    mouseLeftChart = pyqtSignal()

    def __init__(self, dataframe: pd.DataFrame = None, parent=None):
        super().__init__(parent)
        self.df = dataframe if dataframe is not None else pd.DataFrame()
        
        self.visible_bars = 100; self.start_bar = 0
        self.zoom_factor = 1.0; self.scroll_speed = 10
        
        self.volume_pane_ratio = 0.25; self.pane_separator_height = 5
        
        self.bg_color = QColor(25, 25, 25); self.up_color = QColor(0, 204, 0)
        self.down_color = QColor(204, 0, 0); self.separator_color = QColor(80, 80, 80)
        
        # NEW: Enable mouse tracking to get hover events
        self.setMouseTracking(True)
        self.last_hovered_index = -1

        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        
    def set_background_color(self, color: QColor): self.bg_color = color; self.update()
    def get_background_color(self) -> QColor: return self.bg_color
    def set_up_color(self, color: QColor): self.up_color = color; self.update()
    def get_up_color(self) -> QColor: return self.up_color
    def set_down_color(self, color: QColor): self.down_color = color; self.update()
    def get_down_color(self) -> QColor: return self.down_color

    def set_data(self, dataframe: pd.DataFrame):
        self.df = dataframe; self.start_bar = 0; self.zoom_factor = 1.0;
        self.visible_bars = 100; self.update()

    def keyPressEvent(self, event):
        # (Key press logic remains unchanged)
        if self.df.empty: super().keyPressEvent(event); return
        max_start_bar = max(0, len(self.df) - self.visible_bars)
        if event.key() == Qt.Key.Key_Right: self.start_bar = min(self.start_bar + self.scroll_speed, max_start_bar)
        elif event.key() == Qt.Key.Key_Left: self.start_bar = max(0, self.start_bar - self.scroll_speed)
        elif event.key() == Qt.Key.Key_Plus or event.key() == Qt.Key.Key_Equal: self.zoom_factor *= 0.9
        elif event.key() == Qt.Key.Key_Minus: self.zoom_factor *= 1.1
        elif event.key() == Qt.Key.Key_Up or event.key() == Qt.Key.Key_Down:
            center_bar_index = self.start_bar + self.visible_bars // 2
            if event.key() == Qt.Key.Key_Up: new_visible_bars = max(10, int(self.visible_bars * 0.8))
            else: new_visible_bars = min(len(self.df), int(self.visible_bars * 1.2))
            self.visible_bars = new_visible_bars; new_start_bar = max(0, center_bar_index - self.visible_bars // 2)
            new_max_start_bar = max(0, len(self.df) - self.visible_bars); self.start_bar = min(new_start_bar, new_max_start_bar)
        else: super().keyPressEvent(event); return
        self.update()

    # --- NEW: Mouse Event Handlers ---
    def mouseMoveEvent(self, event):
        if self.df.empty: return

        bar_width = self.width() / self.visible_bars
        # Calculate which bar index is under the cursor
        hover_index_in_view = int(event.position().x() / bar_width)
        
        # Avoid out-of-bounds errors
        if hover_index_in_view < 0 or hover_index_in_view >= len(self.df):
            self.mouseLeftChart.emit(); return

        # Translate to the index in the full dataframe
        actual_index = self.start_bar + hover_index_in_view

        if actual_index >= len(self.df):
            if self.last_hovered_index != -1: self.mouseLeftChart.emit(); self.last_hovered_index = -1
            return
            
        # Only emit a signal if the hovered bar has changed
        if actual_index != self.last_hovered_index:
            self.last_hovered_index = actual_index
            data_row = self.df.iloc[actual_index]
            self.barHovered.emit(data_row, event.globalPosition().toPoint())
            
        super().mouseMoveEvent(event)

    def leaveEvent(self, event):
        # When mouse leaves the widget, hide the info box
        self.last_hovered_index = -1
        self.mouseLeftChart.emit()
        super().leaveEvent(event)
    
    # (The rest of the file is mostly drawing logic)
    def initializeGL(self): pass
    def resizeGL(self, w: int, h: int): pass
    def paintGL(self):
        glClearColor(self.bg_color.redF(), self.bg_color.greenF(), self.bg_color.blueF(), 1.0)
        glClear(GL_COLOR_BUFFER_BIT)
        if self.df.empty: return
        visible_df = self.df.iloc[self.start_bar : self.start_bar + self.visible_bars]
        if visible_df.empty: return
        w = self.width(); h = self.height()
        volume_pane_height = int(h * self.volume_pane_ratio)
        price_pane_height = h - volume_pane_height - self.pane_separator_height
        price_pane_y_offset = volume_pane_height + self.pane_separator_height
        self.draw_price_pane(w, price_pane_height, price_pane_y_offset, visible_df)
        self.draw_volume_pane(w, volume_pane_height, visible_df)
        painter = QPainter(self)
        self.draw_overlays(painter, w, h, price_pane_height, volume_pane_height, visible_df)
        painter.end()
        
    def draw_price_pane(self, w, pane_h, pane_y, df):
        glEnable(GL_SCISSOR_TEST); glScissor(0, pane_y, w, pane_h); glViewport(0, pane_y, w, pane_h)
        min_price_actual = df['l'].min(); max_price_actual = df['h'].max()
        center_price = (min_price_actual + max_price_actual) / 2
        display_range = (max_price_actual - min_price_actual) * self.zoom_factor if (max_price_actual - min_price_actual) > 0 else 1
        min_price = center_price - display_range / 2; max_price = center_price + display_range / 2
        glMatrixMode(GL_PROJECTION); glLoadIdentity(); glOrtho(0, self.visible_bars, min_price, max_price, -1, 1)
        glMatrixMode(GL_MODELVIEW); glLoadIdentity(); self.draw_candles_gl(df); glDisable(GL_SCISSOR_TEST)
        
    def draw_volume_pane(self, w, pane_h, df):
        glEnable(GL_SCISSOR_TEST); glScissor(0, 0, w, pane_h); glViewport(0, 0, w, pane_h)
        max_volume = df['v'].max() if not df['v'].empty else 1
        glMatrixMode(GL_PROJECTION); glLoadIdentity(); glOrtho(0, self.visible_bars, 0, max_volume * 1.05, -1, 1)
        glMatrixMode(GL_MODELVIEW); glLoadIdentity(); self.draw_volume_gl(df); glDisable(GL_SCISSOR_TEST)
        
    def draw_candles_gl(self, visible_df):
        glBegin(GL_LINES)
        for i, (index, row) in enumerate(visible_df.iterrows()): glColor3f(0.5, 0.5, 0.5); glVertex2f(i + 0.5, row['l']); glVertex2f(i + 0.5, row['h'])
        glEnd()
        glBegin(GL_QUADS)
        for i, (index, row) in enumerate(visible_df.iterrows()):
            color = self.up_color if row['c'] >= row['o'] else self.down_color
            glColor3f(color.redF(), color.greenF(), color.blueF())
            glVertex2f(i + 0.1, row['o']); glVertex2f(i + 0.9, row['o']); glVertex2f(i + 0.9, row['c']); glVertex2f(i + 0.1, row['c'])
        glEnd()
        
    def draw_volume_gl(self, visible_df):
        glEnable(GL_BLEND); glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA); glBegin(GL_QUADS)
        for i, (index, row) in enumerate(visible_df.iterrows()):
            color = self.up_color if row['c'] >= row['o'] else self.down_color
            glColor4f(color.redF(), color.greenF(), color.blueF(), 0.7)
            glVertex2f(i + 0.1, 0); glVertex2f(i + 0.9, 0); glVertex2f(i + 0.9, row['v']); glVertex2f(i + 0.1, row['v'])
        glEnd(); glDisable(GL_BLEND)

    def draw_overlays(self, painter, w, h, price_pane_h, vol_pane_h, df):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        min_price_actual=df['l'].min(); max_price_actual=df['h'].max(); center_price=(min_price_actual+max_price_actual)/2
        display_range=(max_price_actual-min_price_actual)*self.zoom_factor if (max_price_actual-min_price_actual)>0 else 1
        view_min_price=center_price-display_range/2; view_price_range=display_range
        max_volume=df['v'].max() if not df['v'].empty else 1
        separator_y=price_pane_h+self.pane_separator_height//2
        painter.setPen(QPen(self.separator_color,1)); painter.drawLine(0,separator_y,w,separator_y)
        num_price_lines=8
        for i in range(num_price_lines+1):
            price=view_min_price+(i/num_price_lines)*view_price_range
            y=price_pane_h-int(((price-view_min_price)/view_price_range)*price_pane_h)
            painter.setPen(QPen(self.separator_color,1,Qt.PenStyle.DotLine)); painter.drawLine(0,y,w,y)
            # FIX: Draw highlight behind price text
            label_rect = QRectF(w - 75, y - 9, 70, 18)
            painter.setBrush(QBrush(QColor(40, 40, 40, 180))) # Semi-transparent background
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRect(label_rect)
            painter.setPen(QPen(QColor(220,220,220))); painter.setFont(QFont('monospace',9))
            painter.drawText(label_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight, f"{price:.2f}")
        num_vol_lines=2
        for i in range(num_vol_lines+1):
            vol=(i/num_vol_lines)*max_volume; y=h-int((vol/(max_volume*1.05))*vol_pane_h)
            painter.setPen(QPen(self.separator_color,1,Qt.PenStyle.DotLine)); painter.drawLine(0,y,w,y)
            if vol>1_000_000: vol_str=f"{vol/1_000_000:.2f}M"
            elif vol>1_000: vol_str=f"{vol/1_000:.1f}k"
            else: vol_str=str(int(vol))
            label_rect = QRectF(w-75, y-18, 70, 18)
            painter.setBrush(QBrush(QColor(40,40,40,180))); painter.setPen(Qt.PenStyle.NoPen); painter.drawRect(label_rect)
            painter.setPen(QPen(QColor(220,220,220))); painter.setFont(QFont('monospace',9))
            painter.drawText(label_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight, vol_str)
        first_timestamp_local=df['t'].iloc[0].tz_convert('America/New_York'); date_str=first_timestamp_local.strftime('%Y-%m-%d')
        painter.setFont(QFont('monospace',10)); painter.setPen(QPen(QColor(200,200,200))); painter.drawText(10,15,date_str)
        num_time_labels=10; bar_step=max(1,self.visible_bars//num_time_labels); last_date=None
        for i in range(0, len(df), bar_step):
            local_timestamp=df['t'].iloc[i].tz_convert('America/New_York')
            # FIX: Center time text under the bar group
            bar_width = w / self.visible_bars
            x_pos = int((i + bar_step / 2) * bar_width)
            time_str=local_timestamp.strftime('%H:%M'); time_font=QFont('monospace',9)
            time_font.setBold(True); painter.setFont(time_font) # FIX: Make font bold
            painter.setPen(QPen(QColor(220,220,220)))
            painter.drawText(x_pos-50,h-25,100,20,Qt.AlignmentFlag.AlignCenter,time_str)