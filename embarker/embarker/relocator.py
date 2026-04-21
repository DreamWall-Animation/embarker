import os
import msgpack

from PySide6 import QtWidgets, QtCore, QtGui

from embarker.resources import get_icon
from embarker.msgbox import ScrollMessageBox
import embarker.commands as ebc


class MovieRelocator(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent, QtCore.Qt.Tool)
        self.setWindowTitle('Movie relocator')
        self.file = QtWidgets.QLineEdit()
        self.file.setReadOnly(True)
        self.browser = QtWidgets.QPushButton(get_icon('open_session.png'), '')
        self.browser.released.connect(self.select_session)

        self.search = QtWidgets.QLineEdit()
        self.search.textEdited.connect(self.update_search_and_replace)
        self.replace = QtWidgets.QLineEdit()
        self.replace.textEdited.connect(self.update_search_and_replace)

        self.alternate_source = QtWidgets.QPushButton(
            get_icon('open_session.png'), 'Find source videos in folder.')
        self.alternate_source.released.connect(
            self.look_up_in_alternate_source)

        self.model = SessionFilesModel()
        self.files = QtWidgets.QListView()
        self.files.setModel(self.model)

        self.open = QtWidgets.QPushButton('Open')
        self.open.released.connect(self._call_open)
        self.save_as = QtWidgets.QPushButton('Save as')
        self.save_as.released.connect(self._call_save_as)
        self.save_as_and_open = QtWidgets.QPushButton('Save as / Open')
        self.save_as_and_open.released.connect(self._call_save_as_and_open)

        actions_layout = QtWidgets.QHBoxLayout()
        actions_layout.setContentsMargins(0, 0, 0, 0)
        actions_layout.addWidget(self.open)
        actions_layout.addWidget(self.save_as)
        actions_layout.addWidget(self.save_as_and_open)

        file_layout = QtWidgets.QHBoxLayout()
        file_layout.setContentsMargins(0, 0, 0, 0)
        file_layout.addWidget(self.file)
        file_layout.addWidget(self.browser)

        form_layout = QtWidgets.QFormLayout()
        form_layout.setContentsMargins(0, 0, 0, 0)
        form_layout.addRow('Search: ', self.search)
        form_layout.addRow('Replace: ', self.replace)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addLayout(file_layout)
        layout.addLayout(form_layout)
        layout.addWidget(self.alternate_source)
        layout.addWidget(self.files)
        layout.addLayout(actions_layout)

    def update_search_and_replace(self, *_):
        self.model.set_search_and_replace(
            self.search.text(), self.replace.text())

    def _call_open(self):
        if not self.model.session_data:
            return ScrollMessageBox('No data to open', 'Error').exec_()
        ebc.open_session_data(self.model.session_data)
        self.close()

    def _call_save_as(self):
        if not self.model.session_data:
            return ScrollMessageBox('No data to open', 'Error').exec_()
        ebc.save_as(self.model.session_data)
        self.close()

    def _call_save_as_and_open(self):
        if not self.model.session_data:
            return ScrollMessageBox('No data to open', 'Error').exec_()
        ebc.save_as(self.model.session_data)
        ebc.open_session_data(self.model.session_data)
        self.close()

    def show(self):
        super().show()
        self.model.set_session_data(None)
        self.file.clear()

    def look_up_in_alternate_source(self):
        directory = QtWidgets.QFileDialog.getExistingDirectory(
            self, 'Select directory')
        if not directory:
            return
        self.model.repath_missing_videos(directory)

    def select_session(self):
        self.file.clear()
        filepath, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, 'Select embarker session', filter=('*.embk'))
        if not filepath:
            return
        try:
            with open(filepath, 'rb') as f:
                data = msgpack.load(f)
        except BaseException:
            return ScrollMessageBox(
                'This is not a valid session file', 'Error').exec_()

        self.file.setText(filepath)
        self.model.set_session_data(data)
        self.update_search_and_replace()


class SessionFilesModel(QtCore.QAbstractListModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.session_data = None

    def set_session_data(self, data):
        self.layoutAboutToBeChanged.emit()
        self.session_data = data
        self.layoutChanged.emit()

    def repath_missing_videos(self, directory):
        self.layoutAboutToBeChanged.emit()
        for container in self.session_data['containers']:
            if os.path.exists(container[1]):
                continue
            new_path = f'{directory}/{os.path.basename(container[1])}'
            if os.path.exists(new_path):
                container[1] = new_path
        self.layoutChanged.emit()

    def set_search_and_replace(self, search, replace):
        if not all((search, replace)):
            return
        for container in self.session_data['containers']:
            if os.path.exists(container[1]):
                continue
            new_path = container[1].replace(search, replace)
            if os.path.exists(os.path.expandvars(new_path)):
                container[1] = new_path
        self.layoutChanged.emit()

    def rowCount(self, _):
        if self.session_data is None:
            return 0
        return len(self.session_data['containers'])

    def flags(self, _):
        return QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsEnabled

    def data(self, index, role=QtCore.Qt.UserRole):
        if not index.isValid():
            return

        fp =  self.session_data['containers'][index.row()][1]
        if role in (QtCore.Qt.DisplayRole, QtCore.Qt.EditRole):
            return fp

        if role == QtCore.Qt.BackgroundRole:
            exists = os.path.exists(os.path.expandvars(fp))
            color = 'green' if exists else 'red'
            color = QtGui.QColor(color)
            color.setAlpha(50)
            return color
