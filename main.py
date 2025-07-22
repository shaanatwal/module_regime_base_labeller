# Save this as main.py
import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QFileDialog, QDialog, QWidget, QSizePolicy
from PyQt6.QtGui import QAction, QIcon
from PyQt6.QtCore import Qt

# Import our custom modules
from data_loader import load_parquet_data
from candle_widget import CandleWidget
from preferences_dialog import PreferencesDialog
from welcome_widget import WelcomeWidget # <-- IMPORT NEW WIDGET

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle('Candlestick Labelling Tool')
        self.setGeometry(100, 100, 1200, 800)

        # --- Central Widgets ---
        # Create instances of both widgets. We will swap them as needed.
        self.welcome_screen = WelcomeWidget()
        self.chart_widget = CandleWidget()
        self.setCentralWidget(self.welcome_screen) # Start with the welcome screen

        # --- Toolbar and Actions (Buttons) ---
        toolbar = self.addToolBar('Main Toolbar')
        # MAKE ICONS AND TEXT VISIBLE
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
        
        # Set initial button states
        self.update_action_states(is_data_loaded=False)

    def update_action_states(self, is_data_loaded: bool):
        """Enable or disable toolbar actions based on whether data is loaded."""
        self.save_action.setEnabled(is_data_loaded)
        self.prepopulate_action.setEnabled(is_data_loaded)
        self.train_action.setEnabled(is_data_loaded)

    def open_file(self):
        options = QFileDialog.Option.DontUseNativeDialog
        file_path, _ = QFileDialog.getOpenFileName(self, "Select a Parquet Data File", "", "Parquet Files (*.parquet);;All Files (*)", options=options)

        if file_path:
            print(f"User selected file: {file_path}")
            ohlc_data = load_parquet_data(file_path)

            if not ohlc_data.empty:
                self.chart_widget.set_data(ohlc_data)
                # SWAP to the chart widget
                self.setCentralWidget(self.chart_widget)
                self.setWindowTitle(f'Candlestick Labelling Tool - {file_path}')
                self.update_action_states(is_data_loaded=True)
            else:
                print("Failed to load data from the selected file.")
                # Stay on the welcome screen
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

def main():
    app = QApplication(sys.argv)
    
    # --- Load Stylesheet ---
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