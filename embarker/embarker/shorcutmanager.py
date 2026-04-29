from operator import itemgetter
from PySide6 import QtWidgets, QtCore, QtGui
from embarker.actionregistry import ActionRegistry
from embarker import preferences


class ShortcutManager(QtWidgets.QWidget):
    def __init__(
            self,
            actionregistry: ActionRegistry,
            parent=None):
        super().__init__(parent, QtCore.Qt.Tool)
        self.setWindowTitle('Shortcuts Manager')
        self.actionregistry = actionregistry

        self.shortcut_model = ShortcutModel(actionregistry)
        self.shortcut_table = QtWidgets.QTableView()
        behavior = QtWidgets.QAbstractItemView.SelectRows
        self.shortcut_table.setSelectionBehavior(behavior)
        mode = QtWidgets.QAbstractItemView.SingleSelection
        self.shortcut_table.setSelectionMode(mode)
        mode = QtWidgets.QHeaderView.ResizeToContents
        self.shortcut_table.horizontalHeader().setSectionResizeMode(mode)
        self.shortcut_table.setModel(self.shortcut_model)
        self.shortcut_table.selectionModel().selectionChanged.connect(
            self.action_selected)
        self.shortcut_table.setShowGrid(False)
        self.shortcut_table.setSortingEnabled(True)
        self.shortcut_table.setAlternatingRowColors(True)
        self.shortcut_table.verticalHeader().hide()

        self.hotkey = HotkeyEditor()
        self.hotkey.hotkey_edited.connect(self.do_update_hotkey)

        self.clear_hotkey = QtWidgets.QPushButton('Clear')
        self.clear_hotkey.released.connect(self.do_clear_hotkey)
        self.reset_default = QtWidgets.QPushButton('Default')
        self.reset_default.released.connect(self.do_reset_hotkey)
        self.restore_default_config = QtWidgets.QPushButton('Restore all')
        self.restore_default_config.released.connect(self.do_restore_all)

        buttons = QtWidgets.QHBoxLayout()
        buttons.setContentsMargins(0, 0, 0, 0)
        buttons.addWidget(self.clear_hotkey)
        buttons.addWidget(self.reset_default)

        right = QtWidgets.QVBoxLayout()
        right.setContentsMargins(0, 0, 0, 0)
        right.addWidget(self.hotkey)
        right.addLayout(buttons)
        right.addStretch()
        right.addWidget(self.restore_default_config)

        layout = QtWidgets.QHBoxLayout(self)
        layout.addWidget(self.shortcut_table)
        layout.addLayout(right)

    def sizeHint(self):
        return QtCore.QSize(800, 600)

    def showEvent(self, event):
        super().showEvent(event)
        self.shortcut_model.layoutChanged.emit()
        self.shortcut_table.horizontalHeader().resizeSections(
            QtWidgets.QHeaderView.ResizeToContents)

    def get_selected_action_description(self):
        index = next(iter(
            self.shortcut_table.selectionModel().selectedIndexes()), None)
        if not index:
            return
        return self.shortcut_model.data(index, QtCore.Qt.UserRole)

    def action_selected(self, *_):
        description = self.get_selected_action_description()
        if description is None:
            self.hotkey.set_key_sequence('', '')
            return
        shortcuts = preferences.get('shortcuts', {})
        override = shortcuts.get(description['id'], ...)
        seq = override if override is not ... else description['shortcut']
        if isinstance(seq, QtGui.QKeySequence):
            seq = seq.toString()
        self.hotkey.set_key_sequence(description['text'], seq)
        self.hotkey.set_focus()

    def do_update_hotkey(self):
        description = self.get_selected_action_description()
        if description is None:
            return

        sequence_string = self.hotkey.key_sequence()
        all_shortcuts = {
            k: v.toString() if isinstance(v, QtGui.QKeySequence) else v
            for k, v in self.actionregistry.existing_shortcuts().items()}

        overrided_shortcuts = preferences.get('shortcuts', {})
        if sequence_string not in all_shortcuts.values():
            overrided_shortcuts[description['id']] = sequence_string
            preferences.set('shortcuts', overrided_shortcuts)
            self.shortcut_model.layoutChanged.emit()
            self.actionregistry.register_shortcuts()
            return

        ids = [k for k, v in all_shortcuts.items() if v == sequence_string]
        msg = QtWidgets.QMessageBox(self)
        msg.setWindowTitle('Warning')
        msg.setText(
            f'Sequences already assigned to: {ids}, '
            'woud you like to unassign it ?')
        msg.setIcon(QtWidgets.QMessageBox.Question)
        msg.setStandardButtons(
            QtWidgets.QMessageBox.Yes |
            QtWidgets.QMessageBox.No |
            QtWidgets.QMessageBox.Cancel)
        msg.setDefaultButton(QtWidgets.QMessageBox.Yes)

        msg.button(QtWidgets.QMessageBox.Yes).setText('Yes')
        msg.button(QtWidgets.QMessageBox.No).setText('Keep both')
        msg.button(QtWidgets.QMessageBox.Cancel).setText('Cancel')
        result = msg.exec_()

        if result == QtWidgets.QMessageBox.Cancel:
            return

        overrided_shortcuts[description['id']] = sequence_string
        if result == QtWidgets.QMessageBox.Yes:
            for id_ in ids:
                overrided_shortcuts[id_] = None
        preferences.set('shortcuts', overrided_shortcuts)
        self.shortcut_model.layoutChanged.emit()
        self.actionregistry.register_shortcuts()

    def do_clear_hotkey(self):
        description = self.get_selected_action_description()
        if description is None:
            return
        shortcuts = preferences.get('shortcuts', {})
        shortcuts[description['id']] = None
        preferences.set('shortcuts', shortcuts)
        self.shortcut_model.layoutChanged.emit()
        self.actionregistry.register_shortcuts()

    def do_reset_hotkey(self):
        description = self.get_selected_action_description()
        if description is None:
            return
        shortcuts = preferences.get('shortcuts', {})
        if description['id'] in shortcuts:
            del shortcuts[description['id']]
            preferences.set('shortcuts', shortcuts)
        self.shortcut_model.layoutChanged.emit()
        self.actionregistry.register_shortcuts()

    def do_restore_all(self):
        preferences.set('shortcuts', {})
        self.shortcut_model.layoutChanged.emit()
        self.actionregistry.register_shortcuts()


class ShortcutModel(QtCore.QAbstractTableModel):
    HEADERS = 'Action', 'Category', 'Shortcut'
    SORTERS = {
        'Action': itemgetter('text'),
        'Category': itemgetter('category')}

    def __init__(self, actionregistry, parent=None):
        super().__init__(parent)
        self.actionregistry = actionregistry
        self._reverse = True
        self._sorter = self.SORTERS[self.HEADERS[0]]

    def rowCount(self, _):
        return len(self.actionregistry.descriptions)

    def columnCount(self, _):
        return len(self.HEADERS)

    def sorted_actions(self):
        return sorted(
            self.actionregistry.descriptions.values(),
            key=self._sorter,
            reverse=self._reverse)

    def sort(self, section, order):
        header = self.HEADERS[section]
        sorter = self.SORTERS.get(header)
        if sorter is None:
            return
        self._reverse = order == QtCore.Qt.AscendingOrder
        self._sorter = sorter
        self.layoutChanged.emit()

    def flags(self, _):
        return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable

    def headerData(self, section, orientation, role):
        if orientation == QtCore.Qt.Vertical or role != QtCore.Qt.DisplayRole:
            return
        return self.HEADERS[section]

    def data(self, index, role):
        if not index.isValid():
            return

        description = self.sorted_actions()[index.row()]
        if role == QtCore.Qt.UserRole:
            return description

        if role == QtCore.Qt.TextAlignmentRole:
            if self.HEADERS[index.column()] != 'Action':
                return QtCore.Qt.AlignCenter

        if role != QtCore.Qt.DisplayRole:
            return

        if self.HEADERS[index.column()] == 'Action':
            return description['text']

        if self.HEADERS[index.column()] == 'Category':
            return description['category']

        if self.HEADERS[index.column()] == 'Shortcut':
            shortcuts = preferences.get('shortcuts', {})
            override = shortcuts.get(description['id'], ...)
            seq = override if override is not ... else description['shortcut']
            if isinstance(seq, QtGui.QKeySequence):
                seq = seq.toString()
            return seq or ''


class HotkeyEditor(QtWidgets.QWidget):
    hotkey_edited = QtCore.Signal()

    def __init__(self, parent=None):
        super(HotkeyEditor, self).__init__(parent)
        self.function_name = None
        self.function_name_label = QtWidgets.QLabel()
        self.alt = QtWidgets.QCheckBox('Alt')
        self.alt.released.connect(self.emit_hotkey_edited)
        self.ctrl = QtWidgets.QCheckBox('Ctrl')
        self.ctrl.released.connect(self.emit_hotkey_edited)
        self.shift = QtWidgets.QCheckBox('Shift')
        self.shift.released.connect(self.emit_hotkey_edited)
        self.string = KeyField()
        self.string.changed.connect(self.hotkey_edited.emit)

        modifiers = QtWidgets.QHBoxLayout()
        modifiers.addWidget(self.alt)
        modifiers.addWidget(self.ctrl)
        modifiers.addWidget(self.shift)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.function_name_label)
        layout.addLayout(modifiers)
        layout.addWidget(self.string)

    def set_focus(self):
        self.string.setFocus()

    def clear(self):
        self.function_name = None
        self.clear_values()
        self.function_name_label.setText('')

    def clear_values(self):
        self.ctrl.setChecked(False)
        self.alt.setChecked(False)
        self.shift.setChecked(False)
        self.string.setText('')

    def emit_hotkey_edited(self, *_):
        self.hotkey_edited.emit()

    def key_sequence(self):
        if not self.string.text():
            return None
        sequence = []
        if self.ctrl.isChecked():
            sequence.append('CTRL')
        if self.alt.isChecked():
            sequence.append('ALT')
        if self.shift.isChecked():
            sequence.append('SHIFT')
        sequence.append(self.string.text())
        return '+'.join(sequence)

    def set_key_sequence(self, function_name, key_sequence):
        self.function_name = function_name
        self.function_name_label.setText(function_name.title())
        if key_sequence is None:
            self.ctrl.setChecked(False)
            self.alt.setChecked(False)
            self.shift.setChecked(False)
            self.string.setText('')
            return
        self.ctrl.setChecked('ctrl' in key_sequence.lower())
        self.alt.setChecked('alt' in key_sequence.lower())
        self.shift.setChecked('shift' in key_sequence.lower())
        self.string.setText(key_sequence.split('+')[-1])


class KeyField(QtWidgets.QLineEdit):
    changed = QtCore.Signal()

    def __init__(self, parent=None):
        super(KeyField, self).__init__(parent)

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Shift:
            return
        text = QtGui.QKeySequence(event.key()).toString()
        if text == self.text():
            return
        self.setText(text)
        self.changed.emit()