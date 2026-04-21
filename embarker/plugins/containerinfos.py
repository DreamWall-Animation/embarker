import os
from PySide6 import QtWidgets, QtCore
from embarker.api import EmbarkerDockWidget
import embarker.commands as ebc


PLUGIN_NAME = 'Container Infos'
__version__ = '1.0'
__author__ = 'David Williams'


class ContainerInfos(EmbarkerDockWidget):
    TITLE = "Container"
    DOCK_AREA = QtCore.Qt.LeftDockWidgetArea
    OBJECT_NAME = 'Container-Infos'
    APPEARANCE_PRIORITY = 98
    VISIBLE_BY_DEFAULT = False
    ENABLE_DURING_PLAYBACK = True

    def __init__(self, parent=None):
        super().__init__(parent)

        self.directory = QtWidgets.QLineEdit()
        self.directory.setReadOnly(True)
        self.filename = QtWidgets.QLineEdit()
        self.filename.setReadOnly(True)
        self.length = QtWidgets.QLineEdit()
        self.length.setReadOnly(True)
        self.fps = QtWidgets.QLineEdit()
        self.fps.setReadOnly(True)
        self.codec = QtWidgets.QTextEdit()
        self.codec.setMaximumHeight(80)
        self.codec.setReadOnly(True)

        self.metadata = QtWidgets.QTableWidget()
        self.metadata.setSelectionMode(QtWidgets.QAbstractItemView.NoSelection)
        self.metadata.setColumnCount(2)
        self.metadata.setAlternatingRowColors(True)
        self.metadata.setShowGrid(False)
        self.metadata.setHorizontalHeaderLabels(['Key', 'Value'])
        self.metadata.verticalHeader().hide()

        form = QtWidgets.QFormLayout()
        form.setContentsMargins(0, 0, 0, 0)
        form.setSpacing(0)
        form.addRow('Directory', self.directory)
        form.addRow('Filename', self.filename)
        form.addRow('Length', self.length)
        form.addRow('Fps', self.fps)
        form.addRow('Codec', self.codec)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(form)
        layout.addWidget(self.metadata)
        layout.addStretch()

    def update_view(self):
        container = ebc.get_session().get_current_container()
        if not container:
            self.metadata.setRowCount(0)
            self.directory.setText('')
            self.filename.setText('')
            self.length.setText('')
            self.fps.setText('')
            self.codec.setText('')
            return
        self.directory.setText(os.path.dirname(container.path))
        self.filename.setText(os.path.basename(container.path))
        self.length.setText(str(container.length))
        self.fps.setText(str(container.fps))
        self.codec.setText(str(container))
        self.metadata.setRowCount(0)
        self.metadata.setRowCount(len(container.metadata))
        for i, (key, value) in enumerate(sorted(container.metadata.items())):
            self.metadata.setItem(i, 0, QtWidgets.QTableWidgetItem(key))
            self.metadata.setItem(i, 1, QtWidgets.QTableWidgetItem(str(value)))
        self.metadata.resizeColumnsToContents()
        self.metadata.horizontalHeader().setStretchLastSection(True)
