# Save this file as chart_enums.py
from enum import Enum, auto

class ChartMode(Enum):
    """Defines the interaction modes for the chart widget."""
    CURSOR = auto()
    MARKER = auto()