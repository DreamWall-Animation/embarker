import time
from PySide6 import QtCore, QtGui, QtWidgets

from paintcanvas.draw import create_selection_pixmap
from paintcanvas.geometry import get_shape_rect, ensure_positive_rect
from paintcanvas.tools.base import NavigationTool
from paintcanvas.selection import selection_rect, Selection
from paintcanvas.shapes import (
    Arrow, Rectangle, Circle, Bitmap, Stroke, PStroke, Text, Line)
from paintcanvas.proceduralstroke import ProceduralStrokePoint
from paintcanvas.selection import Selection


class TranslationTool(NavigationTool):
    BRUTE_FORCE = 0
    FAST = 1

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._mouse_ghost = None
        self._offset_start = None
        self.element_hover = None
        self.manipulator = None
        self._pixmap = None
        self._mode = self.BRUTE_FORCE
        self.last_look_up = None

    def mousePressEvent(self, event):
        fast_mode_required = (
            self.selection.type == Selection.SUBOBJECTS and (
            len(self.selection) > 1500 or
            isinstance(event, QtGui.QTabletEvent)))

        self._mode = self.FAST if fast_mode_required else self.BRUTE_FORCE
        if self._mode == self.BRUTE_FORCE:
            return self.mouse_press_event_brute_force(event)
        return self.mouse_press_event_fast(event)

    def mouse_press_event_brute_force(self, event):
        super().mousePressEvent(event)
        return_condition = (
            self.navigator.space_pressed or
            self.layerstack.current is None or
            self.layerstack.is_locked)
        if return_condition:
            return
        self._mouse_ghost = event.pos()
        if self.element_hover is self.selection:
            return
        if self.element_hover:
            self.selection.set(self.element_hover)
            self.canvas.selection_changed.emit()
            return
        self.selection.clear()
        self.canvas.selection_changed.emit()

    def mouse_press_event_fast(self, event):
        super().mousePressEvent(event)
        return_condition = (
            self.navigator.space_pressed or
            self.layerstack.current is None or
            self.layerstack.is_locked)
        if return_condition:
            return
        self._mouse_ghost = event.pos()
        self._offset_start = event.pos()
        if self.element_hover is self.selection:
            self._pixmap = create_selection_pixmap(
                self.model, self.selection, self.viewportmapper)
            rect = self.selection.get_rect()
            rect = self.viewportmapper.to_viewport_rect(rect)
            self.manipulator = ensure_positive_rect(rect)
            return
        if self.element_hover:
            self.selection.set(self.element_hover)
            self.canvas.selection_changed.emit()
            return

        self.selection.clear()
        self.canvas.selection_changed.emit()

    def set_hover_element(self, point):
        if self.selection.type:
            units_pos = self.viewportmapper.to_units_coords(point)
            rect = self.selection.get_rect()
            if rect and rect.contains(units_pos):
                self.element_hover = self.selection
                return
        if not self.last_look_up or time.time() - self.last_look_up < 0.03:
            self.last_look_up = time.time()
            self.element_hover = self.layerstack.find_element_at(
                point, self.viewportmapper)

    def mouseMoveEvent(self, event):
        if self._mode == self.BRUTE_FORCE:
            return self.mouse_move_event_brute_force(event)
        return self.mouse_move_event_fast(event)

    def mouse_move_event_fast(self, event):
        if super().mouseMoveEvent(event):
            return
        if not self._offset_start or not self.manipulator:
            self.set_hover_element(event.pos())
            return

        point = event.pos()
        x = self._mouse_ghost.x() - point.x()
        y = self._mouse_ghost.y() - point.y()
        offset = QtCore.QPointF(x, y)
        self._mouse_ghost = event.pos()
        self.manipulator.moveCenter(self.manipulator.center() - offset)

    def mouse_move_event_brute_force(self, event):
        if super().mouseMoveEvent(event):
            return
        if not self._mouse_ghost:
            self.set_hover_element(event.pos())
            return
        print('DISPLACE')
        point = event.pos()
        x = self._mouse_ghost.x() - point.x()
        y = self._mouse_ghost.y() - point.y()
        offset = QtCore.QPointF(x, y)
        self._mouse_ghost = event.pos()
        if self.selection.type == Selection.SUBOBJECTS:
            shift_selection_content(self.selection, offset, self.viewportmapper)
        elif self.selection.type == Selection.ELEMENT:
            shift_element(self.selection.element, offset, self.viewportmapper)

    def mouseReleaseEvent(self, event):
        if self._mode == self.BRUTE_FORCE:
            return self.mouse_release_event_brute_force(event)
        return self.mouse_release_event_fast(event)

    def mouse_release_event_brute_force(self, event):
        super().mouseReleaseEvent(event)
        result = bool(self._mouse_ghost) and bool(self.selection.type)
        self._mouse_ghost = None
        return result

    def mouse_release_event_fast(self, event):
        super().mouseReleaseEvent(event)
        point = event.pos()
        x = self._offset_start.x() - point.x()
        y = self._offset_start.y() - point.y()
        offset = QtCore.QPointF(x, y)
        self._mouse_ghost = event.pos()
        QtWidgets.QApplication.instance().setOverrideCursor(QtCore.Qt.BusyCursor)
        shift_selection_content(self.selection, offset, self.viewportmapper)
        QtWidgets.QApplication.instance().restoreOverrideCursor()

        self._mouse_ghost = None
        self._offset_start = None
        self._pixmap = None
        return True

    def tabletMoveEvent(self, event):
        self.mouseMoveEvent(event)
        return True

    def window_cursor_override(self):
        cursor = super().window_cursor_override()
        if cursor:
            return cursor
        if self.layerstack.is_locked:
            return QtCore.Qt.ForbiddenCursor
        if self.element_hover:
            return QtCore.Qt.SizeAllCursor

    def draw(self, painter: QtGui.QPainter):
        if self.element_hover is None:
            return
        if self.selection.element == self.element_hover:
            return
        if isinstance(self.element_hover, (QtCore.QPoint, QtCore.QPointF)):
            color = QtGui.QColor(QtCore.Qt.yellow)
            color.setAlpha(75)
            painter.setBrush(color)
            painter.setPen(QtCore.Qt.NoPen)
            point = self.viewportmapper.to_viewport_coords(self.element_hover)
            painter.drawEllipse(point.x() - 20, point.y() - 20, 40, 40)
            return
        if isinstance(self.element_hover, Selection):
            rect = selection_rect(self.element_hover)
            if not rect:
                return
            rect = self.viewportmapper.to_viewport_rect(rect)
        else:
            rect = get_shape_rect(self.element_hover, self.viewportmapper)
        old_opacity = painter.opacity()
        painter.setOpacity(.5)
        painter.setRenderHint(QtGui.QPainter.Antialiasing, False)
        painter.setBrush(QtCore.Qt.transparent)
        painter.setPen(QtCore.Qt.black)
        painter.drawRect(rect)
        pen = QtGui.QPen(QtCore.Qt.white)
        pen.setWidth(1)
        pen.setStyle(QtCore.Qt.DashLine)
        painter.setPen(pen)
        painter.drawRect(rect)
        painter.setRenderHint(QtGui.QPainter.Antialiasing, True)
        painter.setOpacity(old_opacity)
        if self._pixmap:
            painter.setBrush(QtCore.Qt.transparent)
            painter.setPen(QtCore.Qt.white)
            painter.drawRect(self.manipulator.toRect())
            painter.setCompositionMode(
                QtGui.QPainter.CompositionMode_Difference)
            painter.drawPixmap(self.manipulator.toRect(), self._pixmap)


def shift_element(element, offset, viewportmapper):
    if isinstance(element, (QtCore.QPoint, QtCore.QPointF)):
        vp_element = viewportmapper.to_viewport_coords(element)
        result = viewportmapper.to_units_coords(vp_element - offset)
        element.setX(result.x())
        element.setY(result.y())
    elif isinstance(element, ProceduralStrokePoint):
        unit_point = QtCore.QPointF(element.center.x, element.center.y)
        vp_point = viewportmapper.to_viewport_coords(unit_point)
        result = viewportmapper.to_units_coords(vp_point - offset)
        element.center.x = result.x()
        element.center.y = result.y()
    elif isinstance(element, Stroke):
        for point, _ in element.points:
            shift_element(point, offset, viewportmapper)
    elif isinstance(element, PStroke):
        for psp in element.procedurale_stroke:
            shift_element(psp, offset, viewportmapper)
        element.procedurale_stroke.cache_stroke(clear_cache=True)
    elif isinstance(element, (Arrow, Rectangle, Circle, Text, Line)):
        shift_element(element.start, offset, viewportmapper)
        shift_element(element.end, offset, viewportmapper)
    elif isinstance(element, Bitmap):
        vp_rect = viewportmapper.to_viewport_rect(element.rect)
        center = viewportmapper.to_units_coords(vp_rect.center() - offset)
        element.rect.moveCenter(center)


def shift_selection_content(selection, offset, viewportmapper):
    strokes = set()
    for element in selection:
        shift_element(element, offset, viewportmapper)
        if isinstance(element, ProceduralStrokePoint):
            strokes.add(element.stroke)
    for stroke in strokes:
        stroke.cache_stroke(clear_cache=True)


class SelectionTool(NavigationTool):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.start = None
        self.end = None

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        wrong_button = event.button() != QtCore.Qt.LeftButton
        if self.navigator.space_pressed or wrong_button:
            return
        if self.selection.type == Selection.ELEMENT:
            self.selection.clear()
            self.canvas.selection_changed.emit()
        self.start = self.viewportmapper.to_units_coords(event.pos())

    def mouseMoveEvent(self, event):
        if super().mouseMoveEvent(event):
            return
        self.end = event.pos()

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        if event.button() != QtCore.Qt.LeftButton:
            return False
        if self.end is None or not self.layerstack.current:
            self.selection.clear()
        else:
            end = self.viewportmapper.to_units_coords(self.end)
            rect = QtCore.QRectF(self.start, end)
            elements = layer_elements_in_rect(self.layerstack.current, rect)
            self.selection.set(elements)
        self.canvas.selection_changed.emit()
        self.start = None
        self.end = None
        return False

    def tabletMoveEvent(self, event):
        self.mouseMoveEvent(event)

    def window_cursor_override(self):
        cursor = super().window_cursor_override()
        if cursor:
            return cursor
        if self.layerstack.is_locked:
            return QtCore.Qt.ForbiddenCursor
        return QtCore.Qt.CrossCursor

    def draw(self, painter):
        if self.navigator.space_pressed or not self.start or not self.end:
            return
        pen = QtGui.QPen(QtGui.QColor('blue'))
        pen.setWidth(1)
        painter.setPen(pen)
        color = QtGui.QColor('blue')
        color.setAlpha(33)
        painter.setBrush(color)
        start = self.viewportmapper.to_viewport_coords(self.start)
        painter.drawRect(QtCore.QRectF(start, self.end))


def layer_elements_in_rect(layer, rect):
    result = []
    for element in layer:
        if isinstance(element, Stroke):
            result.extend(p for p, _ in element if rect.contains(p))
        elif isinstance(element, PStroke):
            result.extend(
                p for p in element.procedurale_stroke if
                rect.contains(p.center.x, p.center.y))
        elif isinstance(element, (Arrow, Rectangle, Circle, Text, Line)):
            if rect.contains(element.start):
                result.append(element.start)
            if rect.contains(element.end):
                result.append(element.end)
    return result
