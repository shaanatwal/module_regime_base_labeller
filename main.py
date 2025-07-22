# Save this as main.py
import sys
from pathlib import Path
from datetime import datetime 
from PyQt6.QtWidgets import (QApplication, QMainWindow, QFileDialog, QDialog, 
                             QWidget, QSizePolicy, QVBoxLayout, QScrollBar)
from PyQt6.QtGui import QAction, QIcon, QActionGroup
from PyQt6.QtCore import Qt, QSettings, QPoint
import re 

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

        self.chart_mode = ChartMode.CURSOR

        self.welcome_screen = WelcomeWidget()

        self.chart_widget = CandleWidget()
        self.scrollbar = QScrollBar(Qt.Orientation.Horizontal)
        
        self.chart_container = QWidget()
        chart_layout = QVBoxLayout(self.chart_container)
        chart_layout.setContentsMargins(0, 0, 0, 0)
        chart_layout.setSpacing(0)
        chart_layout.addWidget(self.chart_widget)
        chart_layout.addWidget(self.scrollbar)
        
        self.setCentralWidget(self.welcome_screen)

        self.info_widget = InfoWidget(self)

        self.chart_widget.barHovered.connect(self.handle_bar_hover)
        self.chart_widget.mouseLeftChart.connect(self.info_widget.hide)
        self.chart_widget.viewChanged.connect(self.on_chart_view_changed)
        self.scrollbar.valueChanged.connect(self.on_scrollbar_moved)

        self.setup_toolbar()
        
        self.update_action_states(is_data_loaded=False)

    def setup_toolbar(self):
        toolbar = self.addToolBar('Main Toolbar')
        toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        
        self.load_action = QAction(QIcon('icons/load_data.png'), 'Load Data', self)
        self.load_action.setToolTip("Load Parquet Data File")
        self.load_action.triggered.connect(self.open_file)
        toolbar.addAction(self.load_action)
        
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
        
        self.cursor_mode_action = QAction(QIcon('icons/cursor.png'), 'Cursor', self)
        self.cursor_mode_action.setCheckable(True); self.cursor_mode_action.setChecked(True)
        self.cursor_mode_action.setData(ChartMode.CURSOR)
        self.cursor_mode_action.setToolTip("Activate Cursor Mode")
        toolbar.addAction(self.cursor_mode_action); mode_group.addAction(self.cursor_mode_action)
        
        self.marker_mode_action = QAction(QIcon('icons/marker.png'), 'Marker', self)
        self.marker_mode_action.setCheckable(True)
        self.marker_mode_action.setData(ChartMode.MARKER)
        self.marker_mode_action.setToolTip("Activate Marker Mode")
        toolbar.addAction(self.marker_mode_action); mode_group.addAction(self.marker_mode_action)
        
        mode_group.triggered.connect(self.on_mode_change)
        toolbar.addSeparator()
        
        self.prefs_action = QAction(QIcon.fromTheme('preferences-system'), 'Preferences', self)
        self.prefs_action.setToolTip("Preferences")
        self.prefs_action.triggered.connect(self.open_preferences_dialog)
        toolbar.addAction(self.prefs_action)

    def on_scrollbar_moved(self, value):
        self.chart_widget.set_start_bar(value)

    def on_chart_view_changed(self):
        self.scrollbar.blockSignals(True)
        
        # --- MODIFIED: Access data via the state object ---
        total_bars = len(self.chart_widget.state.df)
        visible_bars = self.chart_widget.state.visible_bars
        start_bar = self.chart_widget.state.start_bar
        
        max_scroll_val = max(0, total_bars - visible_bars)
        
        self.scrollbar.setRange(0, max_scroll_val)
        self.scrollbar.setPageStep(visible_bars)
        self.scrollbar.setValue(start_bar)
        
        self.scrollbar.blockSignals(False)


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

    def format_timeframe(self, tf_str: str) -> str:
        match = re.match(r"(\d+)([a-zA-Z]+)", tf_str)
        if not match: return tf_str 

        num_str, unit_str = match.groups()
        num = int(num_str)
        unit_map = {'sec': 'Second', 'min': 'Minute', 'h': 'Hour', 'd': 'Day', 'w': 'Week', 'm': 'Month'}
        
        unit_full = next((v for k, v in unit_map.items() if k in unit_str.lower()), unit_str.capitalize())
        
        if num > 1: unit_full += "s"
            
        return f"{num} {unit_full}"

    def open_file(self):
        last_dir = self.settings.value("last_data_dir", str(Path.home()))
        file_path, _ = QFileDialog.getOpenFileName(self, "Select a Parquet Data File", last_dir, "Parquet Files (*.parquet);;All Files (*)", options=QFileDialog.Option.DontUseNativeDialog)
        if file_path:
            new_dir = str(Path(file_path).parent); self.settings.setValue("last_data_dir", new_dir)
            ohlc_data = load_parquet_data(file_path)
            if not ohlc_data.empty:
                display_text = ""
                try:
                    stem = Path(file_path).stem
                    parts = stem.split('_')
                    if len(parts) >= 5:
                        ticker = parts[0].upper()
                        timeframe = self.format_timeframe(parts[1])
                        year = parts[3]
                        month_num = parts[4]
                        month_name = datetime.strptime(month_num, '%m').strftime('%B')
                        display_text = f"{ticker} ({timeframe})  -  {month_name} {year}"
                    else: 
                        display_text = stem.split('_')[0].upper()
                except Exception as e:
                    print(f"Could not parse filename '{Path(file_path).name}', using fallback. Error: {e}")
                    display_text = Path(file_path).stem.split('_')[0].upper()

                self.chart_widget.set_symbol(display_text)
                self.chart_widget.set_data(ohlc_data)
                self.setCentralWidget(self.chart_container)
                self.setWindowTitle(f'Candlestick Labelling Tool - {file_path}')
                self.update_action_states(is_data_loaded=True)
                self.on_chart_view_changed()
            else:
                self.setCentralWidget(self.welcome_screen)
                self.setWindowTitle('Candlestick Labelling Tool')
                self.update_action_states(is_data_loaded=False)


    def open_preferences_dialog(self):
        dialog = PreferencesDialog(
            # --- MODIFIED: Access colors via the state object ---
            initial_bg_color=self.chart_widget.state.bg_color,
            initial_up_color=self.chart_widget.state.up_color,
            initial_down_color=self.chart_widget.state.down_color,
            parent=self
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            bg_color, up_color, down_color = dialog.get_selected_colors()
            # --- MODIFIED: Set colors via the state object ---
            self.chart_widget.state.bg_color = bg_color
            self.chart_widget.state.up_color = up_color
            self.chart_widget.state.down_color = down_color
            self.chart_widget.update()

    def closeEvent(self, event):
        self.settings.setValue("geometry", self.saveGeometry()); super().closeEvent(event)

def main():
    app = QApplication(sys.argv); app.setOrganizationName("CandleCorp"); app.setApplicationName("CandlestickLabellingTool")
    try:
        with open('main.qss', 'r') as f: app.setStyleSheet(f.read())
    except FileNotFoundError: print("Stylesheet 'main.qss' not found. Using default styles.")
    window = MainWindow()
    window.setWindowIcon(QIcon('icons/appicon.png'))
    window.show()
    sys.exit(app.exec())

if __name__ == '__main__': main()