# Save this file as chart_renderers.py
from PyQt6.QtGui import QPainter, QPen, QColor, QFont, QBrush, QTextDocument, QLinearGradient
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

        # --- FIX: Identify Doji and normal candles ---
        doji_mask = visible_df['o'] == visible_df['c']
        normal_candles_df = visible_df[~doji_mask]
        doji_candles_df = visible_df[doji_mask]

        is_up = (visible_df['c'] >= visible_df['o']).values
        is_up_normal = (normal_candles_df['c'] >= normal_candles_df['o']).values

        # --- 1. Prepare Wick Data (now includes vertical wicks AND horizontal doji lines) ---
        
        # Start with vertical wicks for ALL candles
        wick_vertices_list = []
        wick_colors_list = []
        
        indices = np.arange(len(visible_df))
        vertical_wick_vertices = np.zeros((len(visible_df) * 2, 2), dtype=np.float32)
        vertical_wick_vertices[0::2, 0] = indices + 0.5; vertical_wick_vertices[0::2, 1] = visible_df['l'].values
        vertical_wick_vertices[1::2, 0] = indices + 0.5; vertical_wick_vertices[1::2, 1] = visible_df['h'].values
        wick_vertices_list.append(vertical_wick_vertices)
        
        up_wick_c = [state.up_wick_color.redF(), state.up_wick_color.greenF(), state.up_wick_color.blueF()]
        down_wick_c = [state.down_wick_color.redF(), state.down_wick_color.greenF(), state.down_wick_color.blueF()]
        all_wick_colors = np.array([up_wick_c if up else down_wick_c for up in is_up], dtype=np.float32)
        wick_colors_list.append(np.repeat(all_wick_colors, 2, axis=0))

        # If there are Dojis, add their horizontal lines
        if not doji_candles_df.empty:
            doji_indices = indices[doji_mask]
            horizontal_doji_lines = np.zeros((len(doji_candles_df) * 2, 2), dtype=np.float32)
            horizontal_doji_lines[0::2, 0] = doji_indices + 0.1 # Start of line (left)
            horizontal_doji_lines[1::2, 0] = doji_indices + 0.9 # End of line (right)
            doji_prices = doji_candles_df['o'].values
            horizontal_doji_lines[:, 1] = np.repeat(doji_prices, 2) # Y-price for both points
            wick_vertices_list.append(horizontal_doji_lines)
            
            # Use the same wick colors for the doji lines
            doji_wick_colors = all_wick_colors[doji_mask]
            wick_colors_list.append(np.repeat(doji_wick_colors, 2, axis=0))

        # Combine all wick/line data
        final_wick_vertices = np.vstack(wick_vertices_list)
        final_wick_colors = np.vstack(wick_colors_list)

        self.wick_vbo.set_array(final_wick_vertices)
        self.wick_color_vbo.set_array(final_wick_colors)
        self.wick_vert_count = len(final_wick_vertices)

        # --- 2. Prepare Body Data (ONLY for normal, non-Doji candles) ---
        if not normal_candles_df.empty:
            normal_indices = indices[~doji_mask]
            body_vertices = np.zeros((len(normal_candles_df) * 4, 2), dtype=np.float32)
            body_vertices[0::4, 0] = normal_indices + 0.1; body_vertices[0::4, 1] = normal_candles_df['o'].values
            body_vertices[1::4, 0] = normal_indices + 0.9; body_vertices[1::4, 1] = normal_candles_df['o'].values
            body_vertices[2::4, 0] = normal_indices + 0.9; body_vertices[2::4, 1] = normal_candles_df['c'].values
            body_vertices[3::4, 0] = normal_indices + 0.1; body_vertices[3::4, 1] = normal_candles_df['c'].values

            up_body_c = [state.up_color.redF(), state.up_color.greenF(), state.up_color.blueF()]
            down_body_c = [state.down_color.redF(), state.down_color.greenF(), state.down_color.blueF()]
            body_colors_np = np.array([up_body_c if up else down_body_c for up in is_up_normal], dtype=np.float32)

            self.body_vbo.set_array(body_vertices)
            self.body_color_vbo.set_array(np.repeat(body_colors_np, 4, axis=0))
            self.body_vert_count = len(body_vertices)
        else:
            self.body_vert_count = 0


    def render(self, state: ChartState, w: int, pane_h: int, y_offset: int):
        if self.wick_vert_count == 0 and self.body_vert_count == 0: return
            
        min_price, display_range = state.get_price_range(state.get_visible_data())
        max_price = min_price + display_range

        glEnable(GL_SCISSOR_TEST); glScissor(0, y_offset, w, pane_h); glViewport(0, y_offset, w, pane_h)
        glMatrixMode(GL_PROJECTION); glLoadIdentity()
        glOrtho(0, state.visible_bars, min_price, max_price, -1, 1)
        glMatrixMode(GL_MODELVIEW); glLoadIdentity()
        
        glEnableClientState(GL_VERTEX_ARRAY); glEnableClientState(GL_COLOR_ARRAY)
        
        # Draw Wicks AND Doji lines together
        if self.wick_vert_count > 0:
            self.wick_vbo.bind(); glVertexPointer(2, GL_FLOAT, 0, self.wick_vbo)
            self.wick_color_vbo.bind(); glColorPointer(3, GL_FLOAT, 0, self.wick_color_vbo)
            glDrawArrays(GL_LINES, 0, self.wick_vert_count)
        
        # Draw Bodies
        if self.body_vert_count > 0:
            self.body_vbo.bind(); glVertexPointer(2, GL_FLOAT, 0, self.body_vbo)
            self.body_color_vbo.bind(); glColorPointer(3, GL_FLOAT, 0, self.body_color_vbo)
            glDrawArrays(GL_QUADS, 0, self.body_vert_count)
            
        glDisableClientState(GL_COLOR_ARRAY); glDisableClientState(GL_VERTEX_ARRAY); glDisable(GL_SCISSOR_TEST)

# ... The rest of chart_renderers.py (VolumePaneRenderer, OverlayRenderer) is unchanged ...
class VolumePaneRenderer:
    def __init__(self):
        self.volume_vbo = vbo.VBO(np.array([], dtype=np.float32)); self.volume_color_vbo = vbo.VBO(np.array([], dtype=np.float32)); self.volume_vert_count = 0
    def update_gl_buffers(self, visible_df: pd.DataFrame, state: ChartState):
        if visible_df.empty: self.volume_vert_count = 0; return
        indices = np.arange(len(visible_df)); volume_vertices = np.zeros((len(visible_df) * 4, 2), dtype=np.float32)
        volume_vertices[0::4, 0] = indices + 0.1; volume_vertices[1::4, 0] = indices + 0.9; volume_vertices[2::4, 0] = indices + 0.9; volume_vertices[3::4, 0] = indices + 0.1
        volume_vertices[2::4, 1] = visible_df['v'].values; volume_vertices[3::4, 1] = visible_df['v'].values
        is_up = (visible_df['c'] >= visible_df['o']).values
        up_c = state.up_volume_color; down_c = state.down_volume_color
        up_color = [up_c.redF(), up_c.greenF(), up_c.blueF(), up_c.alphaF()]
        down_color = [down_c.redF(), down_c.greenF(), down_c.blueF(), down_c.alphaF()]
        colors_np = np.array([up_color if up else down_color for up in is_up], dtype=np.float32)
        self.volume_vbo.set_array(volume_vertices); self.volume_color_vbo.set_array(np.repeat(colors_np, 4, axis=0)); self.volume_vert_count = len(volume_vertices)
    def render(self, state: ChartState, w: int, pane_h: int, y_offset: int):
        if self.volume_vert_count == 0: return
        max_volume = state.get_visible_data()['v'].max() if not state.get_visible_data().empty else 1
        glEnable(GL_SCISSOR_TEST); glScissor(0, y_offset, w, pane_h); glViewport(0, y_offset, w, pane_h)
        glMatrixMode(GL_PROJECTION); glLoadIdentity(); glOrtho(0, state.visible_bars, 0, max_volume * 1.05, -1, 1); glMatrixMode(GL_MODELVIEW); glLoadIdentity()
        glEnable(GL_BLEND); glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA); glEnableClientState(GL_VERTEX_ARRAY); glEnableClientState(GL_COLOR_ARRAY)
        self.volume_vbo.bind(); glVertexPointer(2, GL_FLOAT, 0, self.volume_vbo); self.volume_color_vbo.bind(); glColorPointer(4, GL_FLOAT, 0, self.volume_color_vbo); glDrawArrays(GL_QUADS, 0, self.volume_vert_count)
        glDisableClientState(GL_COLOR_ARRAY); glDisableClientState(GL_VERTEX_ARRAY); glDisable(GL_BLEND); glDisable(GL_SCISSOR_TEST)

class OverlayRenderer:
    def __init__(self):
        self.time_axis_height = 30; self.pane_separator_height = 5
    def draw_background(self, painter: QPainter, state: ChartState, w: int, h: int):
        if state.bg_mode == "Solid": painter.fillRect(0, 0, w, h, state.bg_color1)
        else:
            gradient = QLinearGradient(0, 0, 0, h) if state.bg_gradient_dir == "Vertical" else QLinearGradient(0, 0, w, 0)
            gradient.setColorAt(0.0, state.bg_color1); gradient.setColorAt(1.0, state.bg_color2); painter.fillRect(0, 0, w, h, gradient)
    def render(self, painter: QPainter, state: ChartState, w: int, h: int):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing); visible_df = state.get_visible_data()
        if visible_df.empty: self._draw_symbol_overlay(painter, state); return
        chart_area_h = h - self.time_axis_height; volume_pane_h = int(chart_area_h * state.volume_pane_ratio)
        price_pane_h = chart_area_h - volume_pane_h - self.pane_separator_height; price_pane_top_y = 0
        min_display_price, price_range = state.get_price_range(visible_df)
        self._draw_price_axis(painter, state, w, price_pane_h, price_pane_top_y, min_display_price, price_range); self._draw_time_axis_and_separators(painter, state, w, h, visible_df); self._draw_symbol_overlay(painter, state)
        if state.is_dragging: self._draw_drag_selection(painter, state, w, h)
        elif state.mouse_pos and state.mode == ChartMode.CURSOR: self._draw_crosshair(painter, state, w, h, price_pane_top_y, price_pane_h, min_display_price, price_range)
    def _draw_highlighted_text(self, painter, rect, text, bg_color=QColor(40, 40, 40, 180)):
        painter.save(); painter.setBrush(QBrush(bg_color)); painter.setPen(Qt.PenStyle.NoPen); painter.drawRect(rect)
        painter.setPen(QPen(QColor(220, 220, 220))); painter.setFont(QFont('monospace', 9)); painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, text); painter.restore()
    def _draw_price_axis(self, painter: QPainter, state: ChartState, w: int, pane_h: int, pane_top_y: int, min_display_price: float, price_range: float):
        if price_range <= 0: return
        painter.setPen(QPen(state.price_grid_color, state.price_grid_width, state.price_grid_style))
        def price_to_y(price): return pane_top_y + ((1 - (price - min_display_price) / price_range) * pane_h)
        num_lines = max(2, int(pane_h / 75))
        for i in range(1, num_lines):
            price = min_display_price + (i / num_lines) * price_range; y = int(price_to_y(price))
            painter.setPen(QPen(state.price_grid_color, state.price_grid_width, state.price_grid_style)); painter.drawLine(0, y, w - 80, y)
            self._draw_highlighted_text(painter, QRectF(w - 75, y - 9, 70, 18), f"{price:.2f}")
    def _draw_time_axis_and_separators(self, painter: QPainter, state: ChartState, w: int, h: int, df: pd.DataFrame):
        time_pen = QPen(state.time_grid_color, state.time_grid_width, state.time_grid_style); text_pen = QPen(QColor(220, 220, 220)); font = QFont('monospace', 9); font.setBold(True); painter.setFont(font)
        last_date = df['t'].iloc[0].tz_convert('America/New_York').date() if not df.empty else None
        for i, (idx, row) in enumerate(df.iterrows()):
            ts = row['t'].tz_convert('America/New_York')
            if last_date and ts.date() != last_date:
                x = int((i / state.visible_bars) * w)
                painter.setPen(time_pen); painter.drawLine(x, 0, x, h - self.time_axis_height)
                painter.setPen(text_pen); painter.drawText(QRectF(x + 5, h - 25, 60, 20), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, ts.strftime('%d %b'))
            last_date = ts.date()
    def _draw_symbol_overlay(self, painter: QPainter, state: ChartState):
        if not state.symbol_text: return
        painter.setFont(QFont('Segoe UI', 14, QFont.Weight.Bold)); painter.setPen(QColor(220, 220, 220, 200)); painter.drawText(QRectF(15, 5, 500, 30), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, state.symbol_text)
    def _draw_drag_selection(self, painter: QPainter, state: ChartState, w: int, h: int): pass
    def _draw_crosshair(self, painter: QPainter, state: ChartState, w: int, h: int, price_pane_top_y: int, price_pane_h: int, min_price: float, price_range: float):
        if not state.mouse_pos: return
        painter.setPen(QPen(state.crosshair_color, state.crosshair_width, state.crosshair_style))
        if state.last_hovered_index != -1:
            x = int((state.last_hovered_index - state.start_bar + 0.5) * (w / state.visible_bars)); painter.drawLine(x, 0, x, h)
        y = state.mouse_pos.y()
        if y < h - self.time_axis_height:
            painter.drawLine(0, y, w, y)
            if y >= price_pane_top_y and y < price_pane_top_y + price_pane_h and price_range > 0:
                price = min_price + ((price_pane_top_y + price_pane_h - y) / price_pane_h) * price_range
                self._draw_highlighted_text(painter, QRectF(w - 75, y - 9, 70, 18), f"{price:.2f}", state.crosshair_color)