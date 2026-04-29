from PySide6 import QtWidgets, QtCore, QtGui
from paintcanvas.layerstack import BLEND_MODE_NAMES
from paintcanvas.layerstackview import LayerStackView
from paintcanvas.shapesettings import ColorButton


class LayerView(QtWidgets.QWidget):
    edited = QtCore.Signal()

    def __init__(self, canvas, parent=None):
        super().__init__(parent=parent)
        self.canvas = canvas
        self.canvas.updated.connect(self.update)
        self.layerstackview = LayerStackView(self.canvas)
        self.layerstackview.current_changed.connect(self.sync_view)
        # Layer Toolbar
        self.plus = QtGui.QAction(u'\u2795', self)
        self.plus.triggered.connect(self.layer_added)
        self.minus = QtGui.QAction('➖', self)
        self.minus.triggered.connect(self.remove_current_layer)
        self.duplicate = QtGui.QAction('⧉', self)
        self.duplicate.triggered.connect(self.duplicate_layer)
        self.blend_modes = QtWidgets.QComboBox()
        self.blend_modes.currentIndexChanged.connect(self.change_blend_mode)
        self.blend_modes.addItems(sorted(list(BLEND_MODE_NAMES.values())))
        spacer = QtWidgets.QWidget()
        spacer.setSizePolicy(*[QtWidgets.QSizePolicy.Expanding] * 2)
        self.toolbar = QtWidgets.QToolBar()
        self.toolbar.addAction(self.plus)
        self.toolbar.addAction(self.minus)
        self.toolbar.addAction(self.duplicate)
        self.toolbar.addWidget(spacer)
        self.toolbar.addWidget(self.blend_modes)

        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMinimumHeight(150)
        scroll.setStyleSheet('background-color: rgba(0, 0, 0, 50);')
        scroll.setWidget(self.layerstackview)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(scroll)
        layout.addWidget(self.toolbar)
        layout.addStretch()
        self.sync_view()

    def sync_view(self):
        self.blend_modes.blockSignals(True)
        self.blend_modes.setCurrentText(
            self.canvas.model.layerstack.current_blend_mode_name)
        self.blend_modes.blockSignals(False)

    def layer_added(self):
        self.canvas.model.add_layer()
        self.layerstackview.update_size()
        self.layerstackview.update()

    def duplicate_layer(self):
        self.canvas.model.duplicate_layer()
        self.layerstackview.update_size()
        self.layerstackview.update()

    def call_edited(self):
        self.layerstackview.update()
        self.edited.emit()

    def change_blend_mode(self):
        blend_mode = self.blend_modes.currentText()
        self.canvas.model.set_current_blend_mode_name(blend_mode)
        self.edited.emit()

    def remove_current_layer(self):
        index = self.canvas.model.layerstack.current_index
        self.canvas.model.layerstack.delete(index)
        self.canvas.model.add_undo_state()
        self.layerstackview.update_size()
        self.layerstackview.update()
        self.edited.emit()
