# Save this file as chart_renderers.py
from PyQt6.QtGui import QPainter, QPen, QColor, QFont, QBrush, QTextDocument
from PyQt6.QtCore import Qt, QRectF, QPoint, QRect
from OpenGL.GL import *
from OpenGL.arrays import vbo
import pandas as pd
import numpy as np

from chart_enums import ChartMode
from chart_state import ChartState

class PricePaneRenderer:
    """Renders the main price candlestick chart using high-performance VBOs."""
    def __init__(self):
        self.wick_vbo = vbo.VBO(np.array([], dtype=np.float32))
        self.wick_color_vbo = vbo.VBO(np.array([], dtype=np.float32))
        self.body_vbo = vbo.VBO(np.array([], dtype=np.float32))
        self.body_color_vbo = vbo.VBO(np.array([], dtype=np.float32))
        self.wick_vert_count = 0
        self.body_vert_count = 0

    def update_gl_buffers(self, visible_df: pd.DataFrame, state: ChartState):
        if visible_df.empty:
            self.wick_vert_count = 0
            self.body_vert_count = 0
            return

        # Prepare Wick Data (2 vertices per wick)
        wick_vertices = np.zeros((len(visible_df) * 2, 2), dtype=np.float32)
        indices = np.arange(len(visible_df))
        wick_vertices[0::2, 0] = indices + 0.5 # x for low
        wick_vertices[0::2, 1] = visible_df['l'].values # y for low
        wick_vertices[1::2, 0] = indices + 0.5 # x for high
        wick_vertices[1::2, 1] = visible_df['h'].values # y for high
        
        wick_colors = np.full((len(visible_df) * 2, 3), [0.5, 0.5, 0.5], dtype=np.float32)

        self.wick_vbo.set_array(wick_vertices)
        self.wick_color_vbo.set_array(wick_colors)
        self.wick_vert_count = len(wick_vertices)

        # Prepare Body Data (4 vertices per body)
        body_vertices = np.zeros((len(visible_df) * 4, 2), dtype=np.float32)
        body_vertices[0::4, 0] = indices + 0.1; body_vertices[0::4, 1] = visible_df['o'].values
        body_vertices[1::4, 0] = indices + 0.9; body_vertices[1::4, 1] = visible_df['o'].values
        body_vertices[2::4, 0] = indices + 0.9; body_vertices[2::4, 1] = visible_df['c'].values
        body_vertices[3::4, 0] = indices + 0.1; body_vertices[3::4, 1] = visible_df['c'].values

        is_up = (visible_df['c'] >= visible_df['o']).values
        up_color = [state.up_color.redF(), state.up_color.greenF(), state.up_color.blueF()]
        down_color = [state.down_color.redF(), state.down_color.greenF(), state.down_color.blueF()]
        
        colors = np.array([up_color if up else down_color for up in is_up], dtype=np.float32)
        body_colors = np.repeat(colors, 4, axis=0) # Repeat color for each of the 4 vertices

        self.body_vbo.set_array(body_vertices)
        self.body_color_vbo.set_array(body_colors)
        self.body_vert_count = len(body_vertices)

    def render(self, state: ChartState, w: int, pane_h: int, y_offset: int):
        if self.wick_vert_count == 0 and self.body_vert_count == 0:
            return
            
        min_price, display_range = state.get_price_range(state.get_visible_data())
        max_price = min_price + display_range

        glEnable(GL_SCISSOR_TEST)
        glScissor(0, y_offset, w, pane_h)
        glViewport(0, y_offset, w, pane_h)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        glOrtho(0, state.visible_bars, min_price, max_price, -1, 1)
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        
        glEnableClientState(GL_VERTEX_ARRAY)
        glEnableClientState(GL_COLOR_ARRAY)

        # Draw Wicks
        self.wick_vbo.bind()
        glVertexPointer(2, GL_FLOAT, 0, self.wick_vbo)
        self.wick_color_vbo.bind()
        glColorPointer(3, GL_FLOAT, 0, self.wick_color_vbo)
        glDrawArrays(GL_LINES, 0, self.wick_vert_count)
        
        # Draw Bodies
        self.body_vbo.bind()
        glVertexPointer(2, GL_FLOAT, 0, self.body_vbo)
        self.body_color_vbo.bind()
        glColorPointer(3, GL_FLOAT, 0, self.body_color_vbo)
        glDrawArrays(GL_QUADS, 0, self.body_vert_count)

        glDisableClientState(GL_COLOR_ARRAY)
        glDisableClientState(GL_VERTEX_ARRAY)
        glDisable(GL_SCISSOR_TEST)

class VolumePaneRenderer:
    """Renders the volume bars using high-performance VBOs."""
    def __init__(self):
        self.volume_vbo = vbo.VBO(np.array([], dtype=np.float32))
        self.volume_color_vbo = vbo.VBO(np.array([], dtype=np.float32))
        self.volume_vert_count = 0
        
    def update_gl_buffers(self, visible_df: pd.DataFrame, state: ChartState):
        if visible_df.empty:
            self.volume_vert_count = 0
            return
            
        volume_vertices = np.zeros((len(visible_df) * 4, 2), dtype=np.float32)
        indices = np.arange(len(visible_df))
        volume_vertices[0::4, 0] = indices + 0.1; volume_vertices[0::4, 1] = 0
        volume_vertices[1::4, 0] = indices + 0.9; volume_vertices[1::4, 1] = 0
        volume_vertices[2::4, 0] = indices + 0.9; volume_vertices[2::4, 1] = visible_df['v'].values
        volume_vertices[3::4, 0] = indices + 0.1; volume_vertices[3::4, 1] = visible_df['v'].values
        
        is_up = (visible_df['c'] >= visible_df['o']).values
        up_color = [state.up_color.redF(), state.up_color.greenF(), state.up_color.blueF(), 0.7]
        down_color = [state.down_color.redF(), state.down_color.greenF(), state.down_color.blueF(), 0.7]
        colors = np.array([up_color if up else down_color for up in is_up], dtype=np.float32)
        volume_colors = np.repeat(colors, 4, axis=0)

        self.volume_vbo.set_array(volume_vertices)
        self.volume_color_vbo.set_array(volume_colors)
        self.volume_vert_count = len(volume_vertices)

    def render(self, state: ChartState, w: int, pane_h: int, y_offset: int):
        if self.volume_vert_count == 0: return
        
        visible_df = state.get_visible_data() # Still needed for max_volume
        max_volume = visible_df['v'].max() if not visible_df['v'].empty else 1
        
        glEnable(GL_SCISSOR_TEST)
        glScissor(0, y_offset, w, pane_h)
        glViewport(0, y_offset, w, pane_h)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        glOrtho(0, state.visible_bars, 0, max_volume * 1.05, -1, 1)
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        
        glEnableClientState(GL_VERTEX_ARRAY)
        glEnableClientState(GL_COLOR_ARRAY)
        
        self.volume_vbo.bind()
        glVertexPointer(2, GL_FLOAT, 0, self.volume_vbo)
        self.volume_color_vbo.bind()
        glColorPointer(4, GL_FLOAT, 0, self.volume_color_vbo)
        glDrawArrays(GL_QUADS, 0, self.volume_vert_count)

        glDisableClientState(GL_COLOR_ARRAY)
        glDisableClientState(GL_VERTEX_ARRAY)
        glDisable(GL_BLEND)
        glDisable(GL_SCISSOR_TEST)

class OverlayRenderer:
    """Renders all non-OpenGL overlays like axes, text, and crosshairs using QPainter."""
    
    def render(self, painter: QPainter, state: ChartState, w: int, h: int):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        visible_df = state.get_visible_data()
        if visible_df.empty:
            return

        # Calculate pane geometry (again, for painter coordinates)
        chart_area_h = h - self.time_axis_height
        volume_pane_h = int(chart_area_h * state.volume_pane_ratio)
        price_pane_h = chart_area_h - volume_pane_h - self.pane_separator_height
        price_pane_top_y = h - self.time_axis_height - volume_pane_h - self.pane_separator_height - price_pane_h
        volume_pane_top_y = h - self.time_axis_height - volume_pane_h
        
        min_display_price, price_range = state.get_price_range(visible_df)
        
        self._draw_price_axis(painter, state, w, price_pane_h, price_pane_top_y, min_display_price, price_range, visible_df)
        self._draw_volume_axis(painter, state, w, volume_pane_h, volume_pane_top_y, visible_df)
        self._draw_time_axis_and_separators(painter, state, w, h, visible_df)
        self._draw_symbol_overlay(painter, state)
        
        if state.is_dragging:
            self._draw_drag_selection(painter, state, w, h)
        elif state.mouse_pos and state.mode == ChartMode.CURSOR:
            self._draw_crosshair(painter, state, w, h, price_pane_top_y, price_pane_h, min_display_price, price_range)

    def __init__(self):
        # Constants that were part of CandleWidget, now part of the relevant renderer
        self.time_axis_height = 30
        self.pane_separator_height = 5
        
    def _draw_highlighted_text(self, painter, rect, text, bg_color=QColor(40, 40, 40, 180)):
        painter.setBrush(QBrush(bg_color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRect(rect)
        painter.setPen(QPen(QColor(220, 220, 220)))
        painter.setFont(QFont('monospace', 9))
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)

    def _draw_price_axis(self, painter: QPainter, state: ChartState, w: int, pane_h: int, pane_top_y: int, min_display_price: float, price_range: float, df: pd.DataFrame):
        def price_to_y(price):
            if price_range == 0: return pane_top_y + pane_h / 2
            price_ratio = (price - min_display_price) / price_range
            return pane_top_y + ((1 - price_ratio) * pane_h)
        
        for i in range(1, 8):
            price = min_display_price + (i / 8) * price_range
            y = int(price_to_y(price))
            painter.setPen(QPen(state.separator_color, 1, Qt.PenStyle.DotLine))
            painter.drawLine(0, y, w, y)
            self._draw_highlighted_text(painter, QRectF(w - 75, y - 9, 70, 18), f"{price:.2f}")

        if not df.empty:
            actual_max = df['h'].max()
            actual_min = df['l'].min()
            y_max = int(price_to_y(actual_max))
            self._draw_highlighted_text(painter, QRectF(w - 75, y_max - 9, 70, 18), f"{actual_max:.2f}")
            y_min = int(price_to_y(actual_min))
            self._draw_highlighted_text(painter, QRectF(w - 75, y_min - 9, 70, 18), f"{actual_min:.2f}")

    def _draw_volume_axis(self, painter: QPainter, state: ChartState, w: int, pane_h: int, pane_top_y: int, df: pd.DataFrame):
        if df.empty: return
        max_volume = df['v'].max() if not df['v'].empty else 1
        for i in range(1, 3):
            vol = (i / 2) * max_volume
            vol_ratio = vol / (max_volume * 1.05)
            y = int(pane_top_y + ((1 - vol_ratio) * pane_h))
            painter.setPen(QPen(state.separator_color, 1, Qt.PenStyle.DotLine))
            painter.drawLine(0, y, w, y)

    def _draw_time_axis_and_separators(self, painter: QPainter, state: ChartState, w: int, h: int, df: pd.DataFrame):
        last_date = None
        if not df.empty:
            last_date = df['t'].iloc[0].tz_convert('America/New_York').date()
        
        bar_step = max(1, state.visible_bars // 10)
        for i in range(0, len(df), bar_step):
            ts = df['t'].iloc[i].tz_convert('America/New_York')
            x_pos = int(((i + 0.5) / state.visible_bars) * w)
            time_str = ts.strftime('%H:%M')
            
            alignment = Qt.AlignmentFlag.AlignCenter
            rect = QRectF(x_pos - 50, h - 25, 100, 20)
            
            if i == 0 and rect.left() < 0:
                alignment = Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
            
            font = QFont('monospace', 9); font.setBold(True); painter.setFont(font); painter.setPen(QPen(QColor(220, 220, 220)))
            painter.drawText(rect, alignment, time_str)

        for i, (idx, row) in enumerate(df.iterrows()):
            ts = row['t'].tz_convert('America/New_York')
            current_date = ts.date()
            if last_date and current_date != last_date:
                x = int((i / state.visible_bars) * w)
                painter.setPen(QPen(state.separator_color, 1, Qt.PenStyle.DashLine)); painter.drawLine(x, self.time_axis_height, x, h)
                date_str = ts.strftime('%d %b')
                font = QFont('monospace', 9); font.setBold(True); painter.setFont(font)
                painter.setPen(QPen(QColor(220, 220, 220, 180)))
                painter.drawText(QRectF(x + 5, h - 25, 60, 20), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, date_str)
            last_date = current_date
            
    def _draw_symbol_overlay(self, painter: QPainter, state: ChartState):
        if not state.symbol_text:
            return
        font = QFont('Segoe UI', 14)
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(QColor(220, 220, 220, 200))
        painter.drawText(QRectF(15, 5, 500, 30), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, state.symbol_text)

    def _draw_drag_selection(self, painter: QPainter, state: ChartState, w: int, h: int):
        selection_rect = QRect(state.drag_start_pos, state.drag_end_pos).normalized()
        painter.setBrush(QColor(100, 120, 200, 40))
        painter.setPen(QPen(QColor(130, 170, 255), 1))
        painter.drawRect(selection_rect)
        
        bar_w = w / state.visible_bars
        start_idx = state.start_bar + int(selection_rect.left() / bar_w)
        end_idx = state.start_bar + int(selection_rect.right() / bar_w)
        start_idx, end_idx = max(0, start_idx), min(len(state.df) - 1, end_idx)
        if start_idx > end_idx: return
        
        start_row = state.df.iloc[start_idx]; end_row = state.df.iloc[end_idx]
        open_price = start_row['o']; close_price = end_row['c']
        price_change = close_price - open_price
        percent_change = (price_change / open_price) * 100 if open_price != 0 else 0
        change_color = state.up_color if price_change >= 0 else state.down_color
        price_change_str = f"${price_change:+.2f}"; percent_change_str = f"({percent_change:+.2f}%)"
        time_range_str = (f"{start_row['t'].tz_convert('America/New_York').strftime('%H:%M:%S')} to " f"{end_row['t'].tz_convert('America/New_York').strftime('%H:%M:%S')}")
        num_bars = end_idx - start_idx + 1

        info_html = f"""<div style='color:#ddd; font-family: Segoe UI; font-size: 10pt;'>
                        <b>{num_bars} bars</b> ({time_range_str})<br>
                        Change: <span style='color: {change_color.name()}; font-weight: bold;'>{price_change_str} {percent_change_str}</span>
                        </div>"""
        doc = QTextDocument()
        doc.setHtml(info_html)
        doc.setTextWidth(300)
        doc.setDefaultFont(painter.font())

        info_box_size = doc.size()
        info_box_pos = state.drag_end_pos + QPoint(15, 15)
        info_box_rect = QRect(info_box_pos, info_box_size.toSize()).adjusted(-5, -5, 5, 5)

        painter.setBrush(QColor(30, 30, 30, 220)); painter.setPen(QColor(150, 150, 150))
        painter.drawRoundedRect(QRectF(info_box_rect), 3, 3)
        
        painter.save()
        painter.translate(info_box_rect.topLeft())
        doc.drawContents(painter)
        painter.restore()

    def _draw_crosshair(self, painter: QPainter, state: ChartState, w: int, h: int, price_pane_top_y: int, price_pane_h: int, min_price: float, price_range: float):
        pen = QPen(state.crosshair_color, 1, Qt.PenStyle.DashLine)
        painter.setPen(pen)
        
        if state.last_hovered_index != -1:
            index_in_view = state.last_hovered_index - state.start_bar
            x = int((index_in_view + 0.5) * (w / state.visible_bars))
            painter.drawLine(x, self.time_axis_height, x, h)
        
        y = state.mouse_pos.y()
        if y < h - self.time_axis_height:
            painter.drawLine(0, y, w, y)
        
        if y >= price_pane_top_y and y < price_pane_top_y + price_pane_h:
             price = min_price + ((price_pane_top_y + price_pane_h - y) / price_pane_h) * price_range
             self._draw_highlighted_text(painter, QRectF(w - 75, y - 9, 70, 18), f"{price:.2f}", state.crosshair_color)