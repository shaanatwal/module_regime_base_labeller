# Save this file as welcome_widget.py
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QFrame
from PyQt6.QtGui import QIcon, QPixmap
from PyQt6.QtCore import Qt, QSize

class WelcomeWidget(QWidget):
    """
    A placeholder widget shown on startup, prompting the user to load a file.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Give this widget an object name so we can style it with QSS
        self.setObjectName("WelcomeWidget")
        
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # --- Icon ---
        icon_label = QLabel()
        # Use a common theme icon; it will be visible on most systems.
        # We scale it to be large and inviting.
        icon = QIcon.fromTheme("document-open") 
        pixmap = icon.pixmap(QSize(128, 128))
        icon_label.setPixmap(pixmap)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # --- Main Text ---
        main_text = QLabel("Candlestick Labelling Tool")
        main_text.setObjectName("WelcomeMainText") # For styling
        main_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # --- Instructional Text ---
        instruction_text = QLabel("Click the 'Load Data' icon in the toolbar to open a Parquet file and begin.")
        instruction_text.setObjectName("WelcomeInstructionText") # For styling
        instruction_text.setWordWrap(True)
        instruction_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # --- Layout Assembly ---
        layout.addStretch()
        layout.addWidget(icon_label)
        layout.addWidget(main_text)
        layout.addWidget(instruction_text)
        layout.addStretch()
        
        # A container frame to apply a border or background via stylesheet
        container = QFrame(self)
        container.setObjectName("WelcomeContainer")
        container.setLayout(layout)
        
        # Main layout for the widget itself
        main_layout = QVBoxLayout(self)
        main_layout.addWidget(container)
        self.setLayout(main_layout)