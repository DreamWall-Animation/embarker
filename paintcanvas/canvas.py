import os
import time
from functools import partial
from PySide6 import QtCore, QtWidgets, QtGui

from paintcanvas.geometry import (
    get_global_rect, get_shape_rect, ensure_positive_rect)
from viewportmapper import ViewportMapper
from paintcanvas.layersview import LayerView
from paintcanvas.model import CanvasModel
from paintcanvas.qtutils import icon
from paintcanvas.selection import selection_rect, Selection
from paintcanvas.shapes import (
    Circle, Rectangle, Arrow, Stroke, Bitmap, Text, Line)
from paintcanvas.shapesettings import ShapeSettingsWidget, ToolsSettingWidget
from paintcanvas.tools import TOOLS
from paintcanvas.tools.erasertool import get_point_to_erase, erase_on_layer
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
    updated = QtCore.Signal()
    selection_changed = QtCore.Signal()
    panzoom_changed = QtCore.Signal()
    size_changed = QtCore.Signal()

    def __init__(self, model: CanvasModel, parent=None):
        super().__init__(parent)
        self.mute = False
        self.setMouseTracking(True)
        self.setAcceptDrops(True)
        self.shape_settings_widget = None
        self.tool_settings_widget = None

        self.is_using_tablet = False
        self.last_update_evaluation_time = 0
        self.last_update_call_time = time.time()
        self.captime = .1
        self.model: CanvasModel = model
        self.action_group = QtGui.QActionGroup(self)
        self.action_group.setExclusive(True)
        self.tool_actions = self.get_tool_actions()
        self.all_actions = self.tool_actions.copy()
        self.all_actions.update(self.get_canvas_actions())
        self.tool = None
        list(self.tool_actions.values())[0].trigger()

        self.timer = QtCore.QTimer(self)
        self.timer.start(300)
        self.timer.timeout.connect(self.update)

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
        actions = {}
        for tool in TOOLS:
            name = tool['name']
            action = QtGui.QAction(name, self)
            action.setIcon(icon(tool['icon']))
            tool = tool['tool'](canvas=self)
            action.triggered.connect(partial(self.set_tool, tool))
            actions[f'Canvas>{name}'] = action
            action.setCheckable(True)
            self.action_group.addAction(action)
        return actions

    def get_canvas_actions(self):
        actions = {
            'Canvas>DeleteSelection': QtGui.QAction('Delete selection', self),
            'Canvas>Undo': QtGui.QAction('Undo', self),
            'Canvas>Redo': QtGui.QAction('Redo', self)}
        actions['Canvas>DeleteSelection'].triggered.connect(
            self.delete_selection)
        actions['Canvas>Undo'].triggered.connect(self.undo)
        actions['Canvas>Redo'].triggered.connect(self.redo)
        return actions

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

    def enterEvent(self, _):
        self.update_cursor()

    def leaveEvent(self, _):
        QtWidgets.QApplication.restoreOverrideCursor()

    def mouseMoveEvent(self, event):
        if self.is_using_tablet:
            return
        self.tool.mouseMoveEvent(event)
        self.update_cursor()
        self.update()

    def mousePressEvent(self, event):
        self.setFocus(QtCore.Qt.MouseFocusReason)
        self.model.navigator.update(event, pressed=True)
        result = self.tool.mousePressEvent(event)
        self.update_cursor()
        if result:
            self.update()

    def mouseReleaseEvent(self, event):
        if self.is_using_tablet:
            return
        self.model.navigator.update(event, pressed=False)
        result = self.tool.mouseReleaseEvent(event)
        if result is True and self.model.layerstack.current is not None:
            self.model.add_undo_state()
            self.updated.emit()
        self.last_update_evaluation_time = 0
        self.update_cursor()
        self.update()

    def keyPressEvent(self, event):
        if event.isAutoRepeat():
            return
        self.model.navigator.update(event, pressed=True)
        self.tool.keyPressEvent(event)
        self.update_cursor()
        self.update()

    def keyReleaseEvent(self, event):
        if event.isAutoRepeat():
            return
        self.model.navigator.update(event, pressed=False)
        self.tool.keyReleaseEvent(event)
        self.update_cursor()
        self.update()

    def tabletEvent(self, event):
        if event.type() == QtGui.QTabletEvent.TabletPress:
            self.is_using_tablet = True
            self.timer.setInterval(15)
            event.accept()
            return
        if event.type() == QtGui.QTabletEvent.TabletRelease:
            self.is_using_tablet = False
            self.timer.setInterval(300)
            event.accept()
            return
        self.tool.tabletMoveEvent(event)
        self.update_cursor()

    def cap_update(self):
        now = time.time()
        delta = now - self.last_update_call_time
        self.captime = max(0.02, delta)
        if delta < self.captime:
            return
        self.last_update_call_time = now
        start_time = time.time()
        self.update()
        self.last_update_evaluation_time = time.time() - start_time

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
        if not self.tool.window_cursor_visible():
            override = QtCore.Qt.BlankCursor
        else:
            override = self.tool.window_cursor_override()

        override = override or QtCore.Qt.ArrowCursor
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
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        if self.model.wash_opacity:
            painter.setPen(QtCore.Qt.NoPen)
            color = QtGui.QColor(self.model.wash_color)
            color.setAlpha(self.model.wash_opacity)
            painter.setBrush(color)
            painter.drawRect(self.rect())
        try:
            for layer, _, blend_mode, _, visible, opacity in self.model.layerstack:
                if not visible:
                    continue
                draw_layer(
                    painter, layer, blend_mode, opacity, self.model.viewportmapper)
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
        classes = QtCore.QPoint, QtCore.QPointF
        points = [p for p in self.model.selection if isinstance(p, classes)]
        points_to_erase = get_point_to_erase(points, layer)
        erase_on_layer(points_to_erase, layer)
        self.model.selection.clear()
        self.model.add_undo_state()
        self.update_shape_settings_view()
        self.repaint()


def render_annotation(
        viewportmapper: ViewportMapper,
        painter: QtGui.QPainter = None,
        model: CanvasModel = None):
    painter.setRenderHint(QtGui.QPainter.Antialiasing)
    if model.wash_opacity:
        painter.setPen(QtCore.Qt.NoPen)
        color = QtGui.QColor(model.wash_color)
        color.setAlpha(model.wash_opacity)
        painter.setBrush(color)
        rect = QtCore.QRect(0, 0, *viewportmapper.view_size.toTuple())
        painter.drawRect(rect)
    for layer, _, blend_mode, _, visible, opacity in model.layerstack:
        if not visible:
            continue
        draw_layer(painter, layer, blend_mode, opacity, viewportmapper)


def draw_layer(
        painter: QtGui.QPainter, layer, blend_mode, opacity, viewportmapper):
    painter.setOpacity(opacity / 255)
    painter.setCompositionMode(blend_mode)
    for element in layer:
        if isinstance(element, Stroke):
            draw_stroke(painter, element, viewportmapper)
        elif isinstance(element, Arrow):
            draw_arrow(painter, element, viewportmapper)
        elif isinstance(element, Circle):
            draw_shape(painter, element, painter.drawEllipse, viewportmapper)
        elif isinstance(element, Rectangle):
            draw_shape(painter, element, painter.drawRect, viewportmapper)
        elif isinstance(element, Bitmap):
            draw_bitmap(painter, element, viewportmapper)
        elif isinstance(element, Text):
            draw_text(painter, element, viewportmapper)
        elif isinstance(element, Line):
            draw_line(painter, element, viewportmapper)
    painter.setOpacity(1)
    painter.setCompositionMode(QtGui.QPainter.CompositionMode_SourceOver)


def _get_text_alignment_flags(alignment):
    return [
        (QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop),
        (QtCore.Qt.AlignRight | QtCore.Qt.AlignTop),
        (QtCore.Qt.AlignHCenter | QtCore.Qt.AlignTop),
        (QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter),
        (QtCore.Qt.AlignCenter),
        (QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter),
        (QtCore.Qt.AlignLeft | QtCore.Qt.AlignBottom),
        (QtCore.Qt.AlignHCenter | QtCore.Qt.AlignBottom),
        (QtCore.Qt.AlignRight | QtCore.Qt.AlignBottom)][alignment]


def draw_text(painter, text, viewportmapper):
    if not text.is_valid:
        return
    rect = get_shape_rect(text, viewportmapper)
    rect = ensure_positive_rect(rect)
    if text.filled:
        color = text.bgcolor if text.filled else QtCore.Qt.transparent
        color = QtGui.QColor(color)
        if text.bgopacity != 255:
            color.setAlpha(text.bgopacity)
        painter.setPen(QtCore.Qt.transparent)
        painter.setBrush(color)
        painter.drawRect(rect)

    painter.setBrush(QtCore.Qt.transparent)
    painter.setPen(QtGui.QColor(text.color))
    font = QtGui.QFont()
    font.setPointSizeF(viewportmapper.to_viewport(text.text_size))
    painter.setFont(font)
    alignment = _get_text_alignment_flags(text.alignment)
    option = QtGui.QTextOption()
    option.setWrapMode(QtGui.QTextOption.WrapAtWordBoundaryOrAnywhere)
    option.setAlignment(alignment)
    painter.drawText(rect, text.text, option)


def draw_bitmap(painter, bitmap, viewportmapper):
    painter.setBrush(QtCore.Qt.transparent)
    painter.setPen(QtCore.Qt.transparent)
    rect = viewportmapper.to_viewport_rect(bitmap.rect)
    painter.drawImage(rect, bitmap.image)


def draw_shape(painter, shape, drawer, viewportmapper):
    if not shape.is_valid:
        return
    color = QtGui.QColor(shape.color)
    pen = QtGui.QPen(color)
    pen.setCapStyle(QtCore.Qt.RoundCap)
    pen.setJoinStyle(QtCore.Qt.MiterJoin)
    pen.setWidthF(viewportmapper.to_viewport(shape.linewidth))
    painter.setPen(pen)
    state = shape.filled
    color = shape.bgcolor if state else QtCore.Qt.transparent
    color = QtGui.QColor(color)
    if shape.bgopacity != 255:
        color.setAlpha(shape.bgopacity)
    painter.setBrush(color)
    rect = QtCore.QRectF(
        viewportmapper.to_viewport_coords(shape.start),
        viewportmapper.to_viewport_coords(shape.end))
    drawer(rect)


def draw_line(painter, line, viewportmapper):
    if not line.is_valid:
        return
    color = QtGui.QColor(line.color)
    pen = QtGui.QPen(color)
    pen.setCapStyle(QtCore.Qt.RoundCap)
    pen.setJoinStyle(QtCore.Qt.MiterJoin)
    pen.setWidthF(viewportmapper.to_viewport(line.linewidth))
    painter.setPen(pen)
    painter.setBrush(color)
    qline = QtCore.QLineF(
        viewportmapper.to_viewport_coords(line.start),
        viewportmapper.to_viewport_coords(line.end))
    painter.drawLine(qline)


def draw_arrow(painter, arrow, viewportmapper):
    if not arrow.is_valid:
        return
    line = QtCore.QLineF(
        viewportmapper.to_viewport_coords(arrow.start),
        viewportmapper.to_viewport_coords(arrow.end))
    center = line.p2()
    degrees = line.angle()

    offset = viewportmapper.to_viewport(arrow.headsize)
    triangle = QtGui.QPolygonF([
        QtCore.QPoint(center.x() - offset, center.y() - offset),
        QtCore.QPoint(center.x() + offset, center.y()),
        QtCore.QPoint(center.x() - offset, center.y() + offset),
        QtCore.QPoint(center.x() - offset, center.y() - offset)])

    transform = QtGui.QTransform()
    transform.translate(center.x(), center.y())
    transform.rotate(-degrees)
    transform.translate(-center.x(), -center.y())
    triangle = transform.map(triangle)
    path = QtGui.QPainterPath()
    path.setFillRule(QtCore.Qt.WindingFill)
    path.addPolygon(triangle)

    color = QtGui.QColor(arrow.color)
    pen = QtGui.QPen(color)
    pen.setCapStyle(QtCore.Qt.RoundCap)
    pen.setJoinStyle(QtCore.Qt.MiterJoin)
    pen.setWidthF(viewportmapper.to_viewport(arrow.linewidth))
    painter.setPen(pen)
    painter.setBrush(color)
    painter.drawLine(line)
    painter.drawPath(path)


def draw_stroke(painter, stroke, viewportmapper):
    pen = QtGui.QPen(QtGui.QColor(stroke.color))
    pen.setCapStyle(QtCore.Qt.RoundCap)
    start = None
    for point, size in stroke:
        if start is None:
            start = viewportmapper.to_viewport_coords(point)
            continue
        pen.setWidthF(viewportmapper.to_viewport(size))
        painter.setPen(pen)
        end = viewportmapper.to_viewport_coords(point)
        painter.drawLine(start, end)
        start = end


def draw_selection(painter, selection, viewportmapper):
    if selection.type == Selection.SUBOBJECTS:
        draw_subobjects_selection(painter, selection, viewportmapper)
    elif selection.type == Selection.ELEMENT:
        draw_element_selection(painter, selection, viewportmapper)


def draw_element_selection(painter, selection, viewportmapper):
    rect = get_shape_rect(selection.element, viewportmapper)
    if rect is None:
        return
    painter.setRenderHint(QtGui.QPainter.Antialiasing, False)
    painter.setPen(QtCore.Qt.yellow)
    painter.setBrush(QtCore.Qt.NoBrush)
    painter.drawRect(rect)
    painter.setRenderHint(QtGui.QPainter.Antialiasing, True)


def draw_subobjects_selection(painter, selection, viewportmapper):
    painter.setRenderHint(QtGui.QPainter.Antialiasing, False)
    painter.setBrush(QtCore.Qt.yellow)
    painter.setPen(QtCore.Qt.black)
    for element in selection:
        if isinstance(element, (QtCore.QPoint, QtCore.QPointF)):
            point = viewportmapper.to_viewport_coords(element)
            painter.drawRect(point.x() - 2, point.y() - 2, 4, 4)

    rect = viewportmapper.to_viewport_rect(selection_rect(selection))
    painter.setBrush(QtCore.Qt.transparent)
    painter.setPen(QtCore.Qt.black)
    painter.drawRect(rect)
    pen = QtGui.QPen(QtCore.Qt.white)
    pen.setWidth(1)
    pen.setStyle(QtCore.Qt.DashLine)
    offset = round((time.time() * 10) % 10, 3)
    pen.setDashOffset(offset)
    painter.setPen(pen)
    painter.drawRect(rect)
    painter.setRenderHint(QtGui.QPainter.Antialiasing, True)
