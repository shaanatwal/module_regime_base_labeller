from PyQt6.QtGui import (QPainter, QPen, QColor, QFont, QBrush, 
                         QLinearGradient)
from PyQt6.QtCore import Qt, QRectF, QPoint, QRect
from OpenGL.GL import *
from OpenGL.arrays import vbo
import pandas as pd
import numpy as np

from chart_enums import ChartMode
from chart_state import ChartState

class PricePaneRenderer:
    """
    Manages the high-performance rendering of the main candlestick price chart.

    This class leverages OpenGL Vertex Buffer Objects (VBOs) to draw a large
    number of candlestick shapes (bodies and wicks) with minimal CPU overhead,
    making the chart fast and responsive. It separates regular candles from
    Doji candles for optimized drawing.
    """
    def __init__(self):
        """Initializes VBOs for storing vertex and color data for candles."""
        # VBO for the vertical high-low lines (wicks) and horizontal Doji lines.
        self.wick_vbo = vbo.VBO(np.array([], dtype=np.float32))
        self.wick_color_vbo = vbo.VBO(np.array([], dtype=np.float32))
        
        # VBO for the rectangular open-close bodies of the candles.
        self.body_vbo = vbo.VBO(np.array([], dtype=np.float32))
        self.body_color_vbo = vbo.VBO(np.array([], dtype=np.float32))

        # Vertex counts, used by the render method to know how many vertices to draw.
        self.wick_vert_count = 0
        self.body_vert_count = 0

    def update_gl_buffers(self, visible_df: pd.DataFrame, state: ChartState):
        """
        Calculates and uploads candlestick geometry to the GPU.

        This method processes the visible portion of the DataFrame, calculates
        the vertex positions and colors for all wicks and bodies, and transfers
        this data into the VBOs on the graphics card. This is the most
        performance-critical part of the rendering pipeline.

        Args:
            visible_df: DataFrame slice containing only the data for visible bars.
            state: The current state of the chart, providing style information.
        """
        if visible_df.empty:
            self.wick_vert_count = 0
            self.body_vert_count = 0
            return

        # --- Data Preparation ---
        # A Doji candle (open == close) is drawn as a horizontal line, not a quad.
        # We separate them from normal candles for specialized processing.
        doji_mask = visible_df['o'] == visible_df['c']
        normal_candles_df = visible_df[~doji_mask]
        doji_candles_df = visible_df[doji_mask]

        is_up = (visible_df['c'] >= visible_df['o']).values
        is_up_normal = (normal_candles_df['c'] >= normal_candles_df['o']).values
        indices = np.arange(len(visible_df))

        # --- 1. Prepare Wick & Doji Line Data ---
        # We combine all line-based geometry (vertical wicks and horizontal doji lines)
        # into a single VBO for efficient drawing with one GL_LINES call.
        wick_vertices_list = []
        wick_colors_list = []
        
        # Generate vertical wick lines for all candles (Dojis included).
        # Each line requires two vertices (top and bottom).
        vertical_wick_vertices = np.zeros((len(visible_df) * 2, 2), dtype=np.float32)
        vertical_wick_vertices[0::2, 0] = indices + 0.5  # X-coordinate (center of bar)
        vertical_wick_vertices[0::2, 1] = visible_df['l'].values  # Y-coordinate (low price)
        vertical_wick_vertices[1::2, 0] = indices + 0.5  # X-coordinate (center of bar)
        vertical_wick_vertices[1::2, 1] = visible_df['h'].values  # Y-coordinate (high price)
        wick_vertices_list.append(vertical_wick_vertices)
        
        # Define wick colors based on whether the candle is up or down.
        up_wick_c = [state.up_wick_color.redF(), state.up_wick_color.greenF(), state.up_wick_color.blueF()]
        down_wick_c = [state.down_wick_color.redF(), state.down_wick_color.greenF(), state.down_wick_color.blueF()]
        all_wick_colors = np.array([up_wick_c if up else down_wick_c for up in is_up], dtype=np.float32)
        wick_colors_list.append(np.repeat(all_wick_colors, 2, axis=0))

        # Generate horizontal lines for Doji candles if any exist.
        if not doji_candles_df.empty:
            doji_indices = indices[doji_mask]
            horizontal_doji_lines = np.zeros((len(doji_candles_df) * 2, 2), dtype=np.float32)
            # The x-coordinates define a horizontal line centered in the bar's space.
            horizontal_doji_lines[0::2, 0] = doji_indices + 0.1 # Left edge of the line
            horizontal_doji_lines[1::2, 0] = doji_indices + 0.9 # Right edge of the line
            # The y-coordinate is the open/close price.
            doji_prices = doji_candles_df['o'].values
            horizontal_doji_lines[:, 1] = np.repeat(doji_prices, 2)
            wick_vertices_list.append(horizontal_doji_lines)
            
            # Use the same wick colors for the Doji lines.
            doji_wick_colors = all_wick_colors[doji_mask]
            wick_colors_list.append(np.repeat(doji_wick_colors, 2, axis=0))

        # Combine all vertex/color data and upload to the GPU.
        final_wick_vertices = np.vstack(wick_vertices_list)
        final_wick_colors = np.vstack(wick_colors_list)
        self.wick_vbo.set_array(final_wick_vertices)
        self.wick_color_vbo.set_array(final_wick_colors)
        self.wick_vert_count = len(final_wick_vertices)

        # --- 2. Prepare Body Data (Non-Doji candles only) ---
        if not normal_candles_df.empty:
            normal_indices = indices[~doji_mask]
            # Each body is a quad, requiring four vertices.
            body_vertices = np.zeros((len(normal_candles_df) * 4, 2), dtype=np.float32)
            body_vertices[0::4, 0] = normal_indices + 0.1; body_vertices[0::4, 1] = normal_candles_df['o'].values # Top-left
            body_vertices[1::4, 0] = normal_indices + 0.9; body_vertices[1::4, 1] = normal_candles_df['o'].values # Top-right
            body_vertices[2::4, 0] = normal_indices + 0.9; body_vertices[2::4, 1] = normal_candles_df['c'].values # Bottom-right
            body_vertices[3::4, 0] = normal_indices + 0.1; body_vertices[3::4, 1] = normal_candles_df['c'].values # Bottom-left

            up_body_c = [state.up_color.redF(), state.up_color.greenF(), state.up_color.blueF()]
            down_body_c = [state.down_color.redF(), state.down_color.greenF(), state.down_color.blueF()]
            body_colors_np = np.array([up_body_c if up else down_body_c for up in is_up_normal], dtype=np.float32)

            self.body_vbo.set_array(body_vertices)
            self.body_color_vbo.set_array(np.repeat(body_colors_np, 4, axis=0))
            self.body_vert_count = len(body_vertices)
        else:
            self.body_vert_count = 0

    def render(self, state: ChartState, w: int, pane_h: int, y_offset: int):
        """
        Draws the candlesticks for the price pane using pre-calculated VBOs.

        Args:
            state: The current chart state, containing viewport and data info.
            w: The width of the viewport.
            pane_h: The height of the price pane.
            y_offset: The vertical pixel offset of the pane from the window bottom.
        """
        if self.wick_vert_count == 0 and self.body_vert_count == 0: return
            
        min_price, display_range = state.get_price_range(state.get_visible_data())
        max_price = min_price + display_range

        # Configure OpenGL for this specific pane:
        # glScissor/glViewport create a "drawing sub-window" for this pane.
        # glOrtho sets up a 2D projection matrix that maps our data coordinates
        # (bar index, price) directly to the screen area of the pane.
        glEnable(GL_SCISSOR_TEST); glScissor(0, y_offset, w, pane_h)
        glViewport(0, y_offset, w, pane_h)
        glMatrixMode(GL_PROJECTION); glLoadIdentity()
        glOrtho(0, state.visible_bars, min_price, max_price, -1, 1)
        glMatrixMode(GL_MODELVIEW); glLoadIdentity()
        
        # Enable arrays for vertex and color data.
        glEnableClientState(GL_VERTEX_ARRAY); glEnableClientState(GL_COLOR_ARRAY)
        
        # Draw Wicks and Doji Lines (GL_LINES)
        if self.wick_vert_count > 0:
            self.wick_vbo.bind(); glVertexPointer(2, GL_FLOAT, 0, self.wick_vbo)
            self.wick_color_vbo.bind(); glColorPointer(3, GL_FLOAT, 0, self.wick_color_vbo)
            glDrawArrays(GL_LINES, 0, self.wick_vert_count)
        
        # Draw Candle Bodies (GL_QUADS)
        if self.body_vert_count > 0:
            self.body_vbo.bind(); glVertexPointer(2, GL_FLOAT, 0, self.body_vbo)
            self.body_color_vbo.bind(); glColorPointer(3, GL_FLOAT, 0, self.body_color_vbo)
            glDrawArrays(GL_QUADS, 0, self.body_vert_count)
            
        # Clean up OpenGL state.
        glDisableClientState(GL_COLOR_ARRAY); glDisableClientState(GL_VERTEX_ARRAY)
        glDisable(GL_SCISSOR_TEST)

class VolumePaneRenderer:
    """
    Manages the high-performance rendering of the volume bars pane.

    Similar to PricePaneRenderer, this class uses VBOs to draw volume bars
    as colored quads, ensuring smooth performance.
    """
    def __init__(self):
        """Initializes VBOs for storing volume bar geometry and colors."""
        self.volume_vbo = vbo.VBO(np.array([], dtype=np.float32))
        self.volume_color_vbo = vbo.VBO(np.array([], dtype=np.float32))
        self.volume_vert_count = 0

    def update_gl_buffers(self, visible_df: pd.DataFrame, state: ChartState):
        """Calculates and uploads volume bar geometry to the GPU."""
        if visible_df.empty: 
            self.volume_vert_count = 0
            return
            
        indices = np.arange(len(visible_df))
        # Each volume bar is a quad defined by 4 vertices.
        volume_vertices = np.zeros((len(visible_df) * 4, 2), dtype=np.float32)
        # The bottom y-coordinate is always 0. The top y-coordinate is the volume.
        volume_vertices[0::4, 0] = indices + 0.1; volume_vertices[0::4, 1] = 0 # Bottom-left
        volume_vertices[1::4, 0] = indices + 0.9; volume_vertices[1::4, 1] = 0 # Bottom-right
        volume_vertices[2::4, 0] = indices + 0.9; volume_vertices[2::4, 1] = visible_df['v'].values # Top-right
        volume_vertices[3::4, 0] = indices + 0.1; volume_vertices[3::4, 1] = visible_df['v'].values # Top-left
        
        # Determine colors based on the corresponding price candle's direction.
        is_up = (visible_df['c'] >= visible_df['o']).values
        up_c = state.up_volume_color; down_c = state.down_volume_color
        # Note: Volume colors include an alpha component for semi-transparency.
        up_color = [up_c.redF(), up_c.greenF(), up_c.blueF(), up_c.alphaF()]
        down_color = [down_c.redF(), down_c.greenF(), down_c.blueF(), down_c.alphaF()]
        colors_np = np.array([up_color if up else down_color for up in is_up], dtype=np.float32)
        
        self.volume_vbo.set_array(volume_vertices)
        self.volume_color_vbo.set_array(np.repeat(colors_np, 4, axis=0))
        self.volume_vert_count = len(volume_vertices)

    def render(self, state: ChartState, w: int, pane_h: int, y_offset: int):
        """Draws the volume bars using pre-calculated VBOs."""
        if self.volume_vert_count == 0: return

        # Find the max volume in the visible range to scale the y-axis.
        max_volume = state.get_visible_data()['v'].max() if not state.get_visible_data().empty else 1
        
        # Set up the OpenGL projection for the volume pane.
        glEnable(GL_SCISSOR_TEST); glScissor(0, y_offset, w, pane_h)
        glViewport(0, y_offset, w, pane_h)
        glMatrixMode(GL_PROJECTION); glLoadIdentity()
        # The Y-axis goes from 0 to the max volume + 5% padding.
        glOrtho(0, state.visible_bars, 0, max_volume * 1.05, -1, 1)
        glMatrixMode(GL_MODELVIEW); glLoadIdentity()
        
        # Enable alpha blending for semi-transparent volume bars.
        glEnable(GL_BLEND); glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glEnableClientState(GL_VERTEX_ARRAY); glEnableClientState(GL_COLOR_ARRAY)
        
        self.volume_vbo.bind(); glVertexPointer(2, GL_FLOAT, 0, self.volume_vbo)
        # Note: We specify 4 components for color (RGBA).
        self.volume_color_vbo.bind(); glColorPointer(4, GL_FLOAT, 0, self.volume_color_vbo)
        glDrawArrays(GL_QUADS, 0, self.volume_vert_count)
        
        # Clean up OpenGL state.
        glDisableClientState(GL_COLOR_ARRAY); glDisableClientState(GL_VERTEX_ARRAY)
        glDisable(GL_BLEND); glDisable(GL_SCISSOR_TEST)


class OverlayRenderer:
    """
    Renders all 2D UI elements on top of the chart using QPainter.

    This includes price/time axes, grid lines, the crosshair, the symbol text,
    and the chart background. These elements are not performance-intensive
    and are easier to draw with the high-level QPainter API.
    """
    def __init__(self):
        """Initializes constants for UI element dimensions."""
        self.time_axis_height = 30
        self.pane_separator_height = 5

    def draw_background(self, painter: QPainter, state: ChartState, w: int, h: int):
        """
        Draws the chart background, supporting solid or gradient fills.
        
        This method is called first in the paint cycle to clear the canvas.
        """
        if state.bg_mode == "Solid":
            painter.fillRect(0, 0, w, h, state.bg_color1)
        else: # Gradient mode
            gradient = QLinearGradient(0, 0, 0, h) if state.bg_gradient_dir == "Vertical" else QLinearGradient(0, 0, w, 0)
            gradient.setColorAt(0.0, state.bg_color1)
            gradient.setColorAt(1.0, state.bg_color2)
            painter.fillRect(0, 0, w, h, gradient)

    def render(self, painter: QPainter, state: ChartState, w: int, h: int):
        """
        Draws all foreground overlay elements.

        This method orchestrates the drawing of axes, labels, and the crosshair
        after the OpenGL panes have been rendered.

        Args:
            painter: The QPainter instance to use for drawing.
            state: The current chart state.
            w: The width of the widget.
            h: The height of the widget.
        """
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        visible_df = state.get_visible_data()

        if visible_df.empty:
            self._draw_symbol_overlay(painter, state)
            return

        # Calculate pane dimensions based on the available area.
        chart_area_h = h - self.time_axis_height
        volume_pane_h = int(chart_area_h * state.volume_pane_ratio)
        price_pane_h = chart_area_h - volume_pane_h - self.pane_separator_height
        price_pane_top_y = 0
        
        min_display_price, price_range = state.get_price_range(visible_df)

        # Draw UI components.
        self._draw_price_axis(painter, state, w, price_pane_h, price_pane_top_y, min_display_price, price_range)
        self._draw_time_axis_and_separators(painter, state, w, h, visible_df)
        self._draw_symbol_overlay(painter, state)
        
        # Draw interactive elements.
        if state.is_dragging:
            self._draw_drag_selection(painter, state, w, h)
        elif state.mouse_pos and state.mode == ChartMode.CURSOR:
            self._draw_crosshair(painter, state, w, h, price_pane_top_y, price_pane_h, min_display_price, price_range)

    def _draw_highlighted_text(self, painter, rect, text, bg_color=QColor(40, 40, 40, 180)):
        """Utility function to draw text with a semi-transparent background."""
        painter.save()
        painter.setBrush(QBrush(bg_color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRect(rect)
        painter.setPen(QPen(QColor(220, 220, 220)))
        painter.setFont(QFont('monospace', 9))
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)
        painter.restore()

    def _draw_price_axis(self, painter: QPainter, state: ChartState, w: int, pane_h: int, pane_top_y: int, min_display_price: float, price_range: float):
        """Draws the horizontal price grid lines and their corresponding price labels."""
        if price_range <= 0: return
            
        # A helper to convert a price value to a Y-pixel coordinate.
        def price_to_y(price):
            return pane_top_y + ((1 - (price - min_display_price) / price_range) * pane_h)

        # Dynamically determine a reasonable number of grid lines based on pane height.
        num_lines = max(2, int(pane_h / 75))
        
        for i in range(1, num_lines):
            price = min_display_price + (i / num_lines) * price_range
            y = int(price_to_y(price))
            painter.setPen(QPen(state.price_grid_color, state.price_grid_width, state.price_grid_style))
            # Draw grid line across most of the chart.
            painter.drawLine(0, y, w - 80, y) 
            # Draw the price label on the far right.
            self._draw_highlighted_text(painter, QRectF(w - 75, y - 9, 70, 18), f"{price:.2f}")

    def _draw_time_axis_and_separators(self, painter: QPainter, state: ChartState, w: int, h: int, df: pd.DataFrame):
        """Draws vertical time grid lines that separate days, and renders time labels."""
        time_pen = QPen(state.time_grid_color, state.time_grid_width, state.time_grid_style)
        text_pen = QPen(QColor(220, 220, 220))
        font = QFont('monospace', 9); font.setBold(True); painter.setFont(font)
        
        last_date = df['t'].iloc[0].tz_convert('America/New_York').date() if not df.empty else None
        
        # Iterate through visible bars to find where the date changes.
        for i, (idx, row) in enumerate(df.iterrows()):
            ts = row['t'].tz_convert('America/New_York')
            if last_date and ts.date() != last_date:
                # Calculate the x-position corresponding to this bar index.
                x = int((i / state.visible_bars) * w)
                painter.setPen(time_pen)
                painter.drawLine(x, 0, x, h - self.time_axis_height) # Vertical separator line
                painter.setPen(text_pen)
                painter.drawText(QRectF(x + 5, h - 25, 60, 20), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, ts.strftime('%d %b'))
            last_date = ts.date()

    def _draw_symbol_overlay(self, painter: QPainter, state: ChartState):
        """Draws the instrument symbol text in the top-left corner."""
        if not state.symbol_text: return
        painter.setFont(QFont('Segoe UI', 14, QFont.Weight.Bold))
        painter.setPen(QColor(220, 220, 220, 200))
        painter.drawText(QRectF(15, 5, 500, 30), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, state.symbol_text)

    def _draw_drag_selection(self, painter: QPainter, state: ChartState, w: int, h: int):
        """Placeholder for drawing a selection rectangle during a mouse drag."""
        pass # To be implemented

    def _draw_crosshair(self, painter: QPainter, state: ChartState, w: int, h: int, price_pane_top_y: int, price_pane_h: int, min_price: float, price_range: float):
        """Draws the vertical and horizontal lines of the crosshair."""
        if not state.mouse_pos: return
        
        painter.setPen(QPen(state.crosshair_color, state.crosshair_width, state.crosshair_style))
        
        # Draw vertical line snapped to the center of the hovered bar.
        if state.last_hovered_index != -1:
            x = int((state.last_hovered_index - state.start_bar + 0.5) * (w / state.visible_bars))
            painter.drawLine(x, 0, x, h)

        # Draw horizontal line at the mouse's y-position.
        y = state.mouse_pos.y()
        if y < h - self.time_axis_height: # Don't draw in time axis area
            painter.drawLine(0, y, w, y)
            
            # If the cursor is in the price pane, draw the price label.
            if y >= price_pane_top_y and y < price_pane_top_y + price_pane_h and price_range > 0:
                price = min_price + ((price_pane_top_y + price_pane_h - y) / price_pane_h) * price_range
                self._draw_highlighted_text(painter, QRectF(w - 75, y - 9, 70, 18), f"{price:.2f}", state.crosshair_color)