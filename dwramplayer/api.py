from PySide6 import QtWidgets, QtCore, QtGui
from dwramplayer.session import Session


class DwRamPlayerDockWidget(QtWidgets.QWidget):
    """
    Constants to configure:
    DOCK_AREA:
        Default QMainWindow dock area where the widget will be added.
    TITLE:
        Title of the dock.
    OBJECT_NAME:
        Unique Qt object name, used to save and restore state.
    APPEARANCE_PRIORITY:
        Determines the order in which plugin panels are created.

    Signals:
    current_frame_changed:
        Emitted to notify the application that the current frame in the
        playlist has changed.
    update_required:
        Emitted to request the application to repaint, without updating the
        viewport frame.
    """

    current_frame_changed = QtCore.Signal() # Emit to update the UI
    update_required = QtCore.Signal()

    DOCK_AREA: QtCore.Qt.DockWidgetArea
    TITLE: str
    OBJECT_NAME: str
    APPEARANCE_PRIORITY: int = 0

    def __init__(self, session: Session):
        super().__init__()
        self.session = session

    def update_current_frame(self):
        """
        Callback method to implement to manage when the current frame is
        changed from the player and data must be changed.
        This is NOT triggered when playback is active.
        """
        pass

    def get_actions(self) -> dict[str, QtGui.QAction]:
        """
        Method to implement allowing to add custom actions with shortcut to
        the main application
        """
        return {}