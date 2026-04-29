import os
from embarker.pluginregistry import PluginRegistry
from PySide6 import QtWidgets, QtCore


class PluginManagerModel(QtCore.QAbstractTableModel):
    HEADERS = '', 'Name', 'Docks', 'Authors', 'Version', 'Path', 'Description'

    def __init__(self, plugin_registry: PluginRegistry, parent=None):
        super().__init__(parent)
        self.plugin_registry = plugin_registry
        self.plugin_registry.changed.connect(self.layoutChanged.emit)

    def rowCount(self, _):
        return len(self.plugin_registry.plugins_modules)

    def columnCount(self, _):
        return len(self.HEADERS)

    def headerData(self, section, orientation, role):
        if orientation == QtCore.Qt.Vertical or role != QtCore.Qt.DisplayRole:
            return
        return self.HEADERS[section]

    def flags(self, index):
        flags = QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable
        if index.column() == 0:
            flags |= QtCore.Qt.ItemIsUserCheckable
        return flags

    def setData(self, index, value, role):
        if role != QtCore.Qt.CheckStateRole:
            return

        r = index.row()
        module, _ = list(self.plugin_registry.plugins_modules.items())[r]
        if value == 2:
            self.plugin_registry.load_plugin_module(
                plugin_module_path=module,
                initialize_classes=True)
            return True
        if value == 0:
            self.plugin_registry.unload_plugin_module(module)
            return True
        return False

    def data(self, index, role):
        if not index.isValid():
            return

        r = index.row()
        module, data = list(self.plugin_registry.plugins_modules.items())[r]

        if role == QtCore.Qt.CheckStateRole:
            if self.HEADERS[index.column()] == '':
                return (
                    QtCore.Qt.Checked if data['loaded'] else
                    QtCore.Qt.Unchecked)

        if role != QtCore.Qt.DisplayRole:
            return

        if self.HEADERS[index.column()] == 'Name':
            return data['name']
        if self.HEADERS[index.column()] == 'Docks':
            return ',\n'.join([cls.__name__ for cls in data['classes']])
        if self.HEADERS[index.column()] == 'Path':
            return os.path.basename(module)
        if self.HEADERS[index.column()] == 'Description':
            return data['description']
        if self.HEADERS[index.column()] == 'Authors':
            return data['author']
        if self.HEADERS[index.column()] == 'Version':
            return data['version']


class PluginManager(QtWidgets.QWidget):
    def __init__(self, pluginmanager, parent=None):
        super().__init__(parent, QtCore.Qt.Tool)
        self.setWindowTitle('Plugin Manager')
        self.plugin_registry = pluginmanager

        self.table_model = PluginManagerModel(self.plugin_registry)
        self.table_view = QtWidgets.QTableView()
        self.table_view.setSelectionBehavior(
            QtWidgets.QAbstractItemView.SelectRows)
        # self.table_view.verticalHeader().hide()
        self.table_view.setAlternatingRowColors(True)
        self.table_view.setShowGrid(False)
        self.table_view.setModel(self.table_model)
        self.plugin_registry.changed.connect(self.adapt_size)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.table_view)

    def adapt_size(self):
        self.table_view.horizontalHeader().resizeSections(
            QtWidgets.QHeaderView.ResizeToContents)
        self.table_view.verticalHeader().resizeSections(
            QtWidgets.QHeaderView.ResizeToContents)

    def showEvent(self, event):
        super().showEvent(event)
        self.adapt_size()

    def sizeHint(self):
        return QtCore.QSize(1080, 600)