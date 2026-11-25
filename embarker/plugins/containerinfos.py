import os
from PySide6 import QtWidgets, QtCore
from embarker.api import EmbarkerDockWidget
import embarker.commands as ebc
from embarker.decoder import MultiContainer
from paintcanvas.widget import SliderSetValueAtClickPosition


PLUGIN_NAME = 'Container Infos'
__version__ = '1.0'
__author__ = 'David Williams'


class ContainerInfos(EmbarkerDockWidget):
    TITLE = 'Container'
    DOCK_AREA = QtCore.Qt.LeftDockWidgetArea
    OBJECT_NAME = 'Container-Infos'
    APPEARANCE_PRIORITY = 98
    VISIBLE_BY_DEFAULT = False
    ENABLE_DURING_PLAYBACK = True

    def __init__(self, parent=None):
        super().__init__(parent)

        self.fullpath = QtWidgets.QLineEdit()
        self.fullpath.setReadOnly(True)
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

        self.side_by_side = SideBySideOptions()

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
        form.addRow('Full path', self.fullpath)
        form.addRow('Directory', self.directory)
        form.addRow('Filename', self.filename)
        form.addRow('Length', self.length)
        form.addRow('Fps', self.fps)
        form.addRow('Codec', self.codec)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(form)
        layout.addWidget(self.side_by_side)
        layout.addWidget(self.metadata)
        layout.addStretch()

    def update_view(self):
        container = ebc.get_session().get_current_container()
        if not container:
            self.metadata.setRowCount(0)
            self.fullpath.setText('')
            self.directory.setText('')
            self.filename.setText('')
            self.length.setText('')
            self.fps.setText('')
            self.codec.setText('')
            return
        self.fullpath.setText(container.path)
        self.directory.setText(os.path.dirname(container.path))
        self.filename.setText(os.path.basename(container.path))
        self.length.setText(str(container.length))
        self.fps.setText(str(container.fps))
        self.codec.setText(str(container))
        self.side_by_side.set_container(container)

        self.metadata.setRowCount(0)
        self.metadata.setRowCount(len(container.metadata))
        for i, (key, value) in enumerate(sorted(container.metadata.items())):
            self.metadata.setItem(i, 0, QtWidgets.QTableWidgetItem(key))
            self.metadata.setItem(i, 1, QtWidgets.QTableWidgetItem(str(value)))
        self.metadata.resizeColumnsToContents()
        self.metadata.horizontalHeader().setStretchLastSection(True)


class SideBySideOptions(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setVisible(False)
        self.layouts = QtWidgets.QComboBox()
        self.layouts.addItems([
            'horizontal', 'vertical', 'grid', 'thumbnail'])
        self.layouts.currentIndexChanged.connect(self.update_container)

        self.max_pixels = QtWidgets.QSpinBox(
            minimum=1_000_000, maximum=2_073_600)
        self.max_pixels.valueChanged.connect(self.update_container)

        self.thumbnail_height_proportion = SliderSetValueAtClickPosition(
            QtCore.Qt.Horizontal)
        self.thumbnail_height_proportion.setMaximum(100)
        self.thumbnail_height_proportion.setMinimum(10)
        self.thumbnail_height_proportion.sliderReleased.connect(
            self.update_container)

        self.thumbnail_opacity = SliderSetValueAtClickPosition(
            QtCore.Qt.Horizontal)
        self.thumbnail_opacity.setMaximum(100)
        self.thumbnail_opacity.setMinimum(0)
        self.thumbnail_opacity.sliderReleased.connect(
            self.update_container)

        layout = QtWidgets.QFormLayout(self)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addRow('Layout', self.layouts)
        layout.addRow('Max pixels (resolution)', self.max_pixels)
        layout.addRow(
            'Thumbnail proportion', self.thumbnail_height_proportion)
        layout.addRow('Thumbnail opacity', self.thumbnail_opacity)
        self.update_ui_states()

    def set_container(self, container):
        if not isinstance(container, MultiContainer):
            self.setEnabled(False)
            self.setVisible(False)
            return
        self.setVisible(True)
        self.setEnabled(True)

        self.layouts.blockSignals(True)
        self.layouts.setCurrentText(container.layout)
        self.layouts.blockSignals(False)

        self.max_pixels.blockSignals(True)
        self.max_pixels.setValue(container.max_pixels)
        self.max_pixels.blockSignals(False)

        self.thumbnail_height_proportion.setValue(
            int(container.thumbnail_height_proportion * 100))
        self.thumbnail_opacity.setValue(int(container.thumbnail_opacity * 100))
        self.update_ui_states()

    def update_container(self):
        container = ebc.get_session().get_current_container()
        container.layout = self.layouts.currentText()
        container.max_pixels = self.max_pixels.value()
        container.thumbnail_height_proportion = (
            (self.thumbnail_height_proportion.value() / 100))
        container.thumbnail_opacity = (
            (self.thumbnail_opacity.value() / 100))
        ebc.get_session().clear_container_cache(container.id)
        # ebc.get_main_window().current_frame_changed()
        ebc.set_frame(ebc.get_frame())

    def update_ui_states(self):
        container = ebc.get_session().get_current_container()
        state = container.layout == 'thumbnail' if container else False
        self.thumbnail_opacity.setEnabled(state)
        self.thumbnail_height_proportion.setEnabled(state)
