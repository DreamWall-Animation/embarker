from PySide6 import QtCore, QtGui
from paintcanvas.shapes import Stroke
from paintcanvas.tools.basetool import NavigationTool
from paintcanvas.mathutils import distance


class DrawTool(NavigationTool):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.pressure = 1
        self.stroke = None
        self.old_time = None
        self.old_mouse_time = None

    @property
    def color(self):
        return self.drawcontext.color

    @color.setter
    def color(self, color):
        self.drawcontext.color = color

    @property
    def linewidth(self):
        return self.drawcontext.size

    @linewidth.setter
    def linewidth(self, size):
        self.drawcontext.size = size

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        if self.layerstack.is_locked or self.navigator.space_pressed:
            return
        self.pressure = 1
        if self.layerstack.current is None:
            self.model.add_layer(undo=False, name='Stroke')
        self.selection.clear()
        self.stroke = Stroke(
            start=self.viewportmapper.to_units_coords(event.pos()),
            color=self.color,
            size=self.pressure * self.linewidth)
        self.layerstack.current.append(self.stroke)

    def mouseMoveEvent(self, event):
        if not super().mouseMoveEvent(event):
            self.add_point(event.pos())

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        if super().mouseMoveEvent(event):
            return
        if self.stroke:
            if not self.stroke.is_valid:
                self.layerstack.current.remove(self.stroke)
            self.stroke = None
        else:
            super().mouseReleaseEvent(event)
        return True

    def tabletMoveEvent(self, event):
        self.pressure = event.pressure()
        self.add_point(event.pos())

    def add_point(self, position):
        point = self.viewportmapper.to_units_coords(position)
        width = self.pressure * self.linewidth
        valid = self.linewidth / 2
        if not self.stroke or distance(point, self.stroke[-1][0]) <= valid:
            return
        self.stroke.add_point(
            point=point,
            size=width)

    def window_cursor_visible(self):
        return self.navigator.space_pressed or self.layerstack.is_locked

    def window_cursor_override(self):
        cursor = super().window_cursor_override()
        if cursor:
            return cursor
        if self.layerstack.is_locked:
            return QtCore.Qt.ForbiddenCursor

    def draw(self, painter: QtGui.QPainter):
        if self.navigator.space_pressed:
            return

        painter.setCompositionMode(QtGui.QPainter.CompositionMode_Difference)
        painter.setPen(QtCore.Qt.white)
        painter.setBrush(QtCore.Qt.transparent)
        radius = self.viewportmapper.to_viewport(self.linewidth)
        pos = self.canvas.mapFromGlobal(QtGui.QCursor.pos())
        if radius >= 2:
            painter.drawEllipse(pos, radius / 2, radius / 2)
            return
        painter.drawEllipse(pos, 1, 1)
        painter.drawLine(pos.x(), pos.y() - 8, pos.x(), pos.y() - 4)
        painter.drawLine(pos.x(), pos.y() + 4, pos.x(), pos.y() + 8)
        painter.drawLine(pos.x() - 8, pos.y(), pos.x() - 4, pos.y())
        painter.drawLine(pos.x() + 4, pos.y(), pos.x() + 8, pos.y())


class SmoothDrawTool(NavigationTool):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.pressure = 1
        self.stroke = None
        self.buffer = []
        self.width_buffer = []
        self.buffer_lenght = 20

    @property
    def color(self):
        return self.drawcontext.color

    @color.setter
    def color(self, color):
        self.drawcontext.color = color

    @property
    def linewidth(self):
        return self.drawcontext.size

    @linewidth.setter
    def linewidth(self, size):
        self.drawcontext.size = size

    def mousePressEvent(self, event):
        if self.layerstack.is_locked or self.navigator.space_pressed:
            return
        if self.layerstack.current is None:
            self.model.add_layer(undo=False, name='Stroke')
        self.selection.clear()
        point = self.viewportmapper.to_units_coords(event.pos())
        pressure = self.pressure * self.linewidth
        self.buffer = [point]
        self.width_buffer = [pressure]
        self.stroke = Stroke(
            start=point, color=self.color, size=pressure)
        self.layerstack.current.append(self.stroke)

    def mouseMoveEvent(self, event):
        if not super().mouseMoveEvent(event):
            self.add_point(event.pos())

    def add_point(self, point):
        self.buffer.append(self.viewportmapper.to_units_coords(point))
        self.width_buffer.append(self.pressure * self.linewidth)
        if self.stroke:
            x = sum(p.x() for p in self.buffer) / len(self.buffer)
            y = sum(p.y() for p in self.buffer) / len(self.buffer)
            self.stroke.add_point(
                point=QtCore.QPointF(x, y),
                size=sum(self.width_buffer) / len(self.width_buffer))
        self.buffer = self.buffer[-self.buffer_lenght:]
        self.width_buffer = self.width_buffer[-self.buffer_lenght:]

    def mouseReleaseEvent(self, event):
        self.buffer = []
        self.width_buffer = []
        if self.stroke:
            if not self.stroke.is_valid:
                self.layerstack.current.remove(self.stroke)
            self.stroke = None
        else:
            super().mouseReleaseEvent(event)
        return True

    def tabletMoveEvent(self, event):
        self.pressure = event.pressure()
        self.add_point(event.pos())
        return True

    def window_cursor_visible(self):
        return self.navigator.space_pressed

    def window_cursor_override(self):
        cursor = super().window_cursor_override()
        if cursor:
            return cursor
        if self.layerstack.is_locked:
            return QtCore.Qt.ForbiddenCursor

    def draw(self, painter):
        if self.navigator.space_pressed:
            return
        radius = self.viewportmapper.to_viewport(self.linewidth)
        painter.setCompositionMode(QtGui.QPainter.CompositionMode_Difference)
        painter.setPen(QtCore.Qt.white)
        painter.setBrush(QtCore.Qt.transparent)
        pos = self.canvas.mapFromGlobal(QtGui.QCursor.pos())
        painter.drawEllipse(pos, radius / 2, radius / 2)
        if not self.stroke:
            return
        point = self.stroke.points[-1][0]
        point = self.viewportmapper.to_viewport_coords(point)
        painter.drawLine(pos, point)
