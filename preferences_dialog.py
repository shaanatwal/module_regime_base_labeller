# Save this file as preferences_dialog.py
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QPushButton, QColorDialog, QDialogButtonBox, 
                             QLabel, QGridLayout, QDoubleSpinBox, QTabWidget, QWidget, QComboBox, 
                             QSpinBox, QGroupBox, QRadioButton)
from PyQt6.QtGui import QColor, QPalette
from PyQt6.QtCore import pyqtSignal

from style_manager import StyleManager, PEN_STYLE_MAP, REVERSE_PEN_STYLE_MAP

class ColorButton(QPushButton):
    """A button that displays a color and opens a color dialog when clicked."""
    colorChanged = pyqtSignal(QColor)

    def __init__(self, initial_color: QColor, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._color = initial_color
        self.setFixedSize(100, 28)
        self.setFlat(True)
        self.setAutoFillBackground(True)
        self._update_swatch()
        self.clicked.connect(self._choose_color)

    def _update_swatch(self):
        palette = self.palette()
        palette.setColor(QPalette.ColorRole.Button, self._color)
        self.setPalette(palette)

    def _choose_color(self):
        dialog = QColorDialog(self._color, self)
        dialog.setOption(QColorDialog.ColorDialogOption.ShowAlphaChannel, True)
        if dialog.exec():
            new_color = dialog.selectedColor()
            if new_color.isValid():
                self.setColor(new_color)

    def color(self) -> QColor:
        return self._color
    
    def setColor(self, color: QColor):
        if self._color != color:
            self._color = color
            self._update_swatch()
            self.colorChanged.emit(self._color)

class PreferencesDialog(QDialog):
    # Signal emitted when 'Apply' or 'OK' is clicked
    settings_applied = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Preferences")
        self.setMinimumWidth(450)
        self.sm = StyleManager()

        main_layout = QVBoxLayout(self)
        
        # Tabs for organization
        tab_widget = QTabWidget()
        main_layout.addWidget(tab_widget)

        # Create tabs
        tab_widget.addTab(self._create_colors_tab(), "Colors")
        tab_widget.addTab(self._create_lines_tab(), "Lines")
        tab_widget.addTab(self._create_background_tab(), "Background")
        tab_widget.addTab(self._create_other_tab(), "Other")

        # Dialog buttons
        button_box = QDialogButtonBox()
        self.restore_btn = button_box.addButton("Restore Defaults", QDialogButtonBox.ButtonRole.ResetRole)
        button_box.addButton(QDialogButtonBox.StandardButton.Ok)
        button_box.addButton(QDialogButtonBox.StandardButton.Cancel)
        self.apply_btn = button_box.addButton(QDialogButtonBox.StandardButton.Apply)
        
        self.restore_btn.clicked.connect(self.restore_defaults)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        self.apply_btn.clicked.connect(self._apply_and_save_settings)
        
        main_layout.addWidget(button_box)

    def _create_colors_tab(self) -> QWidget:
        tab = QWidget()
        layout = QGridLayout(tab)
        
        # Up/Down Candle
        layout.addWidget(QLabel("Up Candle Body:"), 0, 0); self.up_candle_btn = ColorButton(QColor(self.sm.get_value("colors/up_candle"))); layout.addWidget(self.up_candle_btn, 0, 1)
        layout.addWidget(QLabel("Down Candle Body:"), 1, 0); self.down_candle_btn = ColorButton(QColor(self.sm.get_value("colors/down_candle"))); layout.addWidget(self.down_candle_btn, 1, 1)
        layout.addWidget(QLabel("Up Candle Wick:"), 2, 0); self.up_wick_btn = ColorButton(QColor(self.sm.get_value("colors/up_wick"))); layout.addWidget(self.up_wick_btn, 2, 1)
        layout.addWidget(QLabel("Down Candle Wick:"), 3, 0); self.down_wick_btn = ColorButton(QColor(self.sm.get_value("colors/down_wick"))); layout.addWidget(self.down_wick_btn, 3, 1)
        layout.addWidget(QLabel("Up Volume Bar:"), 4, 0); self.up_volume_btn = ColorButton(QColor(self.sm.get_value("colors/up_volume"))); layout.addWidget(self.up_volume_btn, 4, 1)
        layout.addWidget(QLabel("Down Volume Bar:"), 5, 0); self.down_volume_btn = ColorButton(QColor(self.sm.get_value("colors/down_volume"))); layout.addWidget(self.down_volume_btn, 5, 1)

        layout.setRowStretch(6, 1)
        return tab

    def _create_lines_tab(self) -> QWidget:
        tab = QWidget()
        layout = QGridLayout(tab)
        
        # Headers
        layout.addWidget(QLabel("<b>Color</b>"), 0, 1)
        layout.addWidget(QLabel("<b>Width</b>"), 0, 2)
        layout.addWidget(QLabel("<b>Style</b>"), 0, 3)

        # Crosshair
        layout.addWidget(QLabel("Crosshair:"), 1, 0)
        self.crosshair_color_btn = ColorButton(QColor(self.sm.get_value("lines/crosshair"))); layout.addWidget(self.crosshair_color_btn, 1, 1)
        self.crosshair_width_spin = QSpinBox(); self.crosshair_width_spin.setRange(1, 10); self.crosshair_width_spin.setValue(int(self.sm.get_value("props/crosshair_width"))); layout.addWidget(self.crosshair_width_spin, 1, 2)
        self.crosshair_style_combo = QComboBox(); self.crosshair_style_combo.addItems(PEN_STYLE_MAP.keys()); self.crosshair_style_combo.setCurrentText(self.sm.get_value("props/crosshair_style")); layout.addWidget(self.crosshair_style_combo, 1, 3)

        # Price Grid
        layout.addWidget(QLabel("Price Grid:"), 2, 0)
        self.price_grid_color_btn = ColorButton(QColor(self.sm.get_value("lines/price_grid"))); layout.addWidget(self.price_grid_color_btn, 2, 1)
        self.price_grid_width_spin = QSpinBox(); self.price_grid_width_spin.setRange(1, 10); self.price_grid_width_spin.setValue(int(self.sm.get_value("props/price_grid_width"))); layout.addWidget(self.price_grid_width_spin, 2, 2)
        self.price_grid_style_combo = QComboBox(); self.price_grid_style_combo.addItems(PEN_STYLE_MAP.keys()); self.price_grid_style_combo.setCurrentText(self.sm.get_value("props/price_grid_style")); layout.addWidget(self.price_grid_style_combo, 2, 3)

        # Time Grid
        layout.addWidget(QLabel("Time Grid:"), 3, 0)
        self.time_grid_color_btn = ColorButton(QColor(self.sm.get_value("lines/time_grid"))); layout.addWidget(self.time_grid_color_btn, 3, 1)
        self.time_grid_width_spin = QSpinBox(); self.time_grid_width_spin.setRange(1, 10); self.time_grid_width_spin.setValue(int(self.sm.get_value("props/time_grid_width"))); layout.addWidget(self.time_grid_width_spin, 3, 2)
        self.time_grid_style_combo = QComboBox(); self.time_grid_style_combo.addItems(PEN_STYLE_MAP.keys()); self.time_grid_style_combo.setCurrentText(self.sm.get_value("props/time_grid_style")); layout.addWidget(self.time_grid_style_combo, 3, 3)
        
        layout.setRowStretch(4, 1)
        return tab

    def _create_background_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        group_box = QGroupBox("Background Mode")
        group_layout = QGridLayout(group_box)

        self.solid_radio = QRadioButton("Solid Color"); group_layout.addWidget(self.solid_radio, 0, 0)
        self.bg_color1_btn = ColorButton(QColor(self.sm.get_value("background/color1"))); group_layout.addWidget(self.bg_color1_btn, 0, 1)
        
        self.gradient_radio = QRadioButton("Gradient"); group_layout.addWidget(self.gradient_radio, 1, 0)
        self.bg_color2_btn = ColorButton(QColor(self.sm.get_value("background/color2"))); group_layout.addWidget(self.bg_color2_btn, 1, 1)
        
        self.gradient_dir_combo = QComboBox(); self.gradient_dir_combo.addItems(["Vertical", "Horizontal"]); self.gradient_dir_combo.setCurrentText(self.sm.get_value("background/gradient_direction")); group_layout.addWidget(self.gradient_dir_combo, 1, 2)
        
        self.solid_radio.toggled.connect(self._update_bg_controls)
        
        bg_mode = self.sm.get_value("background/mode")
        if bg_mode == "Solid": self.solid_radio.setChecked(True)
        else: self.gradient_radio.setChecked(True)
        
        layout.addWidget(group_box)
        layout.addStretch()
        return tab

    def _update_bg_controls(self, is_solid):
        self.bg_color2_btn.setEnabled(not is_solid)
        self.gradient_dir_combo.setEnabled(not is_solid)

    def _create_other_tab(self) -> QWidget:
        tab = QWidget()
        layout = QGridLayout(tab)
        layout.addWidget(QLabel("Volume Pane Ratio:"), 0, 0)
        self.volume_ratio_spinner = QDoubleSpinBox(); self.volume_ratio_spinner.setRange(0.1, 0.9); self.volume_ratio_spinner.setSingleStep(0.05); self.volume_ratio_spinner.setValue(float(self.sm.get_value("other/volume_pane_ratio"))); layout.addWidget(self.volume_ratio_spinner, 0, 1)
        layout.setRowStretch(1, 1); layout.setColumnStretch(2, 1)
        return tab

    def _apply_and_save_settings(self):
        # Colors
        self.sm.set_value("colors/up_candle", self.up_candle_btn.color().name(QColor.NameFormat.HexArgb))
        self.sm.set_value("colors/down_candle", self.down_candle_btn.color().name(QColor.NameFormat.HexArgb))
        self.sm.set_value("colors/up_wick", self.up_wick_btn.color().name(QColor.NameFormat.HexArgb))
        self.sm.set_value("colors/down_wick", self.down_wick_btn.color().name(QColor.NameFormat.HexArgb))
        self.sm.set_value("colors/up_volume", self.up_volume_btn.color().name(QColor.NameFormat.HexArgb))
        self.sm.set_value("colors/down_volume", self.down_volume_btn.color().name(QColor.NameFormat.HexArgb))
        # Lines
        self.sm.set_value("lines/crosshair", self.crosshair_color_btn.color().name(QColor.NameFormat.HexArgb))
        self.sm.set_value("props/crosshair_width", self.crosshair_width_spin.value())
        self.sm.set_value("props/crosshair_style", self.crosshair_style_combo.currentText())
        self.sm.set_value("lines/price_grid", self.price_grid_color_btn.color().name(QColor.NameFormat.HexArgb))
        self.sm.set_value("props/price_grid_width", self.price_grid_width_spin.value())
        self.sm.set_value("props/price_grid_style", self.price_grid_style_combo.currentText())
        self.sm.set_value("lines/time_grid", self.time_grid_color_btn.color().name(QColor.NameFormat.HexArgb))
        self.sm.set_value("props/time_grid_width", self.time_grid_width_spin.value())
        self.sm.set_value("props/time_grid_style", self.time_grid_style_combo.currentText())
        # Background
        self.sm.set_value("background/mode", "Solid" if self.solid_radio.isChecked() else "Gradient")
        self.sm.set_value("background/color1", self.bg_color1_btn.color().name(QColor.NameFormat.HexArgb))
        self.sm.set_value("background/color2", self.bg_color2_btn.color().name(QColor.NameFormat.HexArgb))
        self.sm.set_value("background/gradient_direction", self.gradient_dir_combo.currentText())
        # Other
        self.sm.set_value("other/volume_pane_ratio", self.volume_ratio_spinner.value())
        
        self.settings_applied.emit()

    def accept(self):
        self._apply_and_save_settings()
        super().accept()
        
    def restore_defaults(self):
        self.sm.restore_defaults()
        # To see the changes, we need to close and reopen the dialog.
        # A more advanced implementation could update the UI controls in-place.
        self.parent().open_preferences_dialog() # A bit of a hack, but effective
        self.close()