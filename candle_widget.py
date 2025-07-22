# Save this file as candle_widget.py
import pandas as pd
from datetime import timedelta
from PyQt6.QtOpenGLWidgets import QOpenGLWidget
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QColor, QPainter, QPen, QFont, QBrush, QTextDocument # <-- Import QTextDocument
from PyQt6.QtCore import Qt, QPoint, pyqtSignal, QRectF, QRect
from OpenGL.GL import *

from chart_enums import ChartMode

class CandleWidget(QOpenGLWidget):
    barHovered = pyqtSignal(object, QPoint) 
    mouseLeftChart = pyqtSignal()

    def __init__(self, dataframe: pd.DataFrame = None, parent=None):
        super().__init__(parent)
        self.df = dataframe if dataframe is not None else pd.DataFrame()
        
        self.visible_bars = 100; self.start_bar = 0
        self.zoom_factor = 1.0; self.scroll_speed = 10
        self.volume_pane_ratio = 0.25; self.pane_separator_height = 5
        
        self.bg_color = QColor(25, 25, 25); self.up_color = QColor(0, 204, 0)
        self.down_color = QColor(204, 0, 0); self.separator_color = QColor(80, 80, 80)
        self.crosshair_color = QColor(200, 200, 200, 150)
        
        self.setMouseTracking(True)
        self.mouse_pos = None; self.last_hovered_index = -1
        
        self.mode = ChartMode.CURSOR; self.is_dragging = False
        self.drag_start_pos = None; self.drag_end_pos = None

        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        
    def set_data(self, dataframe: pd.DataFrame):
        self.df = dataframe; self.start_bar = 0; self.zoom_factor = 1.0
        self.visible_bars = 100; self.update()
        
    def set_mode(self, mode: ChartMode):
        self.mode = mode; self.is_dragging = False; self.update()

    def mousePressEvent(self, event):
        if self.mode == ChartMode.CURSOR and event.button() == Qt.MouseButton.LeftButton:
            # FIX 1: Hide the hover info widget when a drag starts
            self.mouseLeftChart.emit()
            
            self.is_dragging = True; self.drag_start_pos = event.position().toPoint()
            self.drag_end_pos = event.position().toPoint(); self.update()
        else: super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if self.mode == ChartMode.CURSOR and event.button() == Qt.MouseButton.LeftButton:
            self.is_dragging = False; self.drag_start_pos = None
            self.drag_end_pos = None; self.update()
        else: super().mouseReleaseEvent(event)

    def mouseMoveEvent(self, event):
        self.mouse_pos = event.position().toPoint()
        if self.is_dragging:
            self.drag_end_pos = self.mouse_pos; self.update(); return
        if self.df.empty: return
        bar_width = self.width() / self.visible_bars
        hover_index_in_view = int(event.position().x() / bar_width)
        actual_index = self.start_bar + hover_index_in_view
        if actual_index >= len(self.df): actual_index = -1
        if actual_index != self.last_hovered_index:
            self.last_hovered_index = actual_index
            if actual_index != -1: self.barHovered.emit(self.df.iloc[actual_index], event.globalPosition().toPoint())
            else: self.mouseLeftChart.emit()
        self.update()

    # (Other core methods remain unchanged)
    def keyPressEvent(self, event):
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
    def leaveEvent(self, event):
        self.last_hovered_index = -1; self.mouse_pos = None; self.mouseLeftChart.emit(); self.update(); super().leaveEvent(event)
    def initializeGL(self): pass
    def resizeGL(self, w: int, h: int): pass
    def paintGL(self):
        glClearColor(self.bg_color.redF(), self.bg_color.greenF(), self.bg_color.blueF(), 1.0); glClear(GL_COLOR_BUFFER_BIT)
        if self.df.empty: return
        visible_df = self.df.iloc[self.start_bar : self.start_bar + self.visible_bars]
        if visible_df.empty: return
        w = self.width(); h = self.height()
        volume_pane_height = int(h * self.volume_pane_ratio); price_pane_height = h - volume_pane_height - self.pane_separator_height
        price_pane_y_offset = volume_pane_height + self.pane_separator_height
        self.draw_price_pane(w, price_pane_height, price_pane_y_offset, visible_df); self.draw_volume_pane(w, volume_pane_height, visible_df)
        painter = QPainter(self); self.draw_overlays(painter, w, h, price_pane_height, volume_pane_height, visible_df); painter.end()
    def draw_price_pane(self, w, pane_h, pane_y, df):
        glEnable(GL_SCISSOR_TEST); glScissor(0, pane_y, w, pane_h); glViewport(0, pane_y, w, pane_h)
        min_price_actual=df['l'].min(); max_price_actual=df['h'].max(); center_price=(min_price_actual+max_price_actual)/2
        display_range=(max_price_actual-min_price_actual)*self.zoom_factor if (max_price_actual-min_price_actual)>0 else 1
        min_price=center_price-display_range/2; max_price=center_price+display_range/2
        glMatrixMode(GL_PROJECTION); glLoadIdentity(); glOrtho(0, self.visible_bars, min_price, max_price, -1, 1)
        glMatrixMode(GL_MODELVIEW); glLoadIdentity(); self.draw_candles_gl(df); glDisable(GL_SCISSOR_TEST)
    def draw_volume_pane(self, w, pane_h, df):
        glEnable(GL_SCISSOR_TEST); glScissor(0, 0, w, pane_h); glViewport(0, 0, w, pane_h)
        max_volume=df['v'].max() if not df['v'].empty else 1
        glMatrixMode(GL_PROJECTION); glLoadIdentity(); glOrtho(0, self.visible_bars, 0, max_volume * 1.05, -1, 1)
        glMatrixMode(GL_MODELVIEW); glLoadIdentity(); self.draw_volume_gl(df); glDisable(GL_SCISSOR_TEST)
    def draw_candles_gl(self, visible_df):
        glBegin(GL_LINES)
        for i, (idx, row) in enumerate(visible_df.iterrows()): glColor3f(0.5, 0.5, 0.5); glVertex2f(i + 0.5, row['l']); glVertex2f(i + 0.5, row['h'])
        glEnd()
        glBegin(GL_QUADS)
        for i, (idx, row) in enumerate(visible_df.iterrows()):
            color = self.up_color if row['c'] >= row['o'] else self.down_color; glColor3f(color.redF(), color.greenF(), color.blueF())
            glVertex2f(i + 0.1, row['o']); glVertex2f(i + 0.9, row['o']); glVertex2f(i + 0.9, row['c']); glVertex2f(i + 0.1, row['c'])
        glEnd()
    def draw_volume_gl(self, visible__df):
        glEnable(GL_BLEND); glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA); glBegin(GL_QUADS)
        for i, (idx, row) in enumerate(visible__df.iterrows()):
            color = self.up_color if row['c'] >= row['o'] else self.down_color; glColor4f(color.redF(), color.greenF(), color.blueF(), 0.7)
            glVertex2f(i + 0.1, 0); glVertex2f(i + 0.9, 0); glVertex2f(i + 0.9, row['v']); glVertex2f(i + 0.1, row['v'])
        glEnd(); glDisable(GL_BLEND)
    
    def draw_overlays(self, painter, w, h, price_pane_h, vol_pane_h, df):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing); min_price, price_range = self.get_price_range(df)
        self.draw_price_axis(painter, w, price_pane_h, min_price, price_range)
        self.draw_volume_axis(painter, w, h, vol_pane_h, df['v'].max() if not df['v'].empty else 1)
        self.draw_time_axis_and_separators(painter, w, h, df)
        if self.is_dragging: self.draw_drag_selection(painter, w, price_pane_h, min_price, price_range, df)
        elif self.mouse_pos and self.mode == ChartMode.CURSOR: self.draw_crosshair(painter, w, h, price_pane_h, min_price, price_range, df)

    def draw_drag_selection(self, painter, w, price_pane_h, min_price, price_range, df):
        selection_rect = QRect(self.drag_start_pos, self.drag_end_pos).normalized()
        painter.setBrush(QColor(100, 120, 200, 40)); painter.setPen(QPen(QColor(130, 170, 255), 1)); painter.drawRect(selection_rect)
        
        bar_w = w / self.visible_bars
        start_idx = self.start_bar + int(selection_rect.left() / bar_w); end_idx = self.start_bar + int(selection_rect.right() / bar_w)
        start_idx, end_idx = max(0, start_idx), min(len(self.df) - 1, end_idx)
        if start_idx > end_idx: return
        
        start_row = self.df.iloc[start_idx]; end_row = self.df.iloc[end_idx]
        open_price = start_row['o']; close_price = end_row['c']
        price_change = close_price - open_price
        percent_change = (price_change / open_price) * 100 if open_price != 0 else 0
        change_color = self.up_color if price_change >= 0 else self.down_color
        price_change_str = f"${price_change:+.2f}"; percent_change_str = f"({percent_change:+.2f}%)"
        time_range_str = (f"{start_row['t'].tz_convert('America/New_York').strftime('%H:%M:%S')} to " f"{end_row['t'].tz_convert('America/New_York').strftime('%H:%M:%S')}")
        num_bars = end_idx - start_idx + 1

        info_html = f"""<div style='color:#ddd; font-family: Segoe UI; font-size: 10pt;'>
                        <b>{num_bars} bars</b> ({time_range_str})<br>
                        Change: <span style='color: {change_color.name()}; font-weight: bold;'>{price_change_str} {percent_change_str}</span>
                        </div>"""

        # FIX 2: Use QTextDocument for robust rich text rendering
        painter.save()
        doc = QTextDocument()
        doc.setHtml(info_html)
        doc.setTextWidth(300)
        doc.setDefaultFont(painter.font()) # Use the painter's current font settings

        info_box_size = doc.size()
        info_box_pos = self.drag_end_pos + QPoint(15, 15)
        info_box_rect = QRect(info_box_pos, info_box_size.toSize()).adjusted(-5, -5, 5, 5)

        painter.setBrush(QColor(30, 30, 30, 220)); painter.setPen(QColor(150, 150, 150))
        painter.drawRoundedRect(QRectF(info_box_rect), 3, 3)
        
        painter.translate(info_box_rect.topLeft())
        doc.drawContents(painter)
        painter.restore()

    # (All other helper/drawing methods remain unchanged)
    def get_price_range(self, df):
        min_price_actual=df['l'].min(); max_price_actual=df['h'].max(); center_price=(min_price_actual+max_price_actual)/2
        display_range=(max_price_actual-min_price_actual)*self.zoom_factor if (max_price_actual-min_price_actual)>0 else 1
        return center_price-display_range/2, display_range
    def draw_price_axis(self, painter, w, pane_h, min_price, price_range):
        for i in range(9):
            price = min_price + (i / 8) * price_range; y = pane_h - int(((price - min_price) / price_range) * pane_h)
            painter.setPen(QPen(self.separator_color, 1, Qt.PenStyle.DotLine)); painter.drawLine(0, y, w, y)
            self.draw_highlighted_text(painter, QRectF(w - 75, y - 9, 70, 18), f"{price:.2f}")
    def draw_volume_axis(self, painter, w, h, pane_h, max_volume):
        for i in range(3):
            vol = (i / 2) * max_volume; y = h - int((vol / (max_volume * 1.05)) * pane_h)
            painter.setPen(QPen(self.separator_color, 1, Qt.PenStyle.DotLine)); painter.drawLine(0, y, w, y)
            vol_str = f"{vol/1_000_000:.2f}M" if vol>1_000_000 else f"{vol/1_000:.1f}k" if vol>1_000 else str(int(vol))
            self.draw_highlighted_text(painter, QRectF(w - 75, y - 9, 70, 18), vol_str)
    def draw_time_axis_and_separators(self, painter, w, h, df):
        first_ts = df['t'].iloc[0].tz_convert('America/New_York'); date_str = first_ts.strftime('%Y-%m-%d')
        painter.setFont(QFont('monospace', 10)); painter.setPen(QPen(QColor(200, 200, 200))); painter.drawText(10, 15, date_str)
        last_date = None
        for i, (idx, row) in enumerate(df.iterrows()):
            ts = row['t'].tz_convert('America/New_York')
            if last_date and ts.date() != last_date:
                x = int((i / self.visible_bars) * w); painter.setPen(QPen(self.separator_color, 1, Qt.PenStyle.DashLine)); painter.drawLine(x, 0, x, h - 30)
            last_date = ts.date()
        bar_step = max(1, self.visible_bars // 10)
        for i in range(0, len(df), bar_step):
            ts = df['t'].iloc[i].tz_convert('America/New_York'); x_pos = int(((i + 0.5) / self.visible_bars) * w)
            font = QFont('monospace', 9); font.setBold(True); painter.setFont(font); painter.setPen(QPen(QColor(220, 220, 220)))
            painter.drawText(QRectF(x_pos - 50, h - 25, 100, 20), Qt.AlignmentFlag.AlignCenter, ts.strftime('%H:%M'))
    def draw_crosshair(self, painter, w, h, price_pane_h, min_price, price_range, df):
        pen = QPen(self.crosshair_color, 1, Qt.PenStyle.DashLine); painter.setPen(pen)
        if self.last_hovered_index != -1:
            index_in_view = self.last_hovered_index - self.start_bar
            x = int((index_in_view + 0.5) * (w / self.visible_bars))
            painter.drawLine(x, 0, x, h)
        y = self.mouse_pos.y()
        if y < price_pane_h:
             painter.drawLine(0, y, w, y)
             price = min_price + ((price_pane_h - y) / price_pane_h) * price_range
             self.draw_highlighted_text(painter, QRectF(w - 75, y - 9, 70, 18), f"{price:.2f}", self.crosshair_color)
    def draw_highlighted_text(self, painter, rect, text, bg_color=QColor(40, 40, 40, 180)):
        painter.setBrush(QBrush(bg_color)); painter.setPen(Qt.PenStyle.NoPen); painter.drawRect(rect)
        painter.setPen(QPen(QColor(220, 220, 220))); painter.setFont(QFont('monospace', 9))
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)