from PySide6 import QtWidgets, QtCore, QtGui
from paintcanvas.shapesettings import ColorButton


class WashSettings(QtWidgets.QWidget):
    edited = QtCore.Signal()

    def __init__(self, canvas, parent=None):
        super().__init__(parent=parent)
        self.canvas = canvas
        self.canvas.updated.connect(self.update)
        self.setMaximumHeight(30)
        # Washed out
        self._wash_opacity_ghost = None

        self.wash_color = ColorButton()
        self.wash_color.color = self.canvas.model.wash_color
        self.wash_color.edited.connect(self._wash_changed)
        self.wash_color.edited.connect(self.canvas.model.add_undo_state)
        self.wash_opacity = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.wash_opacity.valueChanged.connect(self._wash_changed)
        self.wash_opacity.sliderPressed.connect(self.start_slide)
        self.wash_opacity.sliderReleased.connect(self.end_slide)
        self.wash_opacity.setMinimum(0)
        self.wash_opacity.setValue(0)
        self.wash_opacity.setMaximum(255)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.wash_color)
        layout.addWidget(self.wash_opacity)

    def start_slide(self):
        self._wash_opacity_ghost = self.wash_opacity.value()

    def end_slide(self):
        if self._wash_opacity_ghost == self.wash_opacity.value():
            return
        self._wash_opacity_ghost = None
        self.canvas.model.add_undo_state()

    def _wash_changed(self, *_):
        self.canvas.model.wash_opacity = self.wash_opacity.value()
        self.canvas.model.wash_color = self.wash_color.color
        self.edited.emit()

    def update(self):
        super().update()
        self.wash_color.color = self.canvas.model.wash_color
        self.wash_opacity.blockSignals(True)
        self.wash_opacity.setValue(self.canvas.model.wash_opacity)
        self.wash_opacity.blockSignals(False)
