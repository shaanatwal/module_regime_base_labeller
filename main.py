# Save this as main.py
import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QFileDialog
from PyQt6.QtGui import QAction, QIcon

# Import our custom modules
from data_loader import load_parquet_data
from candle_widget import CandleWidget

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle('Candlestick Labelling Tool')
        self.setGeometry(100, 100, 1200, 800)

        # --- Central Widget (the chart) ---
        # Initialize the CandleWidget empty. It will draw nothing but the black background.
        self.chart_widget = CandleWidget()
        self.setCentralWidget(self.chart_widget)

        # --- Toolbar and Actions (Buttons) ---
        toolbar = self.addToolBar('Main Toolbar')

        # Use QAction for toolbar buttons. They can have icons and text.
        # We use built-in icons from the system's theme for a native look and feel.
        self.load_action = QAction(QIcon.fromTheme('document-open'), 'Load Data', self)
        self.load_action.triggered.connect(self.open_file) # Connect to method
        toolbar.addAction(self.load_action)

        self.save_action = QAction(QIcon.fromTheme('document-save'), 'Save Labels', self)
        # self.save_action.triggered.connect(self.save_labels) # We'll create this later
        toolbar.addAction(self.save_action)

        toolbar.addSeparator()

        self.prepopulate_action = QAction(QIcon.fromTheme('media-playback-start'), 'Pre-populate', self)
        # self.prepopulate_action.triggered.connect(self.run_prepopulate) # We'll create this later
        toolbar.addAction(self.prepopulate_action)

        self.train_action = QAction(QIcon.fromTheme('system-run'), 'Train Model', self)
        # self.train_action.triggered.connect(self.run_training) # We'll create this later
        toolbar.addAction(self.train_action)
        
        # --- Initial State ---
        # Disable buttons that require data to be loaded
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
                # Send the loaded data to our chart widget
                self.chart_widget.set_data(ohlc_data)
                
                # Update window title and enable the other buttons
                self.setWindowTitle(f'Candlestick Labelling Tool - {file_path}')
                self.save_action.setEnabled(True)
                self.prepopulate_action.setEnabled(True)
                self.train_action.setEnabled(True)
            else:
                print("Failed to load data from the selected file.")
                self.save_action.setEnabled(False)
                self.prepopulate_action.setEnabled(False)
                self.train_action.setEnabled(False)


def main():
    """The main entry point."""
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()