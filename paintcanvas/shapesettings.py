
from PySide6 import QtWidgets, QtCore, QtGui
from paintcanvas.dialog import ColorSelection
from paintcanvas.qtutils import COLORS
from paintcanvas.tools import (
    DrawTool, SmoothDrawTool, ArrowTool, RectangleTool, CircleTool, LineTool,
    EraserTool)
from paintcanvas.widget import SliderSetValueAtClickPosition


class ColorButton(QtWidgets.QAbstractButton):
    edited = QtCore.Signal()

    def __init__(self, color=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setFocusPolicy(QtCore.Qt.NoFocus)
        self.setMouseTracking(True)
        self.color = color or COLORS[0]
        self.released.connect(self.change_color)

    def change_color(self):
        dialog = ColorSelection(self.color)
        dialog.move(self.mapToGlobal(self.rect().bottomLeft()))
        result = dialog.exec_()
        if result != QtWidgets.QDialog.Accepted:
            return
        self.color = dialog.color
        self.update()
        self.edited.emit()

    def mouseMouseEvent(self, _):
        self.update()

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        cursor = self.mapFromGlobal(QtGui.QCursor.pos())
        hovered = event.rect().contains(cursor)
        color = QtCore.Qt.transparent if hovered else QtCore.Qt.black
        painter.setPen(color)
        painter.setBrush(QtGui.QColor(self.color))
        painter.drawRect(self.rect())

    def sizeHint(self):
        return QtCore.QSize(25, 25)

    def get_value(self):
        return self.color

    def set_value(self, color):
        self.color = color
        self.update()


class Slider(QtWidgets.QWidget):
    MIN = 0
    MAX = 255
    edited = QtCore.Signal()
    def __init__(self, parent=None):
        super().__init__(parent)
        self.slider = SliderSetValueAtClickPosition()
        self.slider.setOrientation(QtCore.Qt.Horizontal)
        self.slider.setMinimum(self.MIN)
        self.slider.setMaximum(self.MAX)
        self.slider.valueChanged.connect(self._set_value_from_slider)
        self.value_edit = QtWidgets.QSpinBox()
        self.value_edit.setMinimum(self.MIN)
        self.value_edit.setMaximum(self.MAX)
        self.value_edit.valueChanged.connect(self._set_value_from_edit)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.slider)
        layout.addWidget(self.value_edit)

    def _internal_value_change(self, value):
        self.set_value(value)
        self.edited.emit()

    def value(self):
        return self.slider.value()

    def set_value(self, value):
        self.slider.blockSignals(True)
        self.slider.setValue(value)
        self.slider.blockSignals(False)
        self.value_edit.blockSignals(True)
        self.value_edit.setValue(value)
        self.value_edit.blockSignals(False)

    def _set_value_from_edit(self, value):
        self.slider.blockSignals(True)
        self.slider.setValue(value)
        self.slider.blockSignals(False)
        self.edited.emit()

    def _set_value_from_slider(self, value):
        self.value_edit.blockSignals(True)
        self.value_edit.setValue(value)
        self.value_edit.blockSignals(False)
        self.edited.emit()

    def get_value(self):
        return self.slider.value()


class BrushSize(Slider):
    MIN = 1
    MAX = 100

    def get_value(self):
        value = self.value()
        if value <= 50:
            # Linear interpolation from [1, 50] to [1, 15]
            output = 1 + ((value - 1) / 49) * 14
        elif value <= 75:
            # Linear interpolation from [51, 75] to [16, 40]
            output = 16 + ((value - 51) / 24) * 24
        else:
            # Linear interpolation from [76, 100] to [41, 100]
            output = 41 + ((value - 76) / 24) * 59
        # print(value, output)
        return output

    def set_value(self, value):
        self.blockSignals(True)
        if value <= 15:
            # Inverse of [1, 50] -> [1, 15]
            value = 1 + ((value - 1) / 14) * 49
        elif value <= 40:
            # Inverse of [51, 75] -> [16, 40]
            value = 51 + ((value - 16) / 24) * 24
        else:
            # Inverse of [76, 100] -> [41, 100]
            value = 76 + ((value - 41) / 59) * 24
        super().set_value(value)
        self.blockSignals(False)


class Size(Slider):
    MIN = 1
    MAX = 100


class Opacity(Slider):
    MIN = 0
    MAX = 255


class BufferSize(Opacity):
    MIN = 1
    MAX = 50


class Alignment(QtWidgets.QComboBox):
    edited = QtCore.Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.addItems([
            'Top left', 'Top right', 'Top center', 'Center left', 'Center',
            'Center right', 'Bottom left', 'Bottom center', 'Bottom right'])
        self.currentIndexChanged.connect(lambda: self.edited.emit())

    def set_value(self, index):
        self.setCurrentIndex(index)

    def get_value(self):
        return self.currentIndex()


class TextEdit(QtWidgets.QTextEdit):
    edited = QtCore.Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.textChanged.connect(self.edited.emit)

    def get_value(self):
        return self.toPlainText()

    def set_value(self, text):
        return self.setPlainText(text)


class CheckBox(QtWidgets.QCheckBox):
    edited = QtCore.Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.released.connect(self.edited.emit)

    def get_value(self):
        return self.isChecked()

    def set_value(self, value):
        return self.setChecked(value)


SETTINGS_WIDGETS = {
    'text': ('Text', TextEdit),
    'color': ('Color', ColorButton),
    'bgcolor': ('Background color', ColorButton),
    'filled': ('Filled', CheckBox),
    'text_size': ('Text size', Size),
    'alignment': ('Alignment', Alignment),
    'bgopacity': ('Background opacity', Opacity),
    'linewidth': ('Line width', BrushSize),
    'tailwidth': ('Tail width', Size),
    'headsize': ('Header size', Size),
    'buffer_lenght': ('Buffer', BufferSize)
}


SHAPE_ATTRIBUTES_BY_TYPES = {
    'arrow': ['color', 'headsize', 'linewidth'],
    'circle': ['color', 'bgcolor', 'filled', 'bgopacity', 'linewidth'],
    'bitmap': [],
    'line': ['color', 'linewidth'],
    'rectangle': ['color', 'bgcolor', 'filled', 'bgopacity', 'linewidth'],
    'stroke': ['color'],
    'p-stroke': ['color', 'bgopacity'],
    'text': [
        'color', 'bgcolor', 'filled', 'bgopacity',
        'text_size', 'alignment', 'text'],
}
TOOL_ATTRIBUTES_BY_TOOL = {
    ArrowTool: ['color', 'headsize', 'linewidth'],
    EraserTool: ['linewidth'],
    CircleTool: ['color', 'bgcolor', 'filled', 'bgopacity', 'linewidth'],
    DrawTool: ['color', 'linewidth', 'bgopacity'],
    LineTool: ['color', 'linewidth'],
    RectangleTool: ['color', 'bgcolor', 'filled', 'bgopacity', 'linewidth'],
    SmoothDrawTool: ['color', 'linewidth', 'bgopacity', 'buffer_lenght'],
}


class ToolsSettingWidget(QtWidgets.QWidget):

    def __init__(self, canvas, parent=None):
        super().__init__(parent)
        self.canvas = canvas
        self.widgets = {
            cls: ToolSettings(attributes)
            for cls, attributes in TOOL_ATTRIBUTES_BY_TOOL.items()}
        self.no_tool_label = QtWidgets.QLabel('No options')

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.no_tool_label)
        for cls, widget in self.widgets.items():
            widget.edited.connect(self.tool_edited)
            widget.setVisible(False)
            widget.init_tool(cls(self.canvas))
            layout.addWidget(widget)

    def set_tool(self, tool):
        tool_cls = type(tool)
        attributes = TOOL_ATTRIBUTES_BY_TOOL.get(tool_cls)
        self.no_tool_label.setVisible(not bool(attributes))
        for cls, widget in self.widgets.items():
            widget.setVisible(cls is tool_cls)
            if cls is tool_cls:
                widget.init_tool(self.canvas.tool)

    def sync_tools(self, tools):
        for tool in tools:
            attributes = TOOL_ATTRIBUTES_BY_TOOL.get(tool.__class__)
            if not attributes:
                continue
            widget = self.widgets.get(tool.__class__)
            if widget:
                widget.init_tool(tool)

    def tool_edited(self):
        for key, value in self.settings().items():
            setattr(self.canvas.tool, key, value)

    def settings(self):
        for widget in self.widgets.values():
            if widget.isVisible():
                return widget.settings()

    def serialize(self):
        return {
            cls.__name__: widget.settings()
            for cls, widget in self.widgets.items()}

    def deserialize(self, settings):
        for cls, widget in self.widgets.items():
            data = settings.get(cls.__name__, {})
            for attribute, value in data.items():
                setattr(widget, attribute, value)


class ShapeSettingsWidget(QtWidgets.QWidget):

    def __init__(self, canvas, parent=None):
        super().__init__(parent)
        self.canvas = canvas
        self.canvas.selection_changed.connect(self.selection_changed)
        self.widgets = {
            shape_type: ShapeSettings(attributes)
            for shape_type, attributes in SHAPE_ATTRIBUTES_BY_TYPES.items()}
        self.no_shape_label = QtWidgets.QLabel('No shape selected')

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.no_shape_label)
        for widget in self.widgets.values():
            widget.edited.connect(self.shape_edited)
            widget.setVisible(False)
            layout.addWidget(widget)
        layout.addStretch()

    def shape_edited(self):
        for key, value in self.settings().items():
            setattr(self.canvas.selection.element, key, value)
        self.canvas.updated.emit()

    def selection_changed(self):
        shape = self.canvas.selection.element
        self.no_shape_label.setVisible(shape is None)
        for shape_type, widget in self.widgets.items():
            state = (
                bool(shape) and
                not isinstance(shape, QtCore.QPointF) and
                shape.TYPE == shape_type)
            widget.setVisible(state)
            if state:
                widget.set_settings(shape.serialize())

    def settings(self):
        for widget in self.widgets.values():
            if widget.isVisible():
                return widget.settings()


class ShapeSettings(QtWidgets.QWidget):
    edited = QtCore.Signal()

    def __init__(self, attributes, parent=None):
        super().__init__(parent)
        self.editors = {}

        self.current_form = QtWidgets.QFormLayout()
        self.current_form.setSpacing(0)
        for attribute in attributes:
            title, cls = SETTINGS_WIDGETS[attribute]
            widget = cls(parent=self)
            widget.edited.connect(self.edited.emit)
            self.add_row(attribute, title, widget)
        self.layout = QtWidgets.QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.addLayout(self.current_form)

    def adjust_form_label_size(self):
        margins = QtWidgets.QLabel().contentsMargins()
        margins.setRight(8)
        alignment = QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
        for label in self.findChildren(QtWidgets.QLabel):
            if isinstance(label, QtWidgets.QLabel):
                label.setAlignment(alignment)
                label.setContentsMargins(margins)
                label.setFixedWidth(100)

    def settings(self):
        return {a: w.get_value() for a, w in self.editors.items()}

    def set_settings(self, settings: dict):
        attributes = SHAPE_ATTRIBUTES_BY_TYPES[settings.get('type')]
        for attribute in attributes:
            value = settings[attribute]
            self.editors[attribute].set_value(value)

    def add_row(self, attribute, name, widget):
        self.current_form.addRow(f'  {name}  ', widget)
        self.editors[attribute] = widget

    def block_signals(self, state):
        for editor in self.editors.values():
            editor.blockSignals(state)


class ToolSettings(ShapeSettings):

    def init_tool(self, tool):
        attributes = TOOL_ATTRIBUTES_BY_TOOL.get(type(tool), [])
        for attribute in attributes:
            value = getattr(tool, attribute)
            self.editors[attribute].set_value(value)
