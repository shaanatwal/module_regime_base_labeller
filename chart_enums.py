from enum import Enum, auto

class ChartMode(Enum):
    """
    Defines the user interaction modes for the chart widget.

    This enumeration provides a clear and type-safe way to manage the
    chart's behavior based on which tool is currently selected by the user.

    Attributes:
        CURSOR: The default mode for navigation, inspection (hovering),
                panning, and zooming.
        MARKER: A mode for adding or editing labels on the chart.
    """
    CURSOR = auto()
    MARKER = auto()