# Save this as main.py
import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QFileDialog, QDialog, QWidget, QSizePolicy
from PyQt6.QtGui import QAction, QIcon

# Import our custom modules
from data_loader import load_parquet_data
from candle_widget import CandleWidget
from preferences_dialog import PreferencesDialog

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle('Candlestick Labelling Tool')
        self.setGeometry(100, 100, 1200, 800)

        # Central Widget (the chart)
        self.chart_widget = CandleWidget()
        self.setCentralWidget(self.chart_widget)

        # Toolbar and Actions (Buttons)
        toolbar = self.addToolBar('Main Toolbar')

        self.load_action = QAction(QIcon.fromTheme('document-open'), 'Load Data', self)
        self.load_action.triggered.connect(self.open_file)
        toolbar.addAction(self.load_action)

        self.save_action = QAction(QIcon.fromTheme('document-save'), 'Save Labels', self)
        # self.save_action.triggered.connect(self.save_labels)
        toolbar.addAction(self.save_action)

        toolbar.addSeparator()

        self.prepopulate_action = QAction(QIcon.fromTheme('media-playback-start'), 'Pre-populate', self)
        # self.prepopulate_action.triggered.connect(self.run_prepopulate)
        toolbar.addAction(self.prepopulate_action)

        self.train_action = QAction(QIcon.fromTheme('system-run'), 'Train Model', self)
        # self.train_action.triggered.connect(self.run_training)
        toolbar.addAction(self.train_action)
        
        # Add a spacer widget to push the preferences button to the right
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        toolbar.addWidget(spacer)

        # Preferences Action
        self.prefs_action = QAction(QIcon.fromTheme('preferences-system'), 'Preferences', self)
        self.prefs_action.triggered.connect(self.open_preferences_dialog)
        toolbar.addAction(self.prefs_action)
        
        # Initial State
        self.save_action.setEnabled(False)
        self.prepopulate_action.setEnabled(False)
        self.train_action.setEnabled(False)

    def open_file(self):
        """Opens a file dialog, loads data, and updates the chart."""
        options = QFileDialog.Option.DontUseNativeDialog
        file_path, _ = QFileDialog.getOpenFileName(self, "Select a Parquet Data File", "", "Parquet Files (*.parquet);;All Files (*)", options=options)

        if file_path:
            print(f"User selected file: {file_path}")
            ohlc_data = load_parquet_data(file_path)

            if not ohlc_data.empty:
                self.chart_widget.set_data(ohlc_data)
                self.setWindowTitle(f'Candlestick Labelling Tool - {file_path}')
                self.save_action.setEnabled(True)
                self.prepopulate_action.setEnabled(True)
                self.train_action.setEnabled(True)
            else:
                print("Failed to load data from the selected file.")
                self.save_action.setEnabled(False)
                self.prepopulate_action.setEnabled(False)
                self.train_action.setEnabled(False)

    def open_preferences_dialog(self):
        """Opens the preferences dialog to change settings."""
        # Pass all current colors from the chart widget to the dialog
        dialog = PreferencesDialog(
            initial_bg_color=self.chart_widget.get_background_color(),
            initial_up_color=self.chart_widget.get_up_color(),
            initial_down_color=self.chart_widget.get_down_color(),
            parent=self
        )
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Retrieve all new colors from the dialog
            bg_color, up_color, down_color = dialog.get_selected_colors()
            
            # Apply the new colors to the chart widget
            self.chart_widget.set_background_color(bg_color)
            self.chart_widget.set_up_color(up_color)
            self.chart_widget.set_down_color(down_color)
            
            print(f"Settings updated. BG: {bg_color.name()}, Up: {up_color.name()}, Down: {down_color.name()}")


def main():
    """The main entry point."""
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()