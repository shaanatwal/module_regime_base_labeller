# Save this as main.py
import sys
from pathlib import Path
from PyQt6.QtWidgets import QApplication, QMainWindow, QFileDialog, QDialog, QWidget, QSizePolicy
from PyQt6.QtGui import QAction, QIcon, QActionGroup
from PyQt6.QtCore import Qt, QSettings, QPoint

# Import our custom modules
from data_loader import load_parquet_data
from candle_widget import CandleWidget
from preferences_dialog import PreferencesDialog
from welcome_widget import WelcomeWidget
from info_widget import InfoWidget
from chart_enums import ChartMode

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Candlestick Labelling Tool')
        self.settings = QSettings()
        geom = self.settings.value("geometry")
        if geom: self.restoreGeometry(geom)
        else: self.setGeometry(100, 100, 1200, 800)

        self.chart_mode = ChartMode.CURSOR # Default mode

        self.welcome_screen = WelcomeWidget()
        self.chart_widget = CandleWidget()
        self.info_widget = InfoWidget(self)
        self.setCentralWidget(self.welcome_screen)

        self.chart_widget.barHovered.connect(self.handle_bar_hover)
        self.chart_widget.mouseLeftChart.connect(self.info_widget.hide)

        self.setup_toolbar()
        
        self.update_action_states(is_data_loaded=False)

    def setup_toolbar(self):
        toolbar = self.addToolBar('Main Toolbar')
        toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly) # Keep icons only
        
        # --- CHANGE 1: Use custom 'load_data.png' icon ---
        self.load_action = QAction(QIcon('icons/load_data.png'), 'Load Data', self)
        self.load_action.setToolTip("Load Parquet Data File")
        self.load_action.triggered.connect(self.open_file)
        toolbar.addAction(self.load_action)
        
        # --- CHANGE 2: Use custom 'save_labels.png' icon ---
        self.save_action = QAction(QIcon('icons/save_labels.png'), 'Save Labels', self)
        self.save_action.setToolTip("Save Labels")
        toolbar.addAction(self.save_action)
        
        toolbar.addSeparator()
        
        self.prepopulate_action = QAction(QIcon.fromTheme('media-playback-start'), 'Pre-populate', self)
        self.prepopulate_action.setToolTip("Pre-populate")
        toolbar.addAction(self.prepopulate_action)
        
        self.train_action = QAction(QIcon.fromTheme('system-run'), 'Train Model', self)
        self.train_action.setToolTip("Train Model")
        toolbar.addAction(self.train_action)
        
        spacer = QWidget(); spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred); toolbar.addWidget(spacer)
        
        mode_group = QActionGroup(self)
        mode_group.setExclusive(True)
        
        # --- CHANGE 3: Use custom 'cursor.png' icon ---
        self.cursor_mode_action = QAction(QIcon('icons/cursor.png'), 'Cursor', self)
        self.cursor_mode_action.setCheckable(True); self.cursor_mode_action.setChecked(True)
        self.cursor_mode_action.setData(ChartMode.CURSOR)
        self.cursor_mode_action.setToolTip("Activate Cursor Mode (for crosshair and region analysis)")
        toolbar.addAction(self.cursor_mode_action); mode_group.addAction(self.cursor_mode_action)
        
        # --- CHANGE 4: Use custom 'marker.png' icon ---
        self.marker_mode_action = QAction(QIcon('icons/marker.png'), 'Marker', self)
        self.marker_mode_action.setCheckable(True)
        self.marker_mode_action.setData(ChartMode.MARKER)
        self.marker_mode_action.setToolTip("Activate Marker Mode (for labeling patterns)")
        toolbar.addAction(self.marker_mode_action); mode_group.addAction(self.marker_mode_action)
        
        mode_group.triggered.connect(self.on_mode_change)
        toolbar.addSeparator()
        
        self.prefs_action = QAction(QIcon.fromTheme('preferences-system'), 'Preferences', self)
        self.prefs_action.setToolTip("Preferences")
        self.prefs_action.triggered.connect(self.open_preferences_dialog)
        toolbar.addAction(self.prefs_action)

    def on_mode_change(self, action: QAction):
        new_mode = action.data()
        self.chart_mode = new_mode
        self.chart_widget.set_mode(new_mode)
        print(f"Mode changed to: {new_mode.name}")

    def handle_bar_hover(self, data_row, mouse_pos: QPoint):
        if self.chart_mode == ChartMode.CURSOR:
            self.info_widget.update_and_show(data_row, mouse_pos + QPoint(15, 15))
        else:
            self.info_widget.hide()

    def update_action_states(self, is_data_loaded: bool):
        self.save_action.setEnabled(is_data_loaded); self.prepopulate_action.setEnabled(is_data_loaded); self.train_action.setEnabled(is_data_loaded)

    def open_file(self):
        last_dir = self.settings.value("last_data_dir", str(Path.home()))
        file_path, _ = QFileDialog.getOpenFileName(self,"Select a Parquet Data File",last_dir,"Parquet Files (*.parquet);;All Files (*)",options=QFileDialog.Option.DontUseNativeDialog)
        if file_path:
            new_dir = str(Path(file_path).parent); self.settings.setValue("last_data_dir", new_dir)
            ohlc_data = load_parquet_data(file_path)
            if not ohlc_data.empty:
                self.chart_widget.set_data(ohlc_data); self.setCentralWidget(self.chart_widget)
                self.setWindowTitle(f'Candlestick Labelling Tool - {file_path}'); self.update_action_states(is_data_loaded=True)
            else:
                self.setCentralWidget(self.welcome_screen); self.setWindowTitle('Candlestick Labelling Tool'); self.update_action_states(is_data_loaded=False)

    def open_preferences_dialog(self):
        # NOTE: This function refers to methods that don't exist in CandleWidget yet.
        # We will add get_background_color, etc. in a future step.
        # For now, we can pass default QColor values.
        dialog = PreferencesDialog(
            initial_bg_color=self.chart_widget.bg_color,
            initial_up_color=self.chart_widget.up_color,
            initial_down_color=self.chart_widget.down_color,
            parent=self
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            bg_color, up_color, down_color = dialog.get_selected_colors()
            # NOTE: Similarly, set_background_color etc. will be added later.
            self.chart_widget.bg_color = bg_color
            self.chart_widget.up_color = up_color
            self.chart_widget.down_color = down_color
            self.chart_widget.update() # Redraw the chart with new colors

    def closeEvent(self, event):
        self.settings.setValue("geometry", self.saveGeometry()); super().closeEvent(event)

def main():
    app = QApplication(sys.argv); app.setOrganizationName("CandleCorp"); app.setApplicationName("CandlestickLabellingTool")
    try:
        with open('main.qss', 'r') as f: app.setStyleSheet(f.read())
    except FileNotFoundError: print("Stylesheet 'main.qss' not found. Using default styles.")
    window = MainWindow()
    # --- CHANGE 5: Use 'appicon.png' as the main application icon ---
    window.setWindowIcon(QIcon('icons/appicon.png'))
    window.show()
    sys.exit(app.exec())

if __name__ == '__main__': main()