
from PySide6 import QtWidgets, QtCore, QtGui


class ZoomLabel(QtWidgets.QWidget):
    def __init__(self, canvas, parent=None):
        super().__init__(parent)
        self.setFixedSize(75, 25)
        self.canvas = canvas
        self.canvas.panzoom_changed.connect(self.update)
        self.clicked = False
        self.hovered = False
        self.setMouseTracking(True)

    def show_menu(self):
        menu = QtWidgets.QMenu()
        for size in (0.25, 0.5, 1, 1.5, 2, 3):
            action = QtGui.QAction(f'{round(size * 100)}%', self)
            action.size = size
            menu.addAction(action)
        action = menu.exec_(self.mapToGlobal(self.rect().bottomLeft()))
        if action:
            self.canvas.model.viewportmapper.set_pixel_size(action.size)
            self.canvas.panzoom_changed.emit()

    def enterEvent(self, event):
        self.hovered = True
        self.repaint()

    def mouseMoveEvent(self, event):
        self.hovered = self.rect().contains(event.pos())
        self.repaint()

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.clicked = True
            self.repaint()

    def mouseReleaseEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.show_menu()
            self.clicked = False
            self.repaint()

    def leaveEvent(self, event):
        self.hovered = False
        self.repaint()

    def paintEvent(self, _):
        painter = QtGui.QPainter(self)

        options = QtWidgets.QStyleOptionToolButton()
        options.initFrom(self)
        options.rect = self.rect()
        size = self.canvas.model.viewportmapper.get_pixel_size()
        options.text = f'{round(size * 100)}%'
        options.features = (
            QtWidgets.QStyleOptionToolButton.HasMenu)
        options.arrowType = QtCore.Qt.DownArrow

        if self.clicked:
            options.state = QtWidgets.QStyle.State_Sunken
        elif self.hovered:
            options.state = QtWidgets.QStyle.State_MouseOver
            rect = self.rect()
            rect.setWidth(rect.width() - 1)
            rect.setHeight(rect.height() - 1)
            painter.drawRect(rect)
        try:
            QtWidgets.QApplication.style().drawComplexControl(
                QtWidgets.QStyle.CC_ToolButton,
                options, painter, self)
        except RuntimeError:
            # Embed in some application, the style() is deleted and try to
            # reach it crash the entire app.
            pass
        finally:
            painter.drawText(self.rect(), QtCore.Qt.AlignCenter, options.text)
            painter.end()
