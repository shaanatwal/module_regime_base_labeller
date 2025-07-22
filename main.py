import sys
from pathlib import Path
from datetime import datetime
from PyQt6.QtWidgets import (QApplication, QMainWindow, QFileDialog, QWidget, 
                             QSizePolicy, QVBoxLayout, QScrollBar, QMessageBox, 
                             QStatusBar)
from PyQt6.QtGui import QAction, QIcon, QActionGroup
from PyQt6.QtCore import Qt, QSettings, QPoint, QObject, QThread, pyqtSignal
import pandas as pd
import re

# Application-specific modules
from data_loader import load_parquet_data
from candle_widget import CandleWidget
from preferences_dialog import PreferencesDialog
from welcome_widget import WelcomeWidget
from info_widget import InfoWidget
from chart_enums import ChartMode

class DataLoaderWorker(QObject):
    """
    Performs data loading in a separate thread to prevent freezing the UI.

    This worker is moved to a QThread to handle potentially slow file I/O
    and data processing without blocking the main application event loop.
    It communicates results back to the main thread via signals.

    Signals:
        finished: Emitted on successful data load, carrying the filepath and DataFrame.
        error: Emitted when an error occurs during loading.
    """
    finished = pyqtSignal(str, pd.DataFrame)
    error = pyqtSignal(str)

    def run(self, file_path: str):
        """Loads and processes data from the given file path."""
        try:
            df = load_parquet_data(file_path)
            if df.empty:
                self.error.emit(f"No data was loaded from {file_path}. The file might be empty or contain invalid data.")
            else:
                self.finished.emit(file_path, df)
        except Exception as e:
            # Catch any unexpected errors during the loading process.
            self.error.emit(f"An unexpected error occurred while loading the data:\n{e}")

class MainWindow(QMainWindow):
    """
    The main application window.

    This class sets up the main UI, including the toolbar, chart widget,
    and status bar. It manages application state, handles user actions,
    and orchestrates the interactions between different components like
    the chart, data loader, and preferences dialog.
    """
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Candlestick Labelling Tool')
        
        # Use QSettings to remember window size and position between sessions.
        self.settings = QSettings()
        geom = self.settings.value("geometry")
        if geom: self.restoreGeometry(geom)
        else: self.setGeometry(100, 100, 1200, 800)

        # A reference to the preferences dialog to ensure it's not garbage-collected.
        self.prefs_dialog = None

        # --- Central Widget Management ---
        # The app starts with a welcome screen.
        self.welcome_screen = WelcomeWidget()
        # The chart widget and its scrollbar are held in a container.
        self.chart_widget = CandleWidget()
        self.scrollbar = QScrollBar(Qt.Orientation.Horizontal)
        self.chart_container = QWidget()
        chart_layout = QVBoxLayout(self.chart_container)
        chart_layout.setContentsMargins(0, 0, 0, 0)
        chart_layout.setSpacing(0)
        chart_layout.addWidget(self.chart_widget)
        chart_layout.addWidget(self.scrollbar)
        
        # Initially, show the welcome screen. It will be replaced by the chart
        # container once data is loaded.
        self.setCentralWidget(self.welcome_screen)
        
        # --- UI Components ---
        self.setStatusBar(QStatusBar(self))
        self.info_widget = InfoWidget(self) # Floating OHLCV info panel
        self.setup_toolbar()

        # --- Signal/Slot Connections ---
        self.chart_widget.barHovered.connect(self.handle_bar_hover)
        self.chart_widget.mouseLeftChart.connect(self.info_widget.hide)
        self.chart_widget.viewChanged.connect(self.on_chart_view_changed)
        self.scrollbar.valueChanged.connect(self.on_scrollbar_moved)
        
        # --- State Management ---
        # Disable actions that require data to be loaded.
        self.update_action_states(is_data_loaded=False)
        self.thread = None
        self.worker = None

    def setup_toolbar(self):
        """Creates and configures the main application toolbar."""
        toolbar = self.addToolBar('Main Toolbar')
        toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        
        # --- File Actions ---
        self.load_action = QAction(QIcon('icons/load_data.png'), 'Load Data', self)
        self.load_action.setToolTip("Load Parquet Data File (*.parquet)")
        self.load_action.triggered.connect(self.open_file)
        toolbar.addAction(self.load_action)
        
        self.save_action = QAction(QIcon('icons/save_labels.png'), 'Save Labels', self)
        self.save_action.setToolTip("Save Labels (Not Implemented)")
        toolbar.addAction(self.save_action)
        
        toolbar.addSeparator()

        # --- Functionality Actions ---
        self.prepopulate_action = QAction(QIcon.fromTheme('media-playback-start'), 'Pre-populate', self)
        self.prepopulate_action.setToolTip("Pre-populate (Not Implemented)")
        toolbar.addAction(self.prepopulate_action)
        
        self.train_action = QAction(QIcon.fromTheme('system-run'), 'Train Model', self)
        self.train_action.setToolTip("Train Model (Not Implemented)")
        toolbar.addAction(self.train_action)
        
        # This spacer pushes subsequent items to the right side of the toolbar.
        spacer = QWidget(); spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred); toolbar.addWidget(spacer)
        
        # --- Mode Switching Actions ---
        mode_group = QActionGroup(self)
        mode_group.setExclusive(True) # Ensures only one mode can be active.
        
        self.cursor_mode_action = QAction(QIcon('icons/cursor.png'), 'Cursor', self)
        self.cursor_mode_action.setCheckable(True); self.cursor_mode_action.setChecked(True)
        self.cursor_mode_action.setData(ChartMode.CURSOR)
        self.cursor_mode_action.setToolTip("Activate Cursor Mode (for inspecting candles)")
        toolbar.addAction(self.cursor_mode_action); mode_group.addAction(self.cursor_mode_action)
        
        self.marker_mode_action = QAction(QIcon('icons/marker.png'), 'Marker', self)
        self.marker_mode_action.setCheckable(True)
        self.marker_mode_action.setData(ChartMode.MARKER)
        self.marker_mode_action.setToolTip("Activate Marker Mode (for labelling)")
        toolbar.addAction(self.marker_mode_action); mode_group.addAction(self.marker_mode_action)
        
        mode_group.triggered.connect(self.on_mode_change)
        toolbar.addSeparator()
        
        # --- Preferences Action ---
        self.prefs_action = QAction(QIcon.fromTheme('preferences-system'), 'Preferences', self)
        self.prefs_action.setToolTip("Open Appearance Preferences")
        self.prefs_action.triggered.connect(self.open_preferences_dialog)
        toolbar.addAction(self.prefs_action)

    def on_scrollbar_moved(self, value: int):
        """Slot to handle scrollbar movements and update the chart's view."""
        self.chart_widget.set_start_bar(value)

    def on_chart_view_changed(self):
        """
        Slot to synchronize the scrollbar's state with the chart's view.
        
        This is called whenever the chart is panned or zoomed, ensuring the
        scrollbar accurately reflects the visible data range.
        """
        self.scrollbar.blockSignals(True) # Prevent feedback loop
        total_bars = len(self.chart_widget.state.df)
        visible_bars = self.chart_widget.state.visible_bars
        start_bar = self.chart_widget.state.start_bar
        
        # The max scroll value is the total number of bars minus what's visible.
        max_scroll_val = max(0, total_bars - visible_bars)
        self.scrollbar.setRange(0, max_scroll_val)
        self.scrollbar.setPageStep(visible_bars) # How much to move when clicking the track
        self.scrollbar.setValue(start_bar)
        
        self.scrollbar.blockSignals(False)

    def on_mode_change(self, action: QAction):
        """Slot to update the chart's interaction mode."""
        self.chart_widget.set_mode(action.data())

    def handle_bar_hover(self, data_row: pd.Series, mouse_pos: QPoint):
        """Displays the info widget when hovering over a candle in cursor mode."""
        if self.chart_widget.state.mode == ChartMode.CURSOR:
            self.info_widget.update_and_show(data_row, mouse_pos + QPoint(15, 15))
        else:
            self.info_widget.hide()

    def update_action_states(self, is_data_loaded: bool):
        """Enables or disables toolbar actions based on whether data is loaded."""
        self.save_action.setEnabled(is_data_loaded)
        self.prepopulate_action.setEnabled(is_data_loaded)
        self.train_action.setEnabled(is_data_loaded)

    def format_timeframe(self, tf_str: str) -> str:
        """Utility to format a technical timeframe string into a human-readable one."""
        match = re.match(r"(\d+)([a-zA-Z]+)", tf_str)
        if not match: return tf_str 
        num_str, unit_str = match.groups()
        num = int(num_str)
        unit_map = {'sec': 'Second', 'min': 'Minute', 'h': 'Hour', 'd': 'Day', 'w': 'Week', 'm': 'Month'}
        unit_full = next((v for k, v in unit_map.items() if k in unit_str.lower()), unit_str.capitalize())
        if num > 1: unit_full += "s"
        return f"{num} {unit_full}"

    def open_file(self):
        """
        Opens a file dialog and initiates asynchronous data loading.
        """
        last_dir = self.settings.value("last_data_dir", str(Path.home()))
        file_path, _ = QFileDialog.getOpenFileName(self, "Select a Parquet Data File", last_dir, "Parquet Files (*.parquet);;All Files (*)")
        
        if file_path:
            self.load_action.setEnabled(False) # Disable button during load
            self.statusBar().showMessage(f"Loading {Path(file_path).name}...")

            # --- Asynchronous Loading Setup ---
            self.thread = QThread()
            self.worker = DataLoaderWorker()
            self.worker.moveToThread(self.thread)
            # Connect worker signals to main thread slots
            self.thread.started.connect(lambda: self.worker.run(file_path))
            self.worker.finished.connect(self._on_data_loaded)
            self.worker.error.connect(self._on_data_load_error)
            # Clean up thread and worker after completion
            self.worker.finished.connect(self.thread.quit)
            self.worker.finished.connect(self.worker.deleteLater)
            self.thread.finished.connect(self.thread.deleteLater)
            # Start the event loop in the new thread
            self.thread.start()

    def _on_data_loaded(self, file_path: str, ohlc_data: pd.DataFrame):
        """Slot to handle successfully loaded data."""
        self.statusBar().showMessage(f"Successfully loaded {Path(file_path).name}", 5000)
        self.load_action.setEnabled(True)
        self.settings.setValue("last_data_dir", str(Path(file_path).parent))
        
        # Attempt to parse the filename to create a descriptive title.
        display_text = ""
        try:
            stem = Path(file_path).stem
            parts = stem.split('_')
            if len(parts) >= 5:
                ticker, timeframe, _, year, month_num = parts[0:5]
                month_name = datetime.strptime(month_num, '%m').strftime('%B')
                display_text = f"{ticker.upper()} ({self.format_timeframe(timeframe)})  -  {month_name} {year}"
            else: 
                display_text = stem.replace('_', ' ').title()
        except Exception:
            display_text = Path(file_path).stem.split('_')[0].upper()

        self.chart_widget.set_symbol(display_text)
        self.chart_widget.set_data(ohlc_data)
        # Switch from welcome screen to the chart widget.
        self.setCentralWidget(self.chart_container)
        self.setWindowTitle(f'Candlestick Labelling Tool - {file_path}')
        self.update_action_states(is_data_loaded=True)
        self.on_chart_view_changed() # Initialize the scrollbar

    def _on_data_load_error(self, error_message: str):
        """Slot to handle data loading failures."""
        self.statusBar().showMessage("Failed to load data.", 5000)
        self.load_action.setEnabled(True)
        QMessageBox.critical(self, "Loading Error", error_message)
        self.update_action_states(is_data_loaded=False)

    def open_preferences_dialog(self):
        """
        Opens the preferences dialog, ensuring only one instance can exist.
        """
        if self.prefs_dialog is None:  # Create dialog if it doesn't exist
            self.prefs_dialog = PreferencesDialog(self)
            self.prefs_dialog.settings_applied.connect(self.on_settings_applied)
            self.prefs_dialog.finished.connect(self.on_prefs_dialog_closed) # Cleanup
            self.prefs_dialog.show()
        else: # If it exists, just bring it to the front
            self.prefs_dialog.activateWindow()
            self.prefs_dialog.raise_()

    def on_prefs_dialog_closed(self):
        """Slot to clean up the dialog reference when it's closed."""
        self.prefs_dialog = None
        
    def on_settings_applied(self):
        """
        Slot called when settings are applied in the preferences dialog.
        
        This reloads the style settings in the chart state and triggers a full
        re-computation of the rendering buffers to reflect the changes.
        """
        print("Applying new style settings...")
        self.chart_widget.state.load_style_settings()
        self.chart_widget._update_all_buffers() # Force refresh with new settings

    def closeEvent(self, event):
        """Saves window geometry upon closing the application."""
        self.settings.setValue("geometry", self.saveGeometry())
        super().closeEvent(event)

def main():
    app = QApplication(sys.argv)
    # Set organization and app name for QSettings to work correctly.
    app.setOrganizationName("CandleCorp")
    app.setApplicationName("CandlestickLabellingTool")
    
    try:
        with open('main.qss', 'r') as f: 
            app.setStyleSheet(f.read())
    except FileNotFoundError: 
        print("Stylesheet 'main.qss' not found. Using default styles.")
        
    window = MainWindow()
    window.setWindowIcon(QIcon('icons/appicon.png'))
    window.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()