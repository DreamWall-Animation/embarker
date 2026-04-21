import os
from PySide6 import QtWidgets, QtCore
from embarker.api import EmbarkerDockWidget
import embarker.commands as ebc


PLUGIN_NAME = 'Playlist'
__version__ = '1.0'
__author__ = 'David Williams'


class ContainerInfos(EmbarkerDockWidget):
    TITLE = "Playlist"
    DOCK_AREA = QtCore.Qt.LeftDockWidgetArea
    OBJECT_NAME = 'Playlist'
    APPEARANCE_PRIORITY = 98
    VISIBLE_BY_DEFAULT = False
    ENABLE_DURING_PLAYBACK = True

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.model = ContainersModel()
        self._current_container_id = None
        self.containers = QtWidgets.QTableView()
        behavior = QtWidgets.QAbstractItemView.SelectRows
        self.containers.setSelectionBehavior(behavior)
        mode = QtWidgets.QHeaderView.ResizeToContents
        self.containers.horizontalHeader().setSectionResizeMode(mode)
        self.containers.verticalHeader().hide()
        self.containers.setModel(self.model)
        self.containers.selectionModel().selectionChanged.connect(
            self.container_selected)
        self.containers.setShowGrid(False)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.containers)

    def resizeEvent(self, event):
        mode = QtWidgets.QHeaderView.ResizeToContents
        self.containers.horizontalHeader().setSectionResizeMode(mode)
        self.containers.horizontalHeader().setStretchLastSection(True)
        return super().resizeEvent(event)

    def update_view(self):
        self.model.layoutChanged.emit()
        container = ebc.get_session().get_current_container()
        if not container or container.id == self._current_container_id:
            return
        row = [
            c.id for c in ebc.get_session().playlist.containers].index(container.id)
        self.containers.blockSignals(True)
        self.containers.selectionModel().blockSignals(True)
        self.containers.selectRow(row)
        self.containers.selectionModel().blockSignals(False)
        self.containers.blockSignals(False)
        self._current_container_id = container.id

    def container_selected(self, *_):
        index = next(
            iter(self.containers.selectionModel().selectedIndexes()), None)
        if not index:
            return
        container = ebc.get_session().playlist.containers[index.row()]
        frame = ebc.get_session().playlist.first_frames[container.id]
        ebc.set_frame(frame)


class ContainersModel(QtCore.QAbstractTableModel):
    HEADERS = 'File', 'Start frame'

    def rowCount(self, *_):
        return len(ebc.get_session().playlist.containers)

    def columnCount(self, *_):
        return len(self.HEADERS)

    def headerData(self, section, orientation, role):
        if role != QtCore.Qt.DisplayRole or orientation == QtCore.Qt.Vertical:
            return
        return self.HEADERS[section]

    def data(self, index, role):
        if not index.isValid():
            return

        if role == QtCore.Qt.DisplayRole:
            if index.column() == 0:
                container = ebc.get_session().playlist.containers[index.row()]
                return os.path.basename(container.path)

            if index.column() == 1:
                container = ebc.get_session().playlist.containers[index.row()]
                return str(ebc.get_session().playlist.first_frames[container.id])

        if role == QtCore.Qt.TextAlignmentRole:
            if index.column() == 1:
                return QtCore.Qt.AlignCenter