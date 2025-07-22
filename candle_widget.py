import pandas as pd
from PyQt6.QtOpenGLWidgets import QOpenGLWidget
from PyQt6.QtGui import QPainter  # <-- FIX: Restored the missing import for QPainter.
from PyQt6.QtCore import Qt, QPoint, pyqtSignal
from OpenGL.GL import *

from chart_state import ChartState
from chart_renderers import PricePaneRenderer, VolumePaneRenderer, OverlayRenderer
from chart_enums import ChartMode

class CandleWidget(QOpenGLWidget):
    """
    The primary widget for displaying the candlestick chart.

    This widget uses OpenGL for high-performance rendering of candles and volume
    bars, and QPainter for overlaying UI elements like axes and crosshairs.
    It manages user interactions such as zooming, panning, and hovering.

    Signals:
        barHovered: Emitted when the mouse hovers over a new bar, providing
                    the bar's data and the global mouse position.
        mouseLeftChart: Emitted when the mouse cursor leaves the widget area.
        viewChanged: Emitted whenever the visible range of bars changes due
                     to panning or zooming.
    """
    barHovered = pyqtSignal(object, QPoint)
    mouseLeftChart = pyqtSignal()
    viewChanged = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.state = ChartState()
        self.price_renderer = PricePaneRenderer()
        self.volume_renderer = VolumePaneRenderer()
        self.overlay_renderer = OverlayRenderer()
        
        # Enable mouse tracking to receive mouseMoveEvents even when no button is pressed.
        self.setMouseTracking(True)
        # Set a strong focus policy to receive keyboard events.
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        
    def _update_all_buffers(self):
        """
        Forces a recalculation and upload of all OpenGL vertex data.
        
        This should be called whenever the visible data changes (pan/zoom) or
        when style settings (like colors) that affect the GPU data are modified.
        """
        visible_df = self.state.get_visible_data()
        self.price_renderer.update_gl_buffers(visible_df, self.state)
        self.volume_renderer.update_gl_buffers(visible_df, self.state)
        self.update() # Schedules a repaint (paintGL call).

    def set_data(self, dataframe: pd.DataFrame):
        """Loads new candlestick data into the chart and resets the view."""
        self.state.set_data(dataframe)
        self._update_all_buffers()

    def set_mode(self, mode: ChartMode):
        """Sets the current interaction mode for the chart (e.g., Cursor or Marker)."""
        self.state.mode = mode
        self.state.is_dragging = False
        self.update()

    def set_symbol(self, symbol: str):
        """Sets the symbol text to be displayed in the top-left corner."""
        self.state.symbol_text = symbol

    def set_start_bar(self, value: int):
        """Sets the starting bar index for the visible range (used by scrollbar)."""
        if value != self.state.start_bar:
            self.state.update_start_bar(value)
            self._update_all_buffers()

    # --- User Interaction Event Handlers ---

    def mousePressEvent(self, event):
        """Handles the start of a mouse drag or pan operation."""
        # Left-click drag for selection (not implemented yet).
        if event.button() == Qt.MouseButton.LeftButton and self.state.mode == ChartMode.CURSOR:
            self.mouseLeftChart.emit() # Hide info widget
            self.state.is_dragging = True
            self.state.drag_start_pos = event.position().toPoint()
            self.state.drag_end_pos = event.position().toPoint()
            self.update()
        # Right-click drag to pan the chart.
        elif event.button() == Qt.MouseButton.RightButton:
            self.state.is_panning = True
            self.state.pan_start_pos = event.position().toPoint()
            self.state.pan_start_bar = self.state.start_bar
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
        else:
            super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        """Handles the end of a mouse drag or pan operation."""
        if event.button() == Qt.MouseButton.LeftButton and self.state.is_dragging:
            self.state.is_dragging = False
            self.state.drag_start_pos = None
            self.state.drag_end_pos = None
            self.update()
        elif event.button() == Qt.MouseButton.RightButton and self.state.is_panning:
            self.state.is_panning = False
            self.setCursor(Qt.CursorShape.ArrowCursor)
        else:
            super().mouseReleaseEvent(event)

    def mouseMoveEvent(self, event):
        """Handles mouse movement for panning, dragging, and hovering."""
        self.state.mouse_pos = event.position().toPoint()

        # Handle panning if active.
        if self.state.is_panning:
            if self.state.df.empty: return
            delta_x = self.state.mouse_pos.x() - self.state.pan_start_pos.x()
            # Convert pixel delta to bar index delta.
            bar_delta = delta_x / (self.width() / self.state.visible_bars)
            new_start_bar = self.state.pan_start_bar - int(bar_delta)
            
            if self.state.start_bar != new_start_bar:
                self.state.update_start_bar(new_start_bar)
                self._update_all_buffers()
                self.viewChanged.emit() # Notify scrollbar
            return
            
        # Handle dragging if active.
        if self.state.is_dragging:
            self.state.drag_end_pos = self.state.mouse_pos
            self.update()
            return

        # Handle hovering.
        if self.state.df.empty: return
        # Calculate which bar index is under the mouse cursor.
        bar_width_px = self.width() / self.state.visible_bars
        idx_offset = int(self.state.mouse_pos.x() / bar_width_px)
        idx = self.state.start_bar + idx_offset
        
        if idx >= len(self.state.df): idx = -1 # Cursor is off the right edge of data
        
        # If the hovered bar has changed, emit a signal.
        if idx != self.state.last_hovered_index:
            self.state.last_hovered_index = idx
            if idx != -1:
                self.barHovered.emit(self.state.df.iloc[idx], event.globalPosition().toPoint())
            else:
                self.mouseLeftChart.emit()
            self.update()

    def wheelEvent(self, event):
        """Handles mouse wheel events for zooming."""
        if self.state.df.empty:
            super().wheelEvent(event); return

        # Determine zoom direction and factor.
        zoom_factor = 0.85 if event.angleDelta().y() > 0 else 1.15
        
        # --- Zoom logic: Zoom towards the mouse cursor ---
        # 1. Find which bar index is directly under the mouse.
        bar_width_px = self.width() / self.state.visible_bars
        idx_under_mouse = self.state.start_bar + int(event.position().x() / bar_width_px)
        
        # 2. Calculate the new number of visible bars.
        old_bars = self.state.visible_bars
        new_bars = max(10, min(len(self.state.df), int(old_bars * zoom_factor)))
        if new_bars == old_bars: return # No change in zoom level
        
        self.state.visible_bars = new_bars
        
        # 3. Calculate the new start_bar to keep the bar under the mouse at the same position.
        #    The mouse's proportional position on the screen should correspond to the same
        #    proportional position in the new set of visible bars.
        mouse_x_ratio = event.position().x() / self.width()
        new_start = idx_under_mouse - int(mouse_x_ratio * self.state.visible_bars)
        
        self.state.update_start_bar(new_start)
        self._update_all_buffers()
        self.viewChanged.emit() # Notify scrollbar of the change
        event.accept()

    def leaveEvent(self, event):
        """Hides crosshair and info widget when the mouse leaves the chart."""
        self.state.last_hovered_index = -1
        self.state.mouse_pos = None
        self.mouseLeftChart.emit()
        self.update()
        super().leaveEvent(event)

    # --- Rendering Methods ---

    def initializeGL(self):
        """Called once when the OpenGL context is first created."""
        pass # No global GL state needs to be set up here.
    
    def resizeGL(self, w: int, h: int):
        """Called whenever the widget is resized."""
        # The viewport is set per-pane in the renderers, so a global
        # viewport set here is not necessary.
        pass

    def paintGL(self):
        """
        The main rendering method, called whenever the widget needs to be redrawn.
        
        This method orchestrates the drawing process by layering different components:
        1. The background (solid/gradient) is drawn with QPainter.
        2. High-performance OpenGL is used for the data-heavy candles and volume bars.
        3. QPainter is used again to draw all foreground UI overlays (axes, text, etc.).
        This hybrid approach provides both performance and high-quality UI rendering.
        """
        w, h = self.width(), self.height()

        # Step 1: Initialize a QPainter for the entire widget. This will be our
        # context for all 2D drawing.
        painter = QPainter(self)

        # Step 2: Draw the background first. This clears the entire widget area.
        self.overlay_renderer.draw_background(painter, self.state, w, h)
        
        # Step 3: Switch from QPainter's engine to direct OpenGL calls.
        # This is a critical step for mixing the two rendering systems.
        painter.beginNativePainting()

        # Step 4: Perform all OpenGL drawing.
        # We must clear the depth buffer to ensure our new GL drawings appear
        # correctly on top of the background and are not obscured by old data.
        glClear(GL_DEPTH_BUFFER_BIT)

        if not self.state.df.empty:
            # Calculate pane dimensions for the renderers.
            or_consts = self.overlay_renderer
            chart_area_h = h - or_consts.time_axis_height
            volume_pane_h = int(chart_area_h * self.state.volume_pane_ratio)
            price_pane_h = chart_area_h - volume_pane_h - or_consts.pane_separator_height
            
            # Y-offsets are calculated from the bottom of the widget for OpenGL.
            volume_pane_y_gl = or_consts.time_axis_height
            price_pane_y_gl = volume_pane_y_gl + volume_pane_h + or_consts.pane_separator_height
            
            # Instruct the renderers to draw their respective panes.
            self.price_renderer.render(self.state, w, price_pane_h, price_pane_y_gl)
            self.volume_renderer.render(self.state, w, volume_pane_h, volume_pane_y_gl)
        
        # Step 5: Switch back to the QPainter engine. Now we can draw on top
        # of the scene we just rendered with OpenGL.
        painter.endNativePainting()
        
        # Step 6: Draw all foreground UI elements (axes, grid lines, text, crosshair).
        self.overlay_renderer.render(painter, self.state, w, h)

        # Step 7: Finalize the painting operation.
        painter.end()