# Save this as main.py
import sys
from pathlib import Path # Modern way to handle file paths
from PyQt6.QtWidgets import QApplication, QMainWindow, QFileDialog, QDialog, QWidget, QSizePolicy
from PyQt6.QtGui import QAction, QIcon
from PyQt6.QtCore import Qt, QSettings # <-- IMPORT QSETTINGS

# Import our custom modules
from data_loader import load_parquet_data
from candle_widget import CandleWidget
from preferences_dialog import PreferencesDialog
from welcome_widget import WelcomeWidget

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle('Candlestick Labelling Tool')
        self.setGeometry(100, 100, 1200, 800)

        # Restore window geometry from the last session
        self.settings = QSettings()
        geom = self.settings.value("geometry")
        if geom:
            self.restoreGeometry(geom)

        # --- Central Widgets ---
        self.welcome_screen = WelcomeWidget()
        self.chart_widget = CandleWidget()
        self.setCentralWidget(self.welcome_screen) 

        # --- Toolbar and Actions (Buttons) ---
        toolbar = self.addToolBar('Main Toolbar')
        toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)

        self.load_action = QAction(QIcon.fromTheme('document-open'), 'Load Data', self)
        self.load_action.setToolTip("Open a Parquet data file to begin charting.")
        self.load_action.triggered.connect(self.open_file)
        toolbar.addAction(self.load_action)

        self.save_action = QAction(QIcon.fromTheme('document-save'), 'Save Labels', self)
        self.save_action.setToolTip("Save labels (disabled until data is loaded).")
        toolbar.addAction(self.save_action)

        toolbar.addSeparator()

        self.prepopulate_action = QAction(QIcon.fromTheme('media-playback-start'), 'Pre-populate', self)
        self.prepopulate_action.setToolTip("Pre-populate labels (disabled until data is loaded).")
        toolbar.addAction(self.prepopulate_action)

        self.train_action = QAction(QIcon.fromTheme('system-run'), 'Train Model', self)
        self.train_action.setToolTip("Train a new model (disabled until data is loaded).")
        toolbar.addAction(self.train_action)
        
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        toolbar.addWidget(spacer)

        self.prefs_action = QAction(QIcon.fromTheme('preferences-system'), 'Preferences', self)
        self.prefs_action.setToolTip("Change application settings like chart colors.")
        self.prefs_action.triggered.connect(self.open_preferences_dialog)
        toolbar.addAction(self.prefs_action)
        
        self.update_action_states(is_data_loaded=False)

    def update_action_states(self, is_data_loaded: bool):
        self.save_action.setEnabled(is_data_loaded)
        self.prepopulate_action.setEnabled(is_data_loaded)
        self.train_action.setEnabled(is_data_loaded)

    def open_file(self):
        """Opens a file dialog starting in the last-used directory."""
        # Retrieve the last used directory from settings, defaulting to the user's home folder.
        last_dir = self.settings.value("last_data_dir", str(Path.home()))
        
        options = QFileDialog.Option.DontUseNativeDialog
        file_path, _ = QFileDialog.getOpenFileName(
            self, 
            "Select a Parquet Data File", 
            last_dir, # <-- START IN THE LAST USED DIRECTORY
            "Parquet Files (*.parquet);;All Files (*)", 
            options=options
        )

        if file_path:
            # Save the directory of the chosen file for next time.
            new_dir = str(Path(file_path).parent)
            self.settings.setValue("last_data_dir", new_dir)
            
            print(f"User selected file: {file_path}")
            ohlc_data = load_parquet_data(file_path)

            if not ohlc_data.empty:
                self.chart_widget.set_data(ohlc_data)
                self.setCentralWidget(self.chart_widget)
                self.setWindowTitle(f'Candlestick Labelling Tool - {file_path}')
                self.update_action_states(is_data_loaded=True)
            else:
                print("Failed to load data from the selected file.")
                self.setCentralWidget(self.welcome_screen)
                self.setWindowTitle('Candlestick Labelling Tool')
                self.update_action_states(is_data_loaded=False)

    def open_preferences_dialog(self):
        dialog = PreferencesDialog(
            initial_bg_color=self.chart_widget.get_background_color(),
            initial_up_color=self.chart_widget.get_up_color(),
            initial_down_color=self.chart_widget.get_down_color(),
            parent=self
        )
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            bg_color, up_color, down_color = dialog.get_selected_colors()
            self.chart_widget.set_background_color(bg_color)
            self.chart_widget.set_up_color(up_color)
            self.chart_widget.set_down_color(down_color)
            print(f"Settings updated. BG: {bg_color.name()}, Up: {up_color.name()}, Down: {down_color.name()}")

    def closeEvent(self, event):
        """Save settings when the window closes."""
        self.settings.setValue("geometry", self.saveGeometry())
        super().closeEvent(event)


def main():
    app = QApplication(sys.argv)
    
    # Set organization and application names for QSettings
    app.setOrganizationName("CandleCorp")
    app.setApplicationName("CandlestickLabellingTool")

    try:
        with open('main.qss', 'r') as f:
            app.setStyleSheet(f.read())
            print("Stylesheet 'main.qss' loaded successfully.")
    except FileNotFoundError:
        print("Stylesheet 'main.qss' not found. Using default styles.")
        
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()