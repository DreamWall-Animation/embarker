import itertools
from PySide6 import QtCore, QtGui
from paintcanvas.shapes import Stroke, PStroke
from paintcanvas.mathutils import distance_qline_qpoint, qline_cross_bbox
from paintcanvas.tools.base import NavigationTool
from paintcanvas.shapes import split_pstroke

class EraserTool(NavigationTool):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.pressure = 1
        self._mouse_buffer = None
        self.linewidth = 5

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        if not self.layerstack.current:
            return
        self._mouse_buffer = event.pos()

    def mouseMoveEvent(self, event):
        if super().mouseMoveEvent(event) or not self._mouse_buffer:
            return
        p1 = self.viewportmapper.to_units_coords(self._mouse_buffer)
        p2 = self.viewportmapper.to_units_coords(event.pos())
        line = QtCore.QLineF(p1, p2)
        pixel_size = self.viewportmapper.get_units_pixel_size().width()
        width = (self.linewidth * pixel_size) / 2
        layer = self.layerstack.current
        pstrokes_and_pspoints = filter_psp_to_erase_from_line(line, width, layer)
        erase_on_layer(pstrokes_and_pspoints, layer)
        self._mouse_buffer = event.pos()

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        result = bool(self._mouse_buffer)
        self._mouse_buffer = None
        return result

    def tabletMoveEvent(self, event):
        self.pressure = event.pressure()
        self.mouseMoveEvent(event)

    def window_cursor_visible(self):
        return False

    def draw(self, painter):
        if self.navigator.space_pressed:
            return

        painter.setCompositionMode(QtGui.QPainter.CompositionMode_Difference)
        painter.setPen(QtCore.Qt.white)
        painter.setBrush(QtCore.Qt.transparent)
        pixel_size = self.viewportmapper.get_units_pixel_size().width()
        radius = self.viewportmapper.to_viewport(self.linewidth * pixel_size)
        pos = self.canvas.mapFromGlobal(QtGui.QCursor.pos())
        if radius >= 2:
            painter.drawEllipse(pos, radius / 2, radius / 2)
            return
        painter.drawEllipse(pos, 1, 1)
        painter.drawLine(pos.x(), pos.y() - 8, pos.x(), pos.y() - 4)
        painter.drawLine(pos.x(), pos.y() + 4, pos.x(), pos.y() + 8)
        painter.drawLine(pos.x() - 8, pos.y(), pos.x() - 4, pos.y())
        painter.drawLine(pos.x() + 4, pos.y(), pos.x() + 8, pos.y())


def filter_psp_to_erase_from_line(line, width, layer):
    result = {}
    for element in layer:
        skip = (
            not isinstance(element, PStroke) or
            element.procedurale_stroke.bbox is None or
            not qline_cross_bbox(line, width, element.procedurale_stroke.bbox))
        if skip:
            continue
        for psp in element.procedurale_stroke:
            qpoint = QtCore.QPointF(psp.center.x, psp.center.y)
            if distance_qline_qpoint(line, qpoint) < width:
                result.setdefault(element, []).append(psp)
    return result


def erase_on_layer(pstrokes_and_pspoints, layer):
    for pstroke, pspoints in pstrokes_and_pspoints.items():
        index = layer.index(pstroke)
        del layer[index]
        new_strokes = split_pstroke(pstroke, pspoints)
        for new_stroke in new_strokes:
            layer.insert(index, new_stroke)
def filter_point_to_erase_from_line(line, width, layer):
    result = [
        (s, i, [p for p, _ in s if distance_qline_qpoint(line, p) < width])
        for i, s in enumerate(layer) if isinstance(s, Stroke)]
    return [data for data in result if data[2]]
