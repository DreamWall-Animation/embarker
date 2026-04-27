from dwramplayer.api import DwRamPlayerDockWidget
from PySide6 import QtCore, QtWidgets


class MyPanel(DwRamPlayerDockWidget):
    DOCK_AREA = QtCore.Qt.DockWidgetArea.RightDockWidgetArea
    OBJECT_NAME = 'Filepath'
    TITLE = 'Filepath'
    APPEARANCE_PRIORITY = 0

    def __init__(self, session):
        super().__init__(session)
        self.label = QtWidgets.QLineEdit("---")
        layout = QtWidgets.QHBoxLayout(self)
        layout.addWidget(self.label)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setMaximumHeight(60)

    def update_current_frame(self):
        container = self.session.get_current_container()
        self.label.setText(container.path)