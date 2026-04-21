import os
import time
from functools import partial
from PySide6 import QtCore, QtWidgets, QtGui

from paintcanvas.geometry import get_global_rect
from viewportmapper import ViewportMapper
from paintcanvas.draw import draw_onion_skin, draw_layer, draw_selection
from paintcanvas.navigator import Navigator
from paintcanvas.layersview import LayerView
from paintcanvas.model import CanvasModel
from paintcanvas.proceduralstroke import ProceduralStrokePoint
from paintcanvas.qtutils import icon
from paintcanvas.selection import Selection
from paintcanvas.shapes import PStroke
from paintcanvas.shapesettings import ShapeSettingsWidget, ToolsSettingWidget
from paintcanvas.tools import TOOLS
from paintcanvas.tools.eraser import erase_on_layer
from paintcanvas.washsettings import WashSettings
from paintcanvas.zoomlabel import ZoomLabel

SUPPORTED_IMG_EXT = '.png', '.jpg', '.bmp', '.jpeg', '.webp'


def disable_if_model_locked(method):
    def decorator(self, *args, **kwargs):
        if self.model.locked:
            return
        return method(self, *args, **kwargs)
    return decorator


class Canvas(QtWidgets.QWidget):
    scrub = QtCore.Signal(int)
    updated = QtCore.Signal()
    selection_changed = QtCore.Signal()
    panzoom_changed = QtCore.Signal()
    size_changed = QtCore.Signal()
    layer_added = QtCore.Signal()

    def __init__(self, model: CanvasModel, parent=None):
        super().__init__(parent)
        self.mute = False
        self.onionskin: list[tuple[QtGui.QPixmap, float]] = []
        self.navigator = Navigator()
        self.setMouseTracking(True)
        self.setTabletTracking(True)
        self.setAcceptDrops(True)
        self.shape_settings_widget = None
        self.tool_settings_widget = None

        self.last_cursor_update_time = 0
        self.last_update_call_time = time.time()
        self.captime = .1
        self.model: CanvasModel = model
        self.tool = None
        self.tools = []

        self.timer = QtCore.QTimer(self)
        self.timer.start(300)
        self.timer.timeout.connect(self.update)

        self.mouse_tracker = QtCore.QTimer(self)
        self.mouse_tracker.timeout.connect(self._update_tablet_flag)
        self.mouse_tracker.start(15)
        self.installEventFilter(self)


    def _update_tablet_flag(self):
        global_pos = QtGui.QCursor.pos()
        local_pos = self.mapFromGlobal(global_pos)
        inside = self.rect().contains(local_pos)

        current_flag = QtCore.QCoreApplication.testAttribute(
            QtCore.Qt.AA_SynthesizeMouseForUnhandledTabletEvents)

        if inside and current_flag:
            QtCore.QCoreApplication.setAttribute(
                QtCore.Qt.AA_SynthesizeMouseForUnhandledTabletEvents, False)
        elif not inside and not current_flag:
            QtCore.QCoreApplication.setAttribute(
                QtCore.Qt.AA_SynthesizeMouseForUnhandledTabletEvents, True)

    # def eventFilter(self, object, event):
    #     if event.type() == QtGui.QTabletEvent.TabletMove:
    #         import time
    #         print('move', time.time())
    #         event.ignore()
    #         return False
    #     return super().eventFilter(object, event)

    @property
    def selection(self):
        return self.model.selection

    def get_layer_view(self):
        return LayerView(self)

    def get_wash_settings_widget(self):
        return WashSettings(self)

    def get_shape_settings_widget(self):
        if self.shape_settings_widget is None:
            self.shape_settings_widget = ShapeSettingsWidget(self)
        return self.shape_settings_widget

    def get_tool_settings_widget(self):
        if self.tool_settings_widget is None:
            self.tool_settings_widget = ToolsSettingWidget(self)
        return self.tool_settings_widget

    def get_tool_actions(self):
        actions = []
        for tool in TOOLS:
            tool_instance = tool['tool'](canvas=self)
            self.tools.append(tool_instance)
            actions.append(
                {
                    'id': f'Canvas>{tool["name"]}',
                    'text': tool['name'],
                    'category': 'Tool',
                    'icon': icon(tool['icon']),
                    'group': 'Tool',
                    'method': partial(self.set_tool, tool_instance),
                    'checkable': True,
                    'shortcut': (
                        QtGui.QKeySequence(tool['shortcut'])
                        if tool['shortcut'] else None),
                },
            )
        return actions

    def get_canvas_actions(self):
        return [
            {
                'id': 'Canvas>DeleteSelection',
                'text': 'Delete selection',
                'category': 'Canvas>Global',
                'icon': None,
                'group': None,
                'method': self.delete_selection,
                'checkable': False,
                'shortcut': QtGui.QKeySequence(QtCore.Qt.Key.Key_Delete),
            },
            {
                'id': 'Canvas>ClearSelection',
                'text': 'Clear selection',
                'category': 'Canvas>Global',
                'icon': None,
                'group': None,
                'method': self.clear_selection,
                'checkable': False,
                'shortcut': QtGui.QKeySequence('CTRL+D'),
            },
            {
                'id': 'Canvas>Undo',
                'text': 'Undo',
                'category': 'Canvas>Global',
                'icon': None,
                'group': None,
                'method': self.undo,
                'checkable': False,
                'shortcut': QtGui.QKeySequence('CTRL+Z'),
            },
            {
                'id': 'Canvas>Redo',
                'text': 'Redo',
                'category': 'Canvas>Global',
                'icon': None,
                'group': None,
                'method': self.redo,
                'checkable': False,
                'shortcut': QtGui.QKeySequence('CTRL+Y'),
            },
            {
                'id': 'Canvas>Duplicate',
                'text': 'Duplicate selection',
                'category': 'Canvas>Global',
                'icon': None,
                'group': None,
                'method': self.duplicate_selection,
                'checkable': False,
                'shortcut': QtGui.QKeySequence('CTRL+SHIFT+D'),
            },
        ]

    def clear_selection(self):
        self.selection.clear()
        self.update()

    def duplicate_selection(self):
        self.model.duplicate_selection()

    def undo(self):
        self.model.undo()

    def redo(self):
        self.model.redo()

    def get_zoom_label_widget(self):
        return ZoomLabel(self)

    def set_model(self, model):
        self.model = model
        size = model.baseimage.size()
        self.model.viewportmapper.view_size = QtCore.QSize(size)
        self.update()

    @disable_if_model_locked
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            return event.accept()

    @disable_if_model_locked
    def dropEvent(self, event):
        paths = [
            url.toLocalFile()
            for url in event.mimeData().urls()]
        paths = [
            p for p in paths if
            os.path.splitext(p)[-1].lower() in SUPPORTED_IMG_EXT]
        for path in paths:
            self.model.add_layer_image(path)
        self.update()
        self.updated.emit()

    def sizeHint(self):
        if not self.model.baseimage:
            return QtCore.QSize(300, 300)
        return self.model.baseimage.size()

    def resizeEvent(self, event):
        vpm = self.model.viewportmapper
        vpm.view_size = event.size()
        width_scale = event.size().width() / event.oldSize().width()
        height_scale = event.size().width() / event.oldSize().width()
        vpm.origin.setX(vpm.origin.x() * width_scale)
        vpm.origin.setY(vpm.origin.y() * height_scale)
        self.size_changed.emit()
        self.update()

    def reset(self):
        if not self.model.baseimage:
            return
        self.model.viewportmapper.view_size = self.size()
        rect = get_global_rect(
            self.model.baseimage,
            self.model.imagestack,
            self.model.imagestack_layout)
        self.model.viewportmapper.focus(rect)
        self.panzoom_changed.emit()
        self.update()

    def enterEvent(self, event):
        self.update_cursor()
        super().enterEvent(event)

    def leaveEvent(self, event):
        while QtWidgets.QApplication.overrideCursor():
            QtWidgets.QApplication.restoreOverrideCursor()

    def mouseMoveEvent(self, event):
        if self.mute:
            self.update_cursor()
            return
        self.tool.mouseMoveEvent(event)
        self.update_cursor()
        self.update()

    def mousePressEvent(self, event):
        if self.mute:
            return
        self.setFocus(QtCore.Qt.MouseFocusReason)
        self.navigator.update(event, pressed=True)
        result = self.tool.mousePressEvent(event)
        self.update_cursor()
        if result:
            self.update()

    def mouseReleaseEvent(self, event):
        self.navigator.update(event, pressed=False)
        result = self.tool.mouseReleaseEvent(event)
        if result is True and self.model.layerstack.current is not None:
            self.model.add_undo_state()
            self.updated.emit()
        self.update_cursor()
        self.update()

    def keyPressEvent(self, event):
        if event.isAutoRepeat() or self.mute:
            return
        self.navigator.update(event, pressed=True)
        self.tool.keyPressEvent(event)
        self.update_cursor()
        self.update()

    def keyReleaseEvent(self, event):
        if event.isAutoRepeat() or self.mute:
            return
        self.navigator.update(event, pressed=False)
        self.tool.keyReleaseEvent(event)
        self.update_cursor()
        self.update()

    def tabletEvent(self, event):
        if self.mute:
            return
        if event.type() == QtGui.QTabletEvent.TabletPress:
            self.tool.mousePressEvent(event)
            self.timer.setInterval(15)
            event.accept()
            return
        if event.type() == QtGui.QTabletEvent.TabletRelease:
            result = self.tool.mouseReleaseEvent(event)
            self.timer.setInterval(300)
            event.accept()
            if result is True and self.model.layerstack.current is not None:
                self.model.add_undo_state()
                self.updated.emit()
            self._update_tablet_flag()
            return
        self.tool.tabletMoveEvent(event)
        self.update()
        self.update_cursor()

    def wheelEvent(self, event):
        self.tool.wheelEvent(event)
        self.update()

    def showEvent(self, event):
        self.model.viewportmapper.view_size = self.size()
        return super().showEvent(event)

    def set_zoom(self, factor):
        self.model.viewportmapper.set_zoom_with_pivot(
            factor,
            self.mapFromGlobal(QtGui.QCursor.pos()))

    @disable_if_model_locked
    def set_tool(self, tool):
        if self.tool is not None and self.tool.is_dirty:
            self.model.add_undo_state()
        self.tool = tool
        if self.tool_settings_widget:
            self.tool_settings_widget.set_tool(tool)
        self.update_cursor()
        self.update()

    def update_cursor(self):
        # Thick cursor update to avoid tablet flood
        if self.last_cursor_update_time:
            if time.time() - self.last_cursor_update_time < 0.025:
                return
        self.last_cursor_update_time = time.time()
        if not self.tool.window_cursor_visible():
            override = QtCore.Qt.BlankCursor
        else:
            override = self.tool.window_cursor_override()

        override = override or QtCore.Qt.ArrowCursor
        if self.mute:
            override = QtCore.Qt.ForbiddenCursor
        current_override = QtWidgets.QApplication.overrideCursor()

        if not current_override:
            QtWidgets.QApplication.setOverrideCursor(override)
            return

        if current_override and current_override.shape() != override:
            # Need to restore override because overrides can be nested.
            QtWidgets.QApplication.restoreOverrideCursor()
            QtWidgets.QApplication.setOverrideCursor(override)

    def render(
            self,
            viewportmapper: ViewportMapper,
            painter: QtGui.QPainter = None,
            model: CanvasModel = None):
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        for layer, _, blend_mode, _, visible, opacity in model.layerstack:
            if not visible:
                continue
            draw_layer(
                painter, layer, blend_mode, opacity, viewportmapper)

    def paintEvent(self, _):
        if self.mute is True:
            return
        painter = QtGui.QPainter(self)
        if not painter.isActive():
            return
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        if self.model.wash_opacity:
            painter.setPen(QtCore.Qt.NoPen)
            color = QtGui.QColor(self.model.wash_color)
            color.setAlpha(self.model.wash_opacity)
            painter.setBrush(color)
            painter.drawRect(self.rect())
        draw_onion_skin(painter, self.onionskin, self.model.viewportmapper)
        try:
            for layer, _, blend_mode, _, visible, opacity in self.model.layerstack:
                if not visible:
                    continue
                draw_layer(
                    painter, layer, blend_mode, opacity,
                    self.model.viewportmapper)
            draw_selection(
                painter,
                self.model.selection,
                self.model.viewportmapper)
            if self.tool is not None:
                self.tool.draw(painter)
        finally:
            painter.end()

    def draw_empty(self, painter):
        brush = QtGui.QBrush(QtCore.Qt.grey)
        brush.setStyle(QtCore.Qt.BDiagPattern)
        painter.setBursh(brush)
        pen = QtGui.QPen(QtCore.Qt.black)
        pen.setWidth(3)
        painter.setPen(pen)
        painter.drawRect(self.rect())

    def draw_images(
            self, painter, rects, viewportmapper, model=None):
        model = model or self.model
        if model.imagestack_layout != CanvasModel.STACKED:
            images = self.model.imagestack + [model.baseimage]
            for image, rect in zip(images, rects):
                rect = viewportmapper.to_viewport_rect(rect)
                image = image.scaled(
                    rect.size().toSize(),
                    QtCore.Qt.KeepAspectRatio,
                    QtCore.Qt.SmoothTransformation)
                painter.drawImage(rect, image)
        else:
            images = list(reversed(model.imagestack))
            images += [model.baseimage]
            wipes = model.imagestack_wipes[:]
            wipes.append(model.baseimage_wipes)
            for image, rect, wipe in zip(images, rects, wipes):
                mode = QtCore.Qt.KeepAspectRatio
                image = image.scaled(rect.size().toSize(), mode)
                image = image.copy(wipe)
                wipe = viewportmapper.to_viewport_rect(wipe)
                painter.drawImage(wipe, image)

    def delete_selection(self):
        if self.model.layerstack.is_locked:
            return
        if self.model.selection.type == Selection.NO:
            return
        if self.model.selection.type == Selection.ELEMENT:
            self.model.layerstack.remove(self.model.selection.element)
            self.model.selection.clear()
            self.model.add_undo_state()
            return
        layer = self.model.layerstack.current
        classes = ProceduralStrokePoint
        # This must be siplifyied globally: ProceduralStroke and PStroke should
        # be merge in only one object
        pspoints = [p for p in self.model.selection if isinstance(p, classes)]
        pstroke_to_parent = {}
        for element in layer:
            if isinstance(element, PStroke):
                pstroke_to_parent[element.procedurale_stroke] = element
        stroke_and_psppoints = {}
        for psp in pspoints:
            stroke_and_psppoints.setdefault(
                pstroke_to_parent[psp.stroke], []).append(psp)
        erase_on_layer(stroke_and_psppoints, layer)
        self.model.selection.clear()
        self.model.add_undo_state()
        self.update()

    def copy(self):
        return self.model.copy_selection()

    def paste(self, shapes=None):
        if self.model.locked:
            return
        if shapes:
            self.model.paste(shapes)
            self.layer_added.emit()
            self.updated.emit()
            return
        image = QtWidgets.QApplication.clipboard().image()
        if not image:
            return
        self.model.selection.clear()
        self.model.add_layer(
            undo=False, name="Pasted image", locked=False)
        self.model.add_image(image)
        self.updated.emit()
        self.layer_added.emit()

    def restore_tools_settings(self, settings: dict[str, dict]):
        for tool in self.tools:
            data = settings.get(tool.__class__.__name__)
            if data is None:
                continue
            for attribute, value in data.items():
                setattr(tool, attribute, value)
