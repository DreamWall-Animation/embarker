from PySide6 import QtCore, QtGui
from paintcanvas.navigator import Navigator
from paintcanvas.layerstack import LayerStack
from paintcanvas.selection import Selection
from viewportmapper import ViewportMapper


class BaseTool:
    """
    This baseclass is only there to avoid reimplement unused method in each
    children. This is NOT doing anything.
    """

    def __init__(self, canvas=None):
        self.canvas = canvas
        self.is_dirty = False

    @property
    def drawcontext(self):
        return self.model.drawcontext

    @property
    def layerstack(self) -> LayerStack:
        return self.model.layerstack

    @property
    def navigator(self) -> Navigator:
        return self.canvas.navigator

    @property
    def selection(self) -> Selection:
        return self.model.selection

    @property
    def viewportmapper(self) -> ViewportMapper:
        return self.model.viewportmapper

    @property
    def model(self):
        return self.canvas.model

    def keyPressEvent(self, event):
        ...

    def keyReleaseEvent(self, event):
        ...

    def mousePressEvent(self, event):
        ...

    def mouseMoveEvent(self, event):
        ...

    def mouseReleaseEvent(self, event) -> bool:
        "Record an undo state if it returns True."
        ...

    def mouseWheelEvent(self, event):
        ...

    def tabletMoveEvent(self, event):
        ...

    def wheelEvent(self, event):
        ...

    def draw(self, painter):
        ...

    def window_cursor_visible(self):
        return True

    def window_cursor_override(self):
        return


class NavigationTool(BaseTool):
    """
    This is the main tool to navigate in scene. This can be subclassed for
    advanced tools which would keep the navigation features.
    """

    def mouseMoveEvent(self, event):
        zooming = self.navigator.shift_pressed and self.navigator.alt_pressed
        if zooming:
            offset = self.navigator.mouse_offset(event.pos())
            if offset is not None and self.navigator.zoom_anchor:
                factor = (offset.x() + offset.y()) / 10
                self.zoom(factor, self.navigator.zoom_anchor)
                self.canvas.panzoom_changed.emit()
                return True
        navigate = (
            self.navigator.left_pressed and self.navigator.space_pressed or
            self.navigator.center_pressed)
        if navigate:
            viewport_offset = self.navigator.mouse_offset(event.pos())
            if viewport_offset is not None:
                self.viewportmapper.apply_viewport_offset(viewport_offset)
                self.canvas.panzoom_changed.emit()
            return True
        return False

    def wheelEvent(self, event):
        factor = .15 if event.angleDelta().y() > 0 else -.15
        self.viewportmapper.zoom_with_pivot(factor, event.position())
        self.canvas.panzoom_changed.emit()

    def tabletMoveEvent(self, event):
        return self.mouseMoveEvent(event)

    def window_cursor_visible(self):
        return True

    def window_cursor_override(self):
        space = self.navigator.space_pressed
        left = self.navigator.left_pressed
        center = self.navigator.center_pressed
        if center:
            return QtCore.Qt.ClosedHandCursor
        if space and not left:
            return QtCore.Qt.OpenHandCursor
        if space and left:
            return QtCore.Qt.ClosedHandCursor


class NavigationScrubTool(NavigationTool):
    def __init__(self, canvas):
        super().__init__(canvas)
        self.offset = 0

    def mousePressEvent(self, event):
        self.offset = 0
        return super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if super().mouseMoveEvent(event):
            return
        if self.navigator.left_pressed:
            offset = self.navigator.mouse_offset(event.position())
            if not offset:
                return
            self.offset += offset.x()
            if 2 < self.offset:
                self.canvas.scrub.emit(1)
                self.offset = 0
            elif self.offset < -2:
                self.canvas.scrub.emit(-1)
                self.offset = 0
            if event.pos().x() < 0:
                point = QtCore.QPoint(self.canvas.width(), event.y())
                point = self.canvas.mapToGlobal(point)
                QtGui.QCursor.setPos(point)
            elif self.canvas.width() < event.pos().x():
                point = QtCore.QPoint(0, event.y())
                point = self.canvas.mapToGlobal(point)
                QtGui.QCursor.setPos(point)
