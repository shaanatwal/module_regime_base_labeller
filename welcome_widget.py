from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QFrame
from PyQt6.QtGui import QIcon, QPixmap
from PyQt6.QtCore import Qt, QSize

class WelcomeWidget(QWidget):
    """
    A placeholder widget displayed on application startup.

    It prompts the user to load a data file and provides a visually appealing
    entry point before the main chart is shown. The components of this widget

    are given object names to allow for detailed styling via QSS.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Assign an object name to the root widget for top-level styling.
        self.setObjectName("WelcomeWidget")
        
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # --- Icon ---
        # A large, friendly icon to visually anchor the widget.
        icon_label = QLabel()
        # Using a standard theme icon ensures it's likely available on any system.
        icon = QIcon.fromTheme("document-open") 
        pixmap = icon.pixmap(QSize(128, 128))
        icon_label.setPixmap(pixmap)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # --- Main Text ---
        main_text = QLabel("Candlestick Labelling Tool")
        main_text.setObjectName("WelcomeMainText") # For specific font/color styling.
        main_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # --- Instructional Text ---
        instruction_text = QLabel("Click the 'Load Data' icon in the toolbar to open a Parquet file and begin.")
        instruction_text.setObjectName("WelcomeInstructionText") # For specific styling.
        instruction_text.setWordWrap(True)
        instruction_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # --- Layout Assembly ---
        # Use stretch factors to center the content vertically.
        layout.addStretch()
        layout.addWidget(icon_label)
        layout.addWidget(main_text)
        layout.addWidget(instruction_text)
        layout.addStretch()
        
        # A container frame allows us to apply a border and max-width via QSS
        # without affecting the main widget's background.
        container = QFrame()
        container.setObjectName("WelcomeContainer")
        container.setLayout(layout)
        
        # The final layout for the WelcomeWidget itself contains just the container.
        main_layout = QVBoxLayout(self)
        main_layout.addWidget(container)
        self.setLayout(main_layout)