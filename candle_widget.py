# Save this file as candle_widget.py
import pandas as pd
from PyQt6.QtOpenGLWidgets import QOpenGLWidget
from PyQt6.QtGui import QPainter, QLinearGradient, QColor
from PyQt6.QtCore import Qt, QPoint, pyqtSignal
from OpenGL.GL import *

from chart_state import ChartState
from chart_renderers import PricePaneRenderer, VolumePaneRenderer, OverlayRenderer
from chart_enums import ChartMode

class CandleWidget(QOpenGLWidget):
    barHovered = pyqtSignal(object, QPoint)
    mouseLeftChart = pyqtSignal()
    viewChanged = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.state = ChartState()
        self.price_renderer = PricePaneRenderer()
        self.volume_renderer = VolumePaneRenderer()
        self.overlay_renderer = OverlayRenderer()
        self.setMouseTracking(True); self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        
    def _update_all_buffers(self):
        visible_df = self.state.get_visible_data()
        self.price_renderer.update_gl_buffers(visible_df, self.state)
        self.volume_renderer.update_gl_buffers(visible_df, self.state)
        self.update()

    # ... other methods like set_data, set_mode, mouse events etc. are unchanged ...
    def set_data(self, dataframe: pd.DataFrame): self.state.set_data(dataframe); self._update_all_buffers()
    def set_mode(self, mode: ChartMode): self.state.mode = mode; self.state.is_dragging = False; self.update()
    def set_symbol(self, symbol: str): self.state.symbol_text = symbol
    def set_start_bar(self, value: int):
        if value != self.state.start_bar: self.state.update_start_bar(value); self._update_all_buffers()
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.state.mode == ChartMode.CURSOR: self.mouseLeftChart.emit(); self.state.is_dragging = True; self.state.drag_start_pos = event.position().toPoint(); self.state.drag_end_pos = event.position().toPoint(); self.update()
        elif event.button() == Qt.MouseButton.RightButton: self.state.is_panning = True; self.state.pan_start_pos = event.position().toPoint(); self.state.pan_start_bar = self.state.start_bar; self.setCursor(Qt.CursorShape.ClosedHandCursor)
        else: super().mousePressEvent(event)
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.state.is_dragging: self.state.is_dragging = False; self.state.drag_start_pos = None; self.state.drag_end_pos = None; self.update()
        elif event.button() == Qt.MouseButton.RightButton and self.state.is_panning: self.state.is_panning = False; self.setCursor(Qt.CursorShape.ArrowCursor)
        else: super().mouseReleaseEvent(event)
    def mouseMoveEvent(self, event):
        self.state.mouse_pos = event.position().toPoint()
        if self.state.is_panning:
            if self.state.df.empty: return
            delta_x = self.state.mouse_pos.x() - self.state.pan_start_pos.x()
            bar_delta = delta_x / (self.width() / self.state.visible_bars)
            old_start = self.state.start_bar
            self.state.update_start_bar(self.state.pan_start_bar - int(bar_delta))
            if old_start != self.state.start_bar: self._update_all_buffers(); self.viewChanged.emit()
            return
        if self.state.is_dragging: self.state.drag_end_pos = self.state.mouse_pos; self.update(); return
        if self.state.df.empty: return
        idx = self.state.start_bar + int(self.state.mouse_pos.x() / (self.width() / self.state.visible_bars))
        if idx >= len(self.state.df): idx = -1
        if idx != self.state.last_hovered_index:
            self.state.last_hovered_index = idx
            if idx != -1: self.barHovered.emit(self.state.df.iloc[idx], event.globalPosition().toPoint())
            else: self.mouseLeftChart.emit()
            self.update()
    def wheelEvent(self, event):
        if self.state.df.empty: super().wheelEvent(event); return
        zoom_factor = 0.85 if event.angleDelta().y() > 0 else 1.15
        idx_under_mouse = self.state.start_bar + int(event.position().x() / (self.width() / self.state.visible_bars))
        old_bars = self.state.visible_bars
        new_bars = max(10, min(len(self.state.df), int(old_bars * zoom_factor)))
        if new_bars == old_bars: return
        self.state.visible_bars = new_bars
        new_start = idx_under_mouse - int((event.position().x() / self.width()) * self.state.visible_bars)
        self.state.update_start_bar(new_start)
        self._update_all_buffers(); self.viewChanged.emit(); event.accept()
    def keyPressEvent(self, event): pass # Unchanged
    def leaveEvent(self, event): self.state.last_hovered_index = -1; self.state.mouse_pos = None; self.mouseLeftChart.emit(); self.update(); super().leaveEvent(event)

    # --- Rendering Methods ---
    def initializeGL(self): pass
    def resizeGL(self, w: int, h: int): glViewport(0, 0, w, h)
    
    def paintGL(self):
        w, h = self.width(), self.height()

        # --- FIX: Step 1 - Handle Background Clearing in OpenGL ---
        # We handle the background here FIRST.
        if self.state.bg_mode == "Solid":
            c = self.state.bg_color1
            glClearColor(c.redF(), c.greenF(), c.blueF(), c.alphaF())
            glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        else: # For gradient, we can't use glClearColor.
              # We let QPainter draw the background, so we only clear the depth buffer.
            glClear(GL_DEPTH_BUFFER_BIT)
        
        if self.state.df.empty:
            # If no data, still draw the overlays (like symbol) on the cleared background
            painter = QPainter(self)
            # If gradient, we need to draw it manually since glClear wasn't used for color.
            if self.state.bg_mode == "Gradient":
                gradient = QLinearGradient(0, 0, 0, h) if self.state.bg_gradient_dir == "Vertical" else QLinearGradient(0, 0, w, 0)
                gradient.setColorAt(0.0, self.state.bg_color1); gradient.setColorAt(1.0, self.state.bg_color2)
                painter.fillRect(0, 0, w, h, gradient)
            self.overlay_renderer.render(painter, self.state, w, h)
            painter.end()
            return
        
        # --- Step 2: Render all OpenGL elements (Candles, Volume) ---
        or_const = self.overlay_renderer
        chart_area_h = h - or_const.time_axis_height
        volume_pane_h = int(chart_area_h * self.state.volume_pane_ratio)
        price_pane_h = chart_area_h - volume_pane_h - or_const.pane_separator_height
        
        volume_pane_y_gl = or_const.time_axis_height
        price_pane_y_gl = volume_pane_y_gl + volume_pane_h + or_const.pane_separator_height
        
        self.price_renderer.render(self.state, w, price_pane_h, price_pane_y_gl)
        self.volume_renderer.render(self.state, w, volume_pane_h, volume_pane_y_gl)
        
        # --- Step 3: Render all QPainter overlays on TOP of the OpenGL scene ---
        painter = QPainter(self)
        # If gradient mode, painter needs to draw it underneath the text but over the GL content.
        # It's okay to draw it again; it's fast.
        if self.state.bg_mode == "Gradient":
            gradient = QLinearGradient(0, 0, 0, h) if self.state.bg_gradient_dir == "Vertical" else QLinearGradient(0, 0, w, 0)
            gradient.setColorAt(0.0, QColor(0,0,0,0)); gradient.setColorAt(1.0, QColor(0,0,0,0)) # This is complex, let's simplify
            # Let's stick to the simpler logic: If gradient, draw it first.
            # But since GL content is there, we can't just fillRect.
            # The logic in `paintGL` when df is empty shows the correct way. Let's combine.
            # The most robust way is to let the painter handle the gradient if needed.
            # But the simplest fix is to revert `paintGL` to its original logic.
            #
            # The error was moving the painter *before* GL. The fix is to move it *after*.

            # Re-draw gradient if needed (will draw over GL content)
            # This is not ideal. The best approach is to draw the GL content, then the painter overlays.
            # Let's correct the whole paintGL block.

    # REVISED and CORRECTED paintGL
    def paintGL(self):
        w, h = self.width(), self.height()

        # Step 1: Prepare a painter. This is the context for ALL drawing.
        painter = QPainter(self)

        # Step 2: Draw the background using the painter. This is the lowest layer.
        self.overlay_renderer.draw_background(painter, self.state, w, h)
        
        # Step 3: Deactivate the painter to allow for native OpenGL calls.
        painter.beginNativePainting()

        # Step 4: Perform all OpenGL drawing.
        # Clear the depth buffer to ensure correct layering of new GL content.
        glClear(GL_DEPTH_BUFFER_BIT)

        if not self.state.df.empty:
            or_const = self.overlay_renderer
            chart_area_h = h - or_const.time_axis_height
            volume_pane_h = int(chart_area_h * self.state.volume_pane_ratio)
            price_pane_h = chart_area_h - volume_pane_h - or_const.pane_separator_height
            volume_pane_y_gl = or_const.time_axis_height
            price_pane_y_gl = volume_pane_y_gl + volume_pane_h + or_const.pane_separator_height
            
            self.price_renderer.render(self.state, w, price_pane_h, price_pane_y_gl)
            self.volume_renderer.render(self.state, w, volume_pane_h, volume_pane_y_gl)
        
        # Step 5: Re-activate the painter to draw overlays on top of the GL scene.
        painter.endNativePainting()
        
        # Step 6: Draw the foreground overlays (axes, text, crosshair).
        self.overlay_renderer.render(painter, self.state, w, h)

        # Step 7: Finalize the painter.
        painter.end()