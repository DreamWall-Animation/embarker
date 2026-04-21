import math
from PySide6 import QtGui, QtCore
from paintcanvas.draw import create_selection_pixmap
from paintcanvas.proceduralstroke import ProceduralStrokePoint
from paintcanvas.qtutils import pixmap
from paintcanvas.geometry import ensure_positive_rect
from paintcanvas.selection import Selection
from paintcanvas.shapes import (
    Arrow, Rectangle, Circle, Bitmap, Stroke, Text, Line, PStroke)
from paintcanvas.tools.base import NavigationTool


class RotationTool(NavigationTool):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._start_point = None
        self._end_point = None
        self._manipulator = None
        self._pixmap = None
        self.cursor = QtGui.QCursor(pixmap('rotate.png').scaled(16, 16))

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        if not self.selection or event.button() != QtCore.Qt.LeftButton:
            return
        if self.selection.type != Selection.SUBOBJECTS:
            return
        self._start_point = self.viewportmapper.to_units_coords(event.pos())
        self._manipulator = QtCore.QRectF(
            self.selection.get_rect(force_compute=True))
        self._pixmap = create_selection_pixmap(
            self.model, self.selection, self.viewportmapper)

    def mouseMoveEvent(self, event):
        if super().mouseMoveEvent(event):
            return
        self._end_point = self.viewportmapper.to_units_coords(event.pos())

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        result = False
        if self._end_point and self._start_point:
            center = self._manipulator.center()
            p1 = self.viewportmapper.to_viewport_coords(self._start_point)
            center = self.viewportmapper.to_viewport_coords(
                self._manipulator.center())
            line_1 = QtCore.QLineF(center, p1)
            p2 = self.viewportmapper.to_viewport_coords(self._end_point)
            line_2 = QtCore.QLineF(center, p2)
            angle = line_1.angleTo(line_2)
            rotate_selection(self.selection, -angle, self.viewportmapper)
            self.selection.clear_cache()
            result = True
        self._manipulator = None
        self._end_point = None
        self._start_point = None
        return result

    def window_cursor_override(self):
        cursor = super().window_cursor_override()
        if cursor:
            return cursor
        if not self.selection:
            return
        if self.selection.type != Selection.SUBOBJECTS:
            return QtCore.Qt.ForbiddenCursor
        return self.cursor

    def wheelEvent(self, event):
        if self._start_point:
            return
        return super().wheelEvent(event)

    def draw(self, painter):
        if not self._start_point or not self._manipulator:
            return

        lenght = 30
        painter.setPen(QtCore.Qt.black)
        painter.setBrush(QtCore.Qt.white)
        painter.setCompositionMode(QtGui.QPainter.CompositionMode_Difference)
        p1 = self.viewportmapper.to_viewport_coords(self._start_point)
        center = self.viewportmapper.to_viewport_coords(
            self._manipulator.center())
        line_1 = QtCore.QLineF(center, p1)
        line_1.setLength(lenght)

        if not self._end_point:
            return

        p2 = self.viewportmapper.to_viewport_coords(self._end_point)
        line_2 = QtCore.QLineF(center, p2)
        line_2.setLength(lenght)

        rect = QtCore.QRectF(
            center.x() - lenght, center.y() - lenght, lenght * 2, lenght * 2)
        ref = QtCore.QLineF(center, QtCore.QPointF(center.x() + 1, center.y()))
        angle_1 = int(ref.angleTo(line_1) * 16)
        angle_2 = int(line_1.angleTo(line_2) * 16)
        painter.setOpacity(.5)
        painter.drawPie(rect, angle_1, angle_2)
        painter.setOpacity(1)

        angle = int(round(line_1.angleTo(line_2)))
        line_2.setLength(lenght + 16)
        end = line_2.pointAt(1)
        font = QtGui.QFont()
        font.setBold(True)
        font.setPixelSize(12)
        painter.setFont(font)
        painter.drawText(end, f'{angle}°')

        if not self._pixmap:
            return

        painter.save()
        manipulator = ensure_positive_rect(
            self.viewportmapper.to_viewport_rect(self._manipulator))
        pixmap = self._pixmap.scaled(manipulator.toRect().size())
        painter.translate(center)
        painter.rotate(-angle)

        painter.drawPixmap(
            -pixmap.width() / 2.0,
            -pixmap.height() / 2.0,
            pixmap)
        painter.restore()


def rotate_point(x, y, cx, cy, angle):
    x_rotated = (math.cos(angle) * (x - cx) - math.sin(angle) * (y - cy) + cx)
    y_rotated = (math.sin(angle) * (x - cx) + math.cos(angle) * (y - cy) + cy)
    return x_rotated, y_rotated


def selection_rotatable(selection):
    unrotatble = Bitmap, Rectangle
    if (selection.mode == Selection.ELEMENT):
        return not isinstance(selection.element, unrotatble)
    return True


def rotate_selection(selection, angle, viewportmapper):
    if selection.type == Selection.ELEMENT:
        element = selection.element
        shapes = (Arrow, Rectangle, Circle, Text, Line)
        if isinstance(element, shapes):
            points = (element.start, element.end)
        elif isinstance(element, Stroke):
            points = [p[0] for p in element.points]
        elif isinstance(element, PStroke):
            points = list(element.procedurale_stroke)
        else:
            return
    elif selection.type == Selection.SUBOBJECTS:
        points = selection

    rect = selection.get_rect(force_compute=True)
    center = viewportmapper.to_viewport_coords(rect.center())
    strokes = set()
    angle = math.radians(angle)
    for point in points:
        if isinstance(point, (QtCore.QPointF, QtCore.QPoint)):
            vp_point = viewportmapper.to_viewport_coords(point)
            x, y = rotate_point(
                vp_point.x(), vp_point.y(), center.x(), center.y(), angle)
            rotated = viewportmapper.to_units_coords(QtCore.QPointF(x, y))
            point.setX(rotated.x())
            point.setY(rotated.y())
        if isinstance(point, ProceduralStrokePoint):
            vp_point = viewportmapper.to_viewport_coords(
                QtCore.QPointF(point.center.x, point.center.y))
            x, y = rotate_point(
                vp_point.x(), vp_point.y(), center.x(), center.y(), angle)
            rotated = viewportmapper.to_units_coords(QtCore.QPointF(x, y))
            point.center.x = rotated.x()
            point.center.y = rotated.y()
            strokes.add(point.stroke)

    for stroke in strokes:
        stroke.cache_stroke(clear_cache=True)


