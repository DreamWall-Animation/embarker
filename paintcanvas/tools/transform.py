import time
from PySide6 import QtCore, QtGui, QtWidgets
from viewportmapper import NDCViewportMapper

from paintcanvas.draw import render_annotation, create_selection_pixmap
from paintcanvas.geometry import get_shape_rect, ensure_positive_rect
from paintcanvas.proceduralstroke import ProceduralStrokePoint
from paintcanvas.tools.base import NavigationTool
from paintcanvas.tools.translate import shift_element, shift_selection_content
from paintcanvas.selection import selection_rect, Selection
from paintcanvas.shapes import (
    Arrow, Rectangle, Circle, Bitmap, Stroke, Text, Line, PStroke)


class TransformTool(NavigationTool):
    BRUTE_FORCE = 0
    FAST = 1

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.element_hover = None
        self.action = None
        self._mouse_ghost = None
        self._offset_start = None
        self._reference_rect = None
        self.current_cusor_pos = None
        self.reference_rect = None
        self._ratio = None
        self.manipulator = None
        self._pixmap = None
        self._mode = self.BRUTE_FORCE
        self.last_look_up = None

    def wheelEvent(self, event):
        if self.manipulator:
            return
        return super().wheelEvent(event)

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        return_condition = (
            event.button() != QtCore.Qt.LeftButton or
            self.manipulator or
            self.navigator.space_pressed or
            self.layerstack.current is None or
            self.layerstack.is_locked)
        if return_condition:
            return

        fast_mode_required = (
            self.selection.type == Selection.SUBOBJECTS and (
            len(self.selection) > 1500 or
            isinstance(event, QtGui.QTabletEvent)))

        self._mode = self.FAST if fast_mode_required else self.BRUTE_FORCE

        self._mouse_ghost = event.pos()
        self._offset_start = event.pos()

        if not self.current_cusor_pos:
            return

        rects = self.corner_rects()
        sel_rect = self.selection_rect()
        self.reference_rect = sel_rect

        if self._mode == self.FAST:
            self._pixmap = create_selection_pixmap(
                self.model, self.selection, self.viewportmapper)
            rect = self.selection.get_rect(force_compute=True)
            rect = self.viewportmapper.to_viewport_rect(rect)
            self.manipulator = ensure_positive_rect(rect)

        if rects and sel_rect:
            self._ratio = sel_rect.height() / sel_rect.width()
            if rects[0].contains(event.pos()):
                self.action = 'topleft'
                return

            if rects[2].contains(event.pos()):
                self.action = 'bottomleft'
                return

            if rects[1].contains(event.pos()):
                self.action = 'topright'
                return

            if rects[3].contains(event.pos()):
                self.action = 'bottomright'
                return

        if sel_rect and sel_rect.contains(event.pos()):
            self.action = 'move'
            self.canvas.selection_changed.emit()
            return

        if self.element_hover:
            self.selection.set(self.element_hover)
            self.action = 'move'
            self.canvas.selection_changed.emit()
            return

        self.selection.clear()
        self.canvas.selection_changed.emit()

    def mouseMoveEvent(self, event):
        if super().mouseMoveEvent(event):
            return
        self.current_cusor_pos = event.pos()
        if not self._mouse_ghost:
            self.set_hover_element(event.pos())
            return
        if self._mode == self.BRUTE_FORCE:
            return self.mouse_move_event_brute_force(event)
        return self.mouve_move_event_fast(event)

    def mouve_move_event_fast(self, event):
        if self.action in ('topleft', 'topright', 'bottomleft', 'bottomright'):
            ratio = self._ratio if self.navigator.shift_pressed else None
            set_corner(
                self.manipulator, event.pos(),
                corner=self.action,
                ratio=ratio)
        if self.action == 'move':
            point = event.pos()
            x = self._mouse_ghost.x() - point.x()
            y = self._mouse_ghost.y() - point.y()
            offset = QtCore.QPointF(x, y)
            self._mouse_ghost = event.pos()
            self.manipulator.moveCenter(self.manipulator.center() - offset)

    def mouse_move_event_brute_force(self, event):
        if self.action in ('topleft', 'topright', 'bottomleft', 'bottomright'):
            rect = QtCore.QRectF(self.reference_rect)
            point = event.pos()
            ratio = self._ratio if self.navigator.shift_pressed else None
            set_corner(
                rect, point,
                corner=self.action,
                ratio=ratio)
            factor = scale_factor(self.reference_rect, rect)
            resize_selection(
                self.selection, self.reference_rect, rect, factor,
                self.viewportmapper)
            strokes = {
                point.stroke for point in
                self.selection if isinstance(point, ProceduralStrokePoint)}
            for stroke in strokes:
                stroke.brush_width = stroke.brush_width * factor
            self.reference_rect = rect

        if self.action == 'move':
            point = event.pos()
            x = self._mouse_ghost.x() - point.x()
            y = self._mouse_ghost.y() - point.y()
            offset = QtCore.QPoint(x, y)
            self._mouse_ghost = event.pos()
            if self.selection.type == Selection.SUBOBJECTS:
                shift_selection_content(
                    self.selection, offset, self.viewportmapper)
            elif self.selection.type == Selection.ELEMENT:
                shift_element(
                    self.selection.element, offset, self.viewportmapper)

    def set_hover_element(self, point):
        if self.selection.type:
            units_pos = self.viewportmapper.to_units_coords(point)
            rect = self.selection.get_rect()
            if rect and rect.contains(units_pos):
                self.element_hover = self.selection
                return
        if not self.last_look_up or time.time() - self.last_look_up < 0.03:
            point = self.viewportmapper.to_units_coords(point)
            self.last_look_up = time.time()
            self.element_hover = self.layerstack.find_element_at(
                point, self.viewportmapper)

    def mouseReleaseEvent(self, event):
        if self._mode == self.BRUTE_FORCE:
            return self.mouse_release_event_brute_force(event)
        return self.mouse_release_event_fast(event)

    def mouse_release_event_fast(self, event):
        super().mouseReleaseEvent(event)
        if self.reference_rect is not None:
            rect = QtCore.QRectF(self.reference_rect)
            factor = scale_factor(self.reference_rect, self.manipulator)
            QtWidgets.QApplication.instance().setOverrideCursor(
                QtCore.Qt.BusyCursor)
            resize_selection(
                selection=self.selection,
                reference_rect=rect,
                rect=self.manipulator,
                scale_factor=factor,
                viewportmapper=self.viewportmapper)
            strokes = {
                point.stroke for point in
                self.selection if isinstance(point, ProceduralStrokePoint)}
            for stroke in strokes:
                stroke.brush_width = stroke.brush_width * factor
            QtWidgets.QApplication.instance().restoreOverrideCursor()
        self.selection.clear_cache()
        self.reference_rect = None
        self.manipulator = None
        self.action = None
        self._mouse_ghost = None
        self._pixmap = None
        self._ratio = None
        return True

    def mouse_release_event_brute_force(self, event):
        super().mouseReleaseEvent(event)
        result = bool(self._mouse_ghost) and bool(self.selection.type)
        # REBUILD is buggy
        # strokes = {
        #     point.stroke for point in
        #     self.selection if isinstance(point, ProceduralStrokePoint)}
        # if self.action != 'move':
        #     for stroke in strokes:
        #         stroke.rebuild()
        self._mouse_ghost = None
        self._ratio = None
        self.action = None
        self.reference_rect = None
        return result

    def window_cursor_override(self):
        cursor = super().window_cursor_override()
        if cursor:
            return cursor
        if self.layerstack.is_locked:
            return QtCore.Qt.ForbiddenCursor
        if not self.current_cusor_pos:
            return

        if self.action == 'topleft':
            return QtCore.Qt.SizeFDiagCursor
        if self.action == 'bottomleft':
            return QtCore.Qt.SizeBDiagCursor
        if self.action == 'topright':
            return QtCore.Qt.SizeBDiagCursor
        if self.action == 'bottomright':
            return QtCore.Qt.SizeFDiagCursor
        if self.action == 'move':
            return QtCore.Qt.SizeAllCursor

        rects = self.corner_rects()
        if rects:
            if rects[0].contains(self.current_cusor_pos):
                return QtCore.Qt.SizeFDiagCursor
            if rects[2].contains(self.current_cusor_pos):
                return QtCore.Qt.SizeBDiagCursor
            if rects[1].contains(self.current_cusor_pos):
                return QtCore.Qt.SizeBDiagCursor
            if rects[3].contains(self.current_cusor_pos):
                return QtCore.Qt.SizeFDiagCursor

        if self.element_hover:
            return QtCore.Qt.SizeAllCursor

    def selection_rect(self):
        rect = selection_rect(self.selection)
        if not rect:
            rect = get_shape_rect(self.selection.element, self.viewportmapper)
        else:
            rect = self.viewportmapper.to_viewport_rect(rect)
        if not rect:
            return
        return ensure_positive_rect(rect)

    def corner_rects(self):
        rect = self.manipulator or self.selection_rect()
        if not rect:
            return
        return (
            get_rect_from_point(rect.topLeft(), 4),
            get_rect_from_point(rect.topRight(), 4),
            get_rect_from_point(rect.bottomLeft(), 4),
            get_rect_from_point(rect.bottomRight(), 4))

    def draw(self, painter):
        if not self.selection:
            return

        painter.setRenderHint(QtGui.QPainter.Antialiasing, False)
        painter.setPen(QtCore.Qt.black)
        painter.setBrush(QtCore.Qt.white)
        for rect in self.corner_rects() or []:
            painter.drawRect(rect)
        painter.setRenderHint(QtGui.QPainter.Antialiasing, True)
        if self._pixmap:
            painter.setBrush(QtCore.Qt.transparent)
            painter.setPen(QtCore.Qt.white)
            painter.drawRect(self.manipulator.toRect())
            painter.setCompositionMode(
                QtGui.QPainter.CompositionMode_Difference)
            painter.drawPixmap(self.manipulator.toRect(), self._pixmap)


def get_rect_from_point(point, size):
    return QtCore.QRect(
        point.x() - size, point.y() - size, size * 2, size * 2)


def resize_selection(
        selection, reference_rect, rect, scale_factor, viewportmapper):
    if not selection:
        return
    if selection.type == Selection.ELEMENT:
        element = selection.element
        shapes = (Arrow, Rectangle, Circle, Bitmap, Text, Line)
        if isinstance(element, Bitmap):
            element.rect = viewportmapper.to_units_rect(rect)
            return
        elif isinstance(element, shapes):
            points = (element.start, element.end)
        elif isinstance(element, Stroke):
            points = [p[0] for p in element.points]
        elif isinstance(element, PStroke):
            points = list(element.procedurale_stroke)
        else:
            return
    elif selection.type == Selection.SUBOBJECTS:
        points = selection

    strokes = set()
    for point in points:
        if isinstance(point, (QtCore.QPointF, QtCore.QPoint)):
            vp_point = viewportmapper.to_viewport_coords(point)
            x = relative(
                vp_point.x(),
                in_min=reference_rect.left(),
                in_max=reference_rect.right(),
                out_min=rect.left(),
                out_max=rect.right())
            y = relative(
                vp_point.y(),
                in_min=reference_rect.top(),
                in_max=reference_rect.bottom(),
                out_min=rect.top(),
                out_max=rect.bottom())
            unit_point = viewportmapper.to_units_coords(QtCore.QPointF(x, y))
            point.setX(unit_point.x())
            point.setY(unit_point.y())
        if isinstance(point, ProceduralStrokePoint):
            qpoint = QtCore.QPointF(point.center.x, point.center.y)
            vp_point = viewportmapper.to_viewport_coords(qpoint)
            x = relative(
                vp_point.x(),
                in_min=reference_rect.left(),
                in_max=reference_rect.right(),
                out_min=rect.left(),
                out_max=rect.right())
            y = relative(
                vp_point.y(),
                in_min=reference_rect.top(),
                in_max=reference_rect.bottom(),
                out_min=rect.top(),
                out_max=rect.bottom())
            unit_point = viewportmapper.to_units_coords(QtCore.QPointF(x, y))
            point.center.x = round(unit_point.x(), 8)
            point.center.y = round(unit_point.y(), 8)
            point.pressure = round(point.pressure * scale_factor, 8)
            point.inner_outline_radius = round(
                point.inner_outline_radius * scale_factor, 8)
            point.outer_outline_radius = round(
                point.outer_outline_radius * scale_factor, 8)
            strokes.add(point.stroke)
    for stroke in strokes:
        stroke.cache_stroke(clear_cache=True)


def set_corner(rect, point, corner, ratio=False):
    if corner == 'topleft':
        x = min((rect.right() - 0.5, point.x()))
        y = min((rect.bottom() - 0.5, point.y()))
        rect.setTopLeft(QtCore.QPointF(x, y))
    if corner == 'topright':
        x = max((rect.left() + 0.5, point.x()))
        y = min((rect.bottom() - 0.5, point.y()))
        rect.setTopRight(QtCore.QPointF(x, y))
    if corner == 'bottomleft':
        x = min((rect.right() - 0.5, point.x()))
        y = max((rect.top() + 0.5, point.y()))
        rect.setBottomLeft(QtCore.QPointF(x, y))
    if corner == 'bottomright':
        x = max((rect.left() + 0.5, point.x()))
        y = max((rect.top() + 0.5, point.y()))
        rect.setBottomRight(QtCore.QPointF(x, y))
    if ratio is not None:
        rect.setHeight(rect.width() * ratio)


def relative(value, in_min, in_max, out_min, out_max):
    """
    this function resolve simple equation and return the unknown value
    in between two values.
    a, a" = in_min, out_min
    b, b " = out_max, out_max
    c = value
    ? is the unknown processed by function.
    a --------- c --------- b
    a" --------------- ? ---------------- b"
    """
    factor = float((value - in_min)) / (in_max - in_min)
    width = out_max - out_min
    return out_min + (width * (factor))


def scale_factor(qrectf1, qrectf2):
    return qrectf2.width() * qrectf2.height() / (qrectf1.width() * qrectf1.height())