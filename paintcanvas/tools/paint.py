from PySide6 import QtCore, QtGui
from paintcanvas.shapes import Stroke, PStroke
from paintcanvas.proceduralstroke import Vector2D
from paintcanvas.tools.base import NavigationTool


class DrawTool(NavigationTool):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.pressure = 1
        self.stroke = None

    @property
    def color(self):
        return self.drawcontext.color

    @color.setter
    def color(self, color):
        self.drawcontext.color = color

    @property
    def bgopacity(self):
        return self.drawcontext.bgopacity

    @bgopacity.setter
    def bgopacity(self, value):
        self.drawcontext.bgopacity = value

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
        pixel_size = self.viewportmapper.get_units_pixel_size().width()
        size = self.linewidth * pixel_size
        threshold = pixel_size * 3
        self.stroke = PStroke(
            self.color,
            size=size,
            bgopacity=self.bgopacity,
            pixel_ratio=self.viewportmapper.get_pixel_size_ratio().toTuple(),
            threshold=threshold)
        point = self.viewportmapper.to_units_coords(event.position())
        self.stroke.procedurale_stroke.set_tail(
            x=point.x(),
            y=point.y(),
            pressure=self.pressure,
            tilt=None)
        self.stroke.procedurale_stroke.cache_stroke()
        self.layerstack.current.append(self.stroke)

    def mouseMoveEvent(self, event):
        if super().mouseMoveEvent(event):
            return
        if not self.stroke:
            return
        if self.navigator.mouse_ghost:
            point = event.position() - self.navigator.mouse_ghost
            if point.manattanLenght() < 1:
                return
        point = self.viewportmapper.to_units_coords(event.position())
        self.stroke.procedurale_stroke.set_tail(
            x=point.x(),
            y=point.y(),
            pressure=self.pressure,
            tilt=None)
        self.stroke.procedurale_stroke.cache_stroke()

    def mouseReleaseEvent(self, event):
        if super().mouseMoveEvent(event):
            return False
        if not self.stroke:
            return False
        point = self.viewportmapper.to_units_coords(event.position())
        self.stroke.procedurale_stroke.close(point.x(), point.y())
        self.stroke.procedurale_stroke.cache_stroke()
        self.stroke.qpath = self.stroke.create_qpath()
        if not self.stroke.is_valid:
            self.layerstack.current.remove(self.stroke)
            self.stroke = None
            return False
        self.stroke = None
        return True

    def tabletMoveEvent(self, event):
        if not self.stroke:
            return
        self.pressure = event.pressure()
        if self.navigator.mouse_ghost:
            point = event.position() - self.navigator.mouse_ghost
            if point.manhatanLenght() < 1:
               return
        point = self.viewportmapper.to_units_coords(event.position())
        pixel_size = self.viewportmapper.get_units_pixel_size()
        tilt = QtGui.QVector2D(
            event.xTilt() * pixel_size.width(),
            event.yTilt() * pixel_size.height()).normalized().toPointF()
        self.stroke.procedurale_stroke.set_tail(
            x=point.x(),
            y=point.y(),
            pressure=self.pressure,
            tilt=Vector2D(tilt.x(), tilt.y()))
        self.stroke.procedurale_stroke.cache_stroke()

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
    def bgopacity(self):
        return self.drawcontext.bgopacity

    @bgopacity.setter
    def bgopacity(self, value):
        self.drawcontext.bgopacity = value

    @property
    def linewidth(self):
        return self.drawcontext.size

    @linewidth.setter
    def linewidth(self, size):
        self.drawcontext.size = size

    def mousePressEvent(self, event):
        if super().mouseMoveEvent(event):
            return
        if self.layerstack.is_locked or self.navigator.space_pressed:
            return
        if self.layerstack.current is None:
            self.model.add_layer(undo=False, name='Stroke')
        self.selection.clear()
        point = self.viewportmapper.to_units_coords(event.pos())
        pixel_size = self.viewportmapper.get_units_pixel_size().width()
        self.buffer = [point]
        self.width_buffer = [self.pressure]

        size = self.linewidth * pixel_size
        threshold = pixel_size * 3
        self.stroke = PStroke(
            self.color,
            size=size,
            bgopacity=self.bgopacity,
            pixel_ratio=self.viewportmapper.get_pixel_size_ratio().toTuple(),
            threshold=threshold)
        point = self.viewportmapper.to_units_coords(event.position())
        self.stroke.procedurale_stroke.set_tail(
            x=point.x(),
            y=point.y(),
            pressure=self.pressure,
            tilt=None)
        self.stroke.procedurale_stroke.cache_stroke()
        self.layerstack.current.append(self.stroke)

    def mouseMoveEvent(self, event):
        if super().mouseMoveEvent(event):
            return
        if not self.stroke:
            return
        if self.navigator.mouse_ghost:
            point = event.position() - self.navigator.mouse_ghost
            if point.manattanLenght() < 1:
                return
        point = self.viewportmapper.to_units_coords(event.position())
        self.buffer.append(point)
        self.width_buffer.append(self.pressure)
        self.stroke.procedurale_stroke.set_tail(
            x=sum(p.x() for p in self.buffer) / len(self.buffer),
            y=sum(p.y() for p in self.buffer) / len(self.buffer),
            pressure=sum(self.width_buffer) / len(self.width_buffer),
            tilt=None)
        self.stroke.procedurale_stroke.cache_stroke()
        self.buffer = self.buffer[-self.buffer_lenght:]
        self.width_buffer = self.width_buffer[-self.buffer_lenght:]

    def mouseReleaseEvent(self, event):
        if not self.stroke:
            return False
        point = self.viewportmapper.to_units_coords(event.position())
        self.buffer.append(point)
        self.width_buffer.append(self.pressure)
        while self.buffer:
            self.stroke.procedurale_stroke.set_tail(
                x=sum(p.x() for p in self.buffer) / len(self.buffer),
                y=sum(p.y() for p in self.buffer) / len(self.buffer),
                pressure=sum(self.width_buffer) / len(self.width_buffer),
                tilt=None)
            self.buffer.pop(0)
            self.width_buffer.pop(0)
        self.buffer = []
        self.width_buffer = []
        self.stroke.procedurale_stroke.close(point.x(), point.y())
        self.stroke.procedurale_stroke.cache_stroke()
        self.stroke.qpath = self.stroke.create_qpath()
        if not self.stroke.is_valid:
            self.layerstack.current.remove(self.stroke)
            self.stroke = None
            return False
        self.stroke = None
        return True

    def tabletMoveEvent(self, event):
        self.pressure = event.pressure()
        self.mouseMoveEvent(event)
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
        painter.setCompositionMode(QtGui.QPainter.CompositionMode_Difference)
        painter.setPen(QtCore.Qt.white)
        painter.setBrush(QtCore.Qt.transparent)
        pixel_size = self.viewportmapper.get_units_pixel_size().width()
        radius = self.viewportmapper.to_viewport(self.linewidth * pixel_size)
        pos = self.canvas.mapFromGlobal(QtGui.QCursor.pos())
        if radius >= 2:
            painter.drawEllipse(pos, radius / 2, radius / 2)
        else:
            painter.drawEllipse(pos, 1, 1)
            painter.drawLine(pos.x(), pos.y() - 8, pos.x(), pos.y() - 4)
            painter.drawLine(pos.x(), pos.y() + 4, pos.x(), pos.y() + 8)
            painter.drawLine(pos.x() - 8, pos.y(), pos.x() - 4, pos.y())
            painter.drawLine(pos.x() + 4, pos.y(), pos.x() + 8, pos.y())
        if not self.stroke or not self.stroke.tail():
            return
        point = self.stroke.tail()
        point = self.viewportmapper.to_viewport_coords(point)
        painter.drawLine(pos, point)
