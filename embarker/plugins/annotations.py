import os
from PySide6 import QtWidgets, QtCore

from embarker.api import EmbarkerDockWidget
import embarker.commands as ebc


class DynamicEllide(QtWidgets.QStyledItemDelegate):
    def paint(self, painter, option, index):
        opt = option

        if option.state & QtWidgets.QStyle.State_Selected:
            opt.textElideMode = QtCore.Qt.ElideNone
        else:
            opt.textElideMode = QtCore.Qt.ElideRight

        super().paint(painter, opt, index)


PLUGIN_NAME = 'Annotation'
__version__ = '1.0'
__author__ = 'David Williams'


class AnnotationsTable(EmbarkerDockWidget):
    TITLE = 'Annotations'
    OBJECT_NAME = 'AnnotationsCommentsDock'
    APPEARANCE_PRIORITY = 99
    DOCK_AREA = QtCore.Qt.LeftDockWidgetArea
    VISIBLE_BY_DEFAULT = True
    ENABLE_DURING_PLAYBACK = False

    def __init__(self, parent=None):
        super().__init__(parent)
        self.model = AnnotationsListModel()
        self.delegate = DynamicEllide()
        self.tableview = QtWidgets.QTableView()
        self.tableview.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.tableview.customContextMenuRequested.connect(self.tableview_menu)
        self.tableview.setItemDelegateForColumn(1, self.delegate)
        self.tableview.setSelectionBehavior(
            QtWidgets.QAbstractItemView.SelectRows)
        self.tableview.setSelectionMode(
            QtWidgets.QAbstractItemView.SingleSelection)
        self.tableview.setModel(self.model)
        self.tableview.selectionModel().selectionChanged.connect(
            self.selection_changed)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.tableview)

    def tableview_menu(self, point):
        menu = QtWidgets.QMenu()
        menu.addAction('Invert selection')
        menu.addAction('Select all')
        menu.addAction('Deselect all')

        point = self.tableview.mapToGlobal(point)
        action = menu.exec_(point)
        if not action:
            return

        if action.text() == 'Invert selection':
            self.model.invert_selection()
        elif action.text() == 'Select all':
            self.model.select_all(True)
        else:
            self.model.select_all(False)

    def update_view(self):
        self.tableview.horizontalHeader().resizeSections(
            QtWidgets.QHeaderView.ResizeToContents)
        self.tableview.horizontalHeader().setStretchLastSection(True)
        self.model.layoutChanged.emit()

        container = ebc.get_session().get_current_container()
        if not container:
            return
        frame = ebc.get_session().playlist.frame
        frame = ebc.get_session().playlist.frames_frames[frame]
        annotation_indexes = list(ebc.get_session().annotations)
        if (container.id, frame) in annotation_indexes:
            row = annotation_indexes.index((container.id, frame))
            self.tableview.selectionModel().blockSignals(True)
            self.tableview.selectRow(row)
            self.tableview.selectionModel().blockSignals(False)
            for r in range(self.model.rowCount()):
                if row == r:
                    self.tableview.resizeRowToContents(r)
                    continue
                self.tableview.setRowHeight(r, 25)

    def selection_changed(self, selected, deselected):
        indexes = self.tableview.selectionModel().selectedIndexes()
        index = next(iter(indexes), None)
        if not index:
            return
        container_id, relative_frame = self.model.data(index, QtCore.Qt.UserRole)
        first_frame = ebc.get_session().playlist.first_frames[container_id]
        ebc.set_frame(first_frame + relative_frame)

        for idx in deselected.indexes():
            self.tableview.setRowHeight(idx.row(), 25)

        for idx in selected.indexes():
            self.tableview.resizeRowToContents(idx.row())


class AnnotationsListModel(QtCore.QAbstractTableModel):
    HEADERS = '', 'Frame', 'Comment'

    def columnCount(self, *_):
        return len(self.HEADERS)

    def rowCount(self, *_):
        container = ebc.get_session().get_current_container()
        if container is None:
            return 0
        return len(ebc.get_session().get_container_annotations(container.id, True))

    def flags(self, index):
        if index.column() == 0:
            container = ebc.get_session().get_current_container()
            annotations = ebc.get_session().get_container_annotations(container.id, True)
            if index.row() > len(annotations) - 1:
                return QtCore.Qt.ItemIsEditable
            container_id, relative_frame = sorted(annotations)[index.row()]
            if (container_id, relative_frame) in ebc.get_session().annotations:
                return (
                    QtCore.Qt.ItemIsSelectable |
                    QtCore.Qt.ItemIsEnabled |
                    QtCore.Qt.ItemIsUserCheckable |
                    QtCore.Qt.ItemIsEditable)
            return QtCore.Qt.ItemIsSelectable
        return (
            QtCore.Qt.ItemIsSelectable |
            QtCore.Qt.ItemIsEnabled |
            QtCore.Qt.ItemIsEditable)

    def headerData(self, section, orientation, role):
        if orientation != QtCore.Qt.Vertical and role == QtCore.Qt.DisplayRole:
            return self.HEADERS[section]

    def invert_selection(self):
        self.layoutAboutToBeChanged.emit()
        container = ebc.get_session().get_current_container()
        annotations = ebc.get_session().get_container_annotations(container.id)
        for model in annotations.values():
            state = not model.metadata.get('exportable', True)
            model.metadata['exportable'] = state
        self.layoutChanged.emit()

    def select_all(self, state=True):
        self.layoutAboutToBeChanged.emit()
        container = ebc.get_session().get_current_container()
        annotations = ebc.get_session().get_container_annotations(container.id)
        for model in annotations.values():
            model.metadata['exportable'] = state
        self.layoutChanged.emit()

    def setData(self, index, value, role):
        if role == QtCore.Qt.CheckStateRole and index.column() == 0:
            container = ebc.get_session().get_current_container()
            annotations = ebc.get_session().get_container_annotations(
                container.id, True)
            container_id, relative_frame = sorted(annotations)[index.row()]
            model = ebc.get_session().annotations[(container_id, relative_frame)]
            model.metadata['exportable'] = bool(value)
            return True

        if role != QtCore.Qt.EditRole:
            return False

        if self.HEADERS[index.column()] == 'Frame':
            try:
                container = ebc.get_session().get_current_container()
                annotations = ebc.get_session().get_container_annotations(
                    container.id, True)
                container_id, relative_frame = sorted(annotations)[index.row()]
                frame = int(value)
                model = ebc.get_session().annotations[(container_id, relative_frame)]
                del ebc.get_session().annotations[(container_id, relative_frame)]
                ebc.get_session().annotations[container_id, frame] = model
                start = ebc.get_session().playlist.first_frames[container_id]
                ebc.set_frame(start + frame)
            except ValueError:
                return False
            return True
        elif self.HEADERS[index.column()] == 'Comment':
            value = '' if value == '(no text)' else value
            ebc.set_canvas_comment(str(value))
            return True
        return False

    def data(self, index, role):
        if not index.isValid():
            return

        container = ebc.get_session().get_current_container()
        annotations = ebc.get_session().get_container_annotations(container.id, True)
        container_id, relative_frame = sorted(annotations)[index.row()]

        if role == QtCore.Qt.UserRole:
            return container_id, relative_frame

        if role == QtCore.Qt.CheckStateRole:
            if index.column() != 0:
                return
            id_ = (container_id, relative_frame)
            model = ebc.get_session().annotations.get(id_)
            if model is None:
                return QtCore.Qt.Unchecked
            return (
                QtCore.Qt.Checked if model.metadata.get('exportable', True)
                else QtCore.Qt.Unchecked)

        if role in (QtCore.Qt.DisplayRole, QtCore.Qt.EditRole):
            if index.column() == 1:
                return str(relative_frame)
            if index.column() == 2:
                id_ = (container_id, relative_frame)
                model = ebc.get_session().annotations.get(id_)
                if model is None:
                    return '(no text)'
                return model.comment or '(no text)'
