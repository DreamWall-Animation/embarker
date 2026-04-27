from PySide6 import QtWidgets, QtCore, QtGui
from paintcanvas.qtutils import pixmap, COLORS


class ComparingMediaTable(QtWidgets.QWidget):
    WIDTH = 50
    PADDING = 5

    def __init__(self, model, parent=None):
        super().__init__(parent=parent)
        self.model = model
        self.setMouseTracking(True)

    def set_model(self, model):
        self.model = model
        self.updatesize()
        self.repaint()

    def rects(self):
        width = self.WIDTH + (2 * self.PADDING)
        left, top = 0, 0
        rects = []
        for _ in self.model.imagestack:
            if left + width > self.width():
                left = 0
                top += width
            rect = QtCore.QRect(
                left + self.PADDING,
                top + self.PADDING,
                self.WIDTH,
                self.WIDTH)
            rects.append(rect)
            left += width
        return rects

    def updatesize(self):
        rects = self.rects()
        if not rects:
            self.setFixedHeight(8)
            return
        self.setFixedHeight(rects[-1].bottom() + self.PADDING)
        self.repaint()

    def resizeEvent(self, event):
        self.updatesize()

    def mousePressEvent(self, event):
        if event.button() != QtCore.Qt.LeftButton:
            return
        for i, rect in enumerate(self.rects()):
            if rect.contains(event.pos()):
                mime = QtCore.QMimeData()
                mime.setParent(self)
                data = QtCore.QByteArray()
                data.setNum(i)
                mime.setData('index', data)
                drag = QtGui.QDrag(self)
                drag.setMimeData(mime)
                drag.setHotSpot(event.pos())
                drag.exec_(QtCore.Qt.CopyAction)

    def mouseMoveEvent(self, _):
        self.repaint()

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing, True)
        painter.setPen(QtCore.Qt.transparent)
        color = QtGui.QColor(QtCore.Qt.black)
        color.setAlpha(25)
        painter.setBrush(color)
        painter.drawRoundedRect(event.rect(), self.PADDING, self.PADDING)
        painter.setRenderHint(QtGui.QPainter.Antialiasing, False)
        for rect, image in zip(self.rects(), self.model.imagestack):
            image = image.scaled(
                self.WIDTH,
                self.WIDTH,
                QtCore.Qt.KeepAspectRatio,
                QtCore.Qt.SmoothTransformation)
            image_rect = QtCore.QRect(
                0, 0, image.size().width(), image.size().height())
            image_rect.moveCenter(rect.center())
            painter.setPen(QtCore.Qt.transparent)
            painter.setBrush(QtCore.Qt.black)
            painter.drawRect(rect)
            painter.drawImage(image_rect, image)
            cursor = self.mapFromGlobal(QtGui.QCursor.pos())
            if rect.contains(cursor):
                painter.setPen(QtCore.Qt.yellow)
                color = QtGui.QColor(QtCore.Qt.white)
                color.setAlpha(50)
                painter.setBrush(color)
                painter.drawRect(rect)
                painter.setPen(QtCore.Qt.transparent)
        painter.end()

class Garbage(QtWidgets.QAbstractButton):
    removeIndex = QtCore.Signal(int)

    def __init__(self, parent):
        super().__init__(parent)
        self.icon = pixmap('garbage.png')
        self.setFixedSize(parent.iconSize())
        self.setAcceptDrops(True)
        self.refuse = False
        self.hover = False

    def dragEnterEvent(self, event):
        mime = event.mimeData()
        if not isinstance(mime.parent(), ComparingMediaTable):
            self.refuse = True
            self.repaint()
            return
        self.hover = True
        self.repaint()
        return event.accept()

    def dragLeaveEvent(self, _):
        self.release()

    def leaveEvent(self, _):
        self.release()

    def dropEvent(self, event):
        index = event.mimeData().data('index').toInt()[0]
        self.removeIndex.emit(index)
        self.release()

    def release(self):
        self.hover = False
        self.refuse = False
        self.repaint()

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.drawPixmap(self.rect(), self.icon)
        if self.hover:
            color = QtGui.QColor(QtCore.Qt.white)
            color.setAlpha(75)
        elif self.refuse:
            color = QtGui.QColor(QtCore.Qt.red)
            color.setAlpha(75)
        else:
            color = QtGui.QColor(QtCore.Qt.transparent)
        painter.setPen(QtCore.Qt.transparent)
        painter.setBrush(color)
        painter.drawRect(event.rect())
        painter.end()
