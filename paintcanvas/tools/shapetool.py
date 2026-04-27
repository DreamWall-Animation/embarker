
from PySide6 import QtCore
from paintcanvas.shapes import Arrow, Rectangle, Circle, Line
from paintcanvas.tools.basetool import NavigationTool


class ShapeTool(NavigationTool):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.layername = 'Shape'
        self.shape = None

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

    @property
    def bgcolor(self):
        return self.drawcontext.bgcolor

    @bgcolor.setter
    def bgcolor(self, color):
        self.drawcontext.bgcolor = color

    @property
    def bgopacity(self):
        return self.drawcontext.bgopacity

    @bgopacity.setter
    def bgopacity(self, value):
        self.drawcontext.bgopacity = value

    @property
    def filled(self):
        return self.drawcontext.filled

    @filled.setter
    def filled(self, value):
        self.drawcontext.filled = value

    def mouseMoveEvent(self, event):
        if super().mouseMoveEvent(event):
            return
        if self.shape:
            self.shape.handle(self.viewportmapper.to_units_coords(event.pos()))

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        if self.shape:
            self.selection.clear()
            if not self.shape.is_valid:
                self.layerstack.current.remove(self.shape)
            else:
                self.selection.set(self.shape)
            self.canvas.selection_changed.emit()
            self.shape = None
        return True

    def tabletMoveEvent(self, event):
        self.mouseMoveEvent(event)

    def window_cursor_override(self):
        result = super().window_cursor_override()
        if result:
            return result
        if self.layerstack.is_locked:
            return QtCore.Qt.ForbiddenCursor


class LineTool(ShapeTool):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.layername = 'Line'

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        if self.layerstack.is_locked or self.navigator.space_pressed:
            return
        if event.button() != QtCore.Qt.LeftButton:
            return
        if self.layerstack.current is None:
            self.model.add_layer(undo=False, name=self.layername)
        self.selection.clear()
        self.shape = Line(
            start=self.viewportmapper.to_units_coords(event.pos()),
            color=self.drawcontext.color,
            linewidth=self.drawcontext.size)
        self.layerstack.current.append(self.shape)


class ArrowTool(ShapeTool):

    def __init__(self, canvas=None):
        super().__init__(canvas=canvas)
        self.layername = 'Arrow'
        self.headsize = self.drawcontext.size
        self.tailwidth = self.drawcontext.size * 3

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        if self.layerstack.is_locked or self.navigator.space_pressed:
            return
        if event.button() != QtCore.Qt.LeftButton:
            return
        if self.layerstack.current is None:
            self.model.add_layer(undo=False, name=self.layername)
        self.selection.clear()
        self.shape = Arrow(
            start=self.viewportmapper.to_units_coords(event.pos()),
            color=self.drawcontext.color,
            linewidth=self.drawcontext.size)
        self.layerstack.current.append(self.shape)
        if self.shape:
            self.shape.headsize = self.headsize
            self.shape.linewidth = self.tailwidth


class RectangleTool(ShapeTool):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.layername = 'Rectangle'
        self.shape_cls = Rectangle

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        if self.layerstack.is_locked or self.navigator.space_pressed:
            return
        if event.button() != QtCore.Qt.LeftButton:
            return
        if self.layerstack.current is None:
            self.model.add_layer(undo=False, name=self.layername)
        self.selection.clear()
        self.shape = Rectangle(
            start=self.viewportmapper.to_units_coords(event.pos()),
            color=self.drawcontext.color,
            bgcolor=self.drawcontext.bgcolor,
            bgopacity=self.drawcontext.bgopacity,
            linewidth=self.drawcontext.size,
            filled=self.drawcontext.filled)
        self.layerstack.current.append(self.shape)


class CircleTool(ShapeTool):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.layername = 'Circle'

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        if self.layerstack.is_locked or self.navigator.space_pressed:
            return
        if event.button() != QtCore.Qt.LeftButton:
            return
        if self.layerstack.current is None:
            self.model.add_layer(undo=False, name=self.layername)
        self.selection.clear()
        self.shape = Circle(
            start=self.viewportmapper.to_units_coords(event.pos()),
            color=self.drawcontext.color,
            bgcolor=self.drawcontext.bgcolor,
            bgopacity=self.drawcontext.bgopacity,
            linewidth=self.drawcontext.size,
            filled=self.drawcontext.filled)
        self.layerstack.current.append(self.shape)
