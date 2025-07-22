# Save this file as preferences_dialog.py
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QPushButton, QColorDialog, QDialogButtonBox, QLabel, QHBoxLayout, QFrame, QGridLayout
from PyQt6.QtGui import QColor, QPalette
from PyQt6.QtCore import Qt

class PreferencesDialog(QDialog):
    def __init__(self, initial_bg_color: QColor, initial_up_color: QColor, initial_down_color: QColor, parent=None):
        super().__init__(parent)
        
        self.setWindowTitle("Preferences")
        self.setMinimumWidth(350)

        # Store the selected colors
        self.background_color = initial_bg_color
        self.up_color = initial_up_color
        self.down_color = initial_down_color

        # --- Layouts and Widgets ---
        main_layout = QVBoxLayout(self)
        grid_layout = QGridLayout()
        grid_layout.setColumnStretch(1, 1) # Allow the color swatch column to stretch a bit

        # Background Color row
        bg_label = QLabel("Background Color:")
        self.bg_swatch = self.create_color_swatch(self.background_color)
        self.bg_swatch.clicked.connect(self.choose_bg_color)
        grid_layout.addWidget(bg_label, 0, 0)
        grid_layout.addWidget(self.bg_swatch, 0, 1)

        # Up Candle Color row
        up_label = QLabel("Up Candle Color:")
        self.up_swatch = self.create_color_swatch(self.up_color)
        self.up_swatch.clicked.connect(self.choose_up_color)
        grid_layout.addWidget(up_label, 1, 0)
        grid_layout.addWidget(self.up_swatch, 1, 1)
        
        # Down Candle Color row
        down_label = QLabel("Down Candle Color:")
        self.down_swatch = self.create_color_swatch(self.down_color)
        self.down_swatch.clicked.connect(self.choose_down_color)
        grid_layout.addWidget(down_label, 2, 0)
        grid_layout.addWidget(self.down_swatch, 2, 1)

        # OK and Cancel buttons
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)

        main_layout.addLayout(grid_layout)
        main_layout.addStretch()
        main_layout.addWidget(button_box)

    def create_color_swatch(self, color: QColor) -> QPushButton:
        """Helper function to create and style a color swatch button."""
        swatch = QPushButton()
        swatch.setFixedSize(100, 25)
        swatch.setFlat(True)
        swatch.setAutoFillBackground(True)
        self.update_swatch_color(swatch, color)
        return swatch

    def update_swatch_color(self, swatch: QPushButton, color: QColor):
        """Updates the preview color of a single swatch."""
        palette = swatch.palette()
        palette.setColor(QPalette.ColorRole.Button, color)
        swatch.setPalette(palette)

    def choose_bg_color(self):
        new_color = QColorDialog.getColor(self.background_color, self, "Select Background Color")
        if new_color.isValid():
            self.background_color = new_color
            self.update_swatch_color(self.bg_swatch, new_color)

    def choose_up_color(self):
        new_color = QColorDialog.getColor(self.up_color, self, "Select Up Candle Color")
        if new_color.isValid():
            self.up_color = new_color
            self.update_swatch_color(self.up_swatch, new_color)
            
    def choose_down_color(self):
        new_color = QColorDialog.getColor(self.down_color, self, "Select Down Candle Color")
        if new_color.isValid():
            self.down_color = new_color
            self.update_swatch_color(self.down_swatch, new_color)

    def get_selected_colors(self) -> tuple[QColor, QColor, QColor]:
        """Public method to retrieve all chosen colors at once."""
        return self.background_color, self.up_color, self.down_color