# Save this file as candle_widget.py
import pandas as pd
from PyQt6.QtOpenGLWidgets import QOpenGLWidget
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QPainter
from PyQt6.QtCore import Qt, QPoint, pyqtSignal
from OpenGL.GL import *

# Refactored components
from chart_state import ChartState
from chart_renderers import PricePaneRenderer, VolumePaneRenderer, OverlayRenderer
from chart_enums import ChartMode

class CandleWidget(QOpenGLWidget):
    # Signals remain the same
    barHovered = pyqtSignal(object, QPoint)
    mouseLeftChart = pyqtSignal()
    viewChanged = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        
        # The widget now owns the state and the renderers
        self.state = ChartState()
        self.price_renderer = PricePaneRenderer()
        self.volume_renderer = VolumePaneRenderer()
        self.overlay_renderer = OverlayRenderer()

        # UI settings
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        
    def set_data(self, dataframe: pd.DataFrame):
        self.state.set_data(dataframe)
        self.update()
        
    def set_mode(self, mode: ChartMode):
        self.state.mode = mode
        self.state.is_dragging = False
        self.update()

    def set_symbol(self, symbol: str):
        self.state.symbol_text = symbol

    def set_start_bar(self, value: int):
        if value != self.state.start_bar:
            self.state.update_start_bar(value)
            self.update()

    # --- Event Handlers: Translate user input into state changes ---

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.state.mode == ChartMode.CURSOR:
            self.mouseLeftChart.emit()
            self.state.is_dragging = True
            self.state.drag_start_pos = event.position().toPoint()
            self.state.drag_end_pos = event.position().toPoint()
            self.update()
        elif event.button() == Qt.MouseButton.RightButton:
            self.state.is_panning = True
            self.state.pan_start_pos = event.position().toPoint()
            self.state.pan_start_bar = self.state.start_bar
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
        else:
            super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
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
        self.state.mouse_pos = event.position().toPoint()
        
        if self.state.is_panning:
            if self.state.df.empty: return
            delta_x = self.state.mouse_pos.x() - self.state.pan_start_pos.x()
            bar_width = self.width() / self.state.visible_bars
            bar_delta = delta_x / bar_width
            
            new_start_bar = self.state.pan_start_bar - int(bar_delta)
            self.state.update_start_bar(new_start_bar)
            
            self.update()
            self.viewChanged.emit()
            return

        if self.state.is_dragging:
            self.state.drag_end_pos = self.state.mouse_pos
            self.update()
            return
        
        if self.state.df.empty: return
        
        bar_width = self.width() / self.state.visible_bars
        hover_index_in_view = int(self.state.mouse_pos.x() / bar_width)
        actual_index = self.state.start_bar + hover_index_in_view
        
        if actual_index >= len(self.state.df):
            actual_index = -1
            
        if actual_index != self.state.last_hovered_index:
            self.state.last_hovered_index = actual_index
            if actual_index != -1:
                self.barHovered.emit(self.state.df.iloc[actual_index], event.globalPosition().toPoint())
            else:
                self.mouseLeftChart.emit()
        self.update()

    def wheelEvent(self, event):
        if self.state.df.empty:
            super().wheelEvent(event)
            return

        delta = event.angleDelta().y()
        zoom_factor = 0.85 if delta > 0 else 1.15
        
        mouse_x = event.position().x()
        bar_width = self.width() / self.state.visible_bars
        index_under_mouse = self.state.start_bar + int(mouse_x / bar_width)

        old_visible_bars = self.state.visible_bars
        new_visible_bars = int(old_visible_bars * zoom_factor)
        new_visible_bars = max(10, min(len(self.state.df), new_visible_bars))

        if new_visible_bars == old_visible_bars: return
        self.state.visible_bars = new_visible_bars

        mouse_x_ratio = mouse_x / self.width()
        new_start_bar_offset = int(self.state.visible_bars * mouse_x_ratio)
        new_start_bar = index_under_mouse - new_start_bar_offset
        self.state.update_start_bar(new_start_bar)

        self.update()
        self.viewChanged.emit()
        event.accept()

    def keyPressEvent(self, event):
        if self.state.df.empty:
            super().keyPressEvent(event)
            return
        
        original_start_bar = self.state.start_bar
        original_visible_bars = self.state.visible_bars

        key_actions = {
            Qt.Key.Key_Right: lambda: self.state.update_start_bar(self.state.start_bar + self.state.scroll_speed),
            Qt.Key.Key_Left: lambda: self.state.update_start_bar(self.state.start_bar - self.state.scroll_speed),
        }
        
        action = key_actions.get(event.key())
        if action:
            action()
        elif event.key() in (Qt.Key.Key_Up, Qt.Key.Key_Down):
            center_bar_index = self.state.start_bar + self.state.visible_bars // 2
            zoom_factor = 0.8 if event.key() == Qt.Key.Key_Up else 1.2
            new_visible_bars = max(10, min(len(self.state.df), int(self.state.visible_bars * zoom_factor)))
            self.state.visible_bars = new_visible_bars
            
            new_start_bar = center_bar_index - self.state.visible_bars // 2
            self.state.update_start_bar(new_start_bar)
        elif event.key() in (Qt.Key.Key_Plus, Qt.Key.Key_Equal):
            self.state.zoom_factor *= 0.9
        elif event.key() == Qt.Key.Key_Minus:
            self.state.zoom_factor *= 1.1
        else:
            super().keyPressEvent(event)
            return
            
        if original_start_bar != self.state.start_bar or original_visible_bars != self.state.visible_bars:
            self.update()
            self.viewChanged.emit()

    def leaveEvent(self, event):
        self.state.last_hovered_index = -1
        self.state.mouse_pos = None
        self.mouseLeftChart.emit()
        self.update()
        super().leaveEvent(event)

    def initializeGL(self): pass
    def resizeGL(self, w: int, h: int): pass
    
    # --- Rendering Orchestration ---
    
    def paintGL(self):
        # 1. Clear background
        c = self.state.bg_color
        glClearColor(c.redF(), c.greenF(), c.blueF(), 1.0)
        glClear(GL_COLOR_BUFFER_BIT)
        
        if self.state.df.empty: return
        
        # 2. Ensure state is valid
        self.state.update_start_bar(self.state.start_bar)
        
        # 3. Calculate pane geometry (for both GL and Painter)
        w, h = self.width(), self.height()
        or_constants = self.overlay_renderer
        chart_area_h = h - or_constants.time_axis_height
        volume_pane_h = int(chart_area_h * self.state.volume_pane_ratio)
        price_pane_h = chart_area_h - volume_pane_h - or_constants.pane_separator_height
        
        # Y-offsets are from the bottom for OpenGL
        volume_pane_y = or_constants.time_axis_height
        price_pane_y = volume_pane_y + volume_pane_h + or_constants.pane_separator_height
        
        # 4. Delegate to Renderers
        self.price_renderer.render(self.state, w, price_pane_h, price_pane_y)
        self.volume_renderer.render(self.state, w, volume_pane_h, volume_pane_y)
        
        # 5. Paint overlays using QPainter
        painter = QPainter(self)
        self.overlay_renderer.render(painter, self.state, w, h)
        painter.end()