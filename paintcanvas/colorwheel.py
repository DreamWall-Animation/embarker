import math
from PySide6 import QtWidgets, QtCore, QtGui
from paintcanvas.qtutils import COLORS


CONICAL_GRADIENT = (
    (0.0, (0, 255, 255)),
    (0.16, (0, 0, 255)),
    (0.33, (255, 0, 255)),
    (0.5, (255, 0, 0)),
    (0.66, (255, 255, 0)),
    (0.83, (0, 255, 0)),
    (1.0, (0, 255, 255)))
TRANSPARENT = 0, 0, 0, 0
BLACK = 'black'
WHITE = 'white'


class ColorWheel(QtWidgets.QWidget):
    currentColorChanged = QtCore.Signal(QtGui.QColor)

    def __init__(self, color, parent=None):
        super(ColorWheel, self).__init__(parent)
        self.was_clicked = False
        self._is_clicked = False
        self._rect = QtCore.QRectF(50, 50, 150, 150)
        self._current_color = QtGui.QColor(color)
        self._color_point = QtCore.QPoint(100, 100)
        self._current_tool = None
        self._angle = 0
        self.setFixedSize(250, 250)
        self.initUI()

    def initUI(self):
        self._conicalGradient = QtGui.QConicalGradient(
            self.width() / 2, self.height() / 2, 180)
        for pos, (r, g, b) in CONICAL_GRADIENT:
            self._conicalGradient.setColorAt(pos, QtGui.QColor(r, g, b))

        top = self._rect.top()
        bottom = self._rect.top() + self._rect.height()
        self._vertical_gradient = QtGui.QLinearGradient(0, top, 0, bottom)
        self._vertical_gradient.setColorAt(0.0, QtGui.QColor(*TRANSPARENT))
        self._vertical_gradient.setColorAt(1.0, QtGui.QColor(BLACK))

        left = self._rect.left()
        right = self._rect.left() + self._rect.width()
        self._horizontal_gradient = QtGui.QLinearGradient(left, 0, right, 0)
        self._horizontal_gradient.setColorAt(0.0, QtGui.QColor(WHITE))

    def paintEvent(self, _):
        try:
            painter = QtGui.QPainter()
            painter.begin(self)
            self.paint(painter)
        except BaseException:
            pass  # avoid crash
            # TODO: log the error
        finally:
            painter.end()

    def mousePressEvent(self, event):
        tool = 'rect' if self._rect.contains(event.pos()) else 'wheel'
        self._current_tool = tool
        self.mouse_update(event)

    def mouseMoveEvent(self, event):
        self.was_clicked = True
        self._is_clicked = True
        self.mouse_update(event)

    def mouse_update(self, event):
        if self._current_tool == 'rect':
            self.color_point = event.pos()
        else:
            center = self._get_center()
            a = QtCore.QPoint(event.pos().x(), center.y())
            self._angle = get_absolute_angle_c(a=a, b=event.pos(), c=center)

        self.update()
        self.currentColorChanged.emit(self.current_color())

    def mouseReleaseEvent(self, event):
        self._is_clicked = False

    def paint(self, painter):
        painter.setRenderHint(QtGui.QPainter.Antialiasing)

        pen = QtGui.QPen(QtGui.QColor(0, 0, 0, 0))
        pen.setWidth(0)
        pen.setJoinStyle(QtCore.Qt.MiterJoin)

        painter.setBrush(self._conicalGradient)
        painter.setPen(pen)
        painter.drawRoundedRect(
            6, 6, (self.width() - 12), (self.height() - 12),
            self.width(), self.height())

        painter.setBrush(self.palette().color(QtGui.QPalette.Window))
        painter.drawRoundedRect(
            12.5, 12.5, (self.width() - 25), (self.height() - 25),
            self.width(), self.height())

        self._horizontal_gradient.setColorAt(
            1.0, self._get_current_wheel_color())
        painter.setBrush(self._horizontal_gradient)
        painter.drawRect(self._rect)

        painter.setBrush(self._vertical_gradient)
        painter.drawRect(self._rect)

        pen.setColor(QtGui.QColor(BLACK))
        pen.setWidth(3)
        painter.setPen(pen)

        pen.setWidth(5)
        pen.setCapStyle(QtCore.Qt.RoundCap)
        painter.setPen(pen)
        painter.drawPoint(self._color_point)

    @property
    def color_point(self):
        return self._color_point

    @color_point.setter
    def color_point(self, point):
        if point.x() < self._rect.left():
            x = self._rect.left()
        elif point.x() > self._rect.left() + self._rect.width():
            x = self._rect.left() + self._rect.width()
        else:
            x = point.x()

        if point.y() < self._rect.top():
            y = self._rect.top()
        elif point.y() > self._rect.top() + self._rect.height():
            y = self._rect.top() + self._rect.height()
        else:
            y = point.y()

        self._color_point = QtCore.QPoint(x, y)

    def _get_current_wheel_color(self):
        degree = 360 - self._angle
        return QtGui.QColor(*degree_to_color(degree))

    def _get_center(self):
        return QtCore.QPoint(self.width() / 2, self.height() / 2)

    def current_color(self):
        point = get_relative_point(self._rect, self.color_point)
        x_factor = 1.0 - (float(point.x()) / self._rect.width())
        y_factor = 1.0 - (float(point.y()) / self._rect.height())
        r, g, b, _ = self._get_current_wheel_color().getRgb()

        # fade to white
        differences = 255.0 - r, 255.0 - g, 255.0 - b
        r += round(differences[0] * x_factor)
        g += round(differences[1] * x_factor)
        b += round(differences[2] * x_factor)

        # fade to black
        r = round(r * y_factor)
        g = round(g * y_factor)
        b = round(b * y_factor)

        return QtGui.QColor(r, g, b)

    def set_current_color(self, color):
        [r, g, b] = color.getRgb()[:3]
        self._angle = 360.0 - (QtGui.QColor(r, g, b).getHslF()[0] * 360.0)
        self._angle = self._angle if self._angle != 720.0 else 0

        max_val = min(255, max(r, g, b))
        min_val = max(0, min(r, g, b))
        x_factor = (max_val - min_val) / float(max_val) if max_val > 0 else 0.0
        y_factor = (255.0 - max_val) / 255.0
        x = self._rect.left() + round(self._rect.width() * x_factor)
        y = self._rect.top() + round(self._rect.height() * y_factor)

        self._current_color = color
        self._color_point = QtCore.QPoint(x, y)
        self.update()


def get_relative_point(rect, point):
    x = point.x() - rect.left()
    y = point.y() - rect.top()
    return QtCore.QPoint(x, y)


def get_quarter(a, b, c):
    quarter = None
    if b.y() <= a.y() and b.x() < c.x():
        quarter = 0
    elif b.y() < a.y() and b.x() >= c.x():
        quarter = 1
    elif b.y() >= a.y() and b.x() > c.x():
        quarter = 2
    elif b.y() >= a.y() and b.x() <= c.x():
        quarter = 3
    return quarter


def degree_to_color(degree):
    if degree is None:
        return None
    degree = degree / 360.0

    r, g, b = 255.0, 255.0, 255.0
    contain_red = (
        (degree >= 0.0 and degree <= 0.33)
        or (degree >= 0.66 and degree <= 1.0))

    if contain_red:
        if degree >= 0.66 and degree <= 0.83:
            factor = degree - 0.66
            r = round(255 * (factor / .16))
        if ((degree > 0.0 and degree < 0.16) or (degree > 0.83 and degree < 1.0)):

            r = 255
        elif degree >= 0.16 and degree <= 0.33:
            factor = degree - 0.16
            r = 255 - round(255 * (factor / .16))
    else:
        r = 0
    r = min(r, 255)
    r = max(r, 0)

    # GREEN
    if degree >= 0.0 and degree <= 0.66:
        if degree <= 0.16:
            g = round(255.0 * (degree / .16))
        elif degree < 0.5:
            g = 255
        if degree >= 0.5:
            factor = degree - 0.5
            g = 255 - round(255.0 * (factor / .16))
    else:
        g = 0
    g = min(g, 255.0)
    g = max(g, 0)

    # BLUE
    if degree >= 0.33 and degree <= 1.0:
        if degree <= 0.5:
            factor = degree - 0.33
            b = round(255 * (factor / .16))
        elif degree < 0.83:
            b = 255.0
        if degree >= 0.83 and degree <= 1.0:
            factor = degree - 0.83
            b = 255.0 - round(255.0 * (factor / .16))
    else:
        b = 0
    b = min(b, 255)
    b = max(b, 0)
    return r, g, b


def get_point_on_line(angle, ray):
    x = 50 + ray * math.cos(float(angle))
    y = 50 + ray * math.sin(float(angle))
    return QtCore.QPoint(x, y)


def distance(a, b):
    x = (b.x() - a.x())**2
    y = (b.y() - a.y())**2
    return math.sqrt(abs(x + y))


def get_angle_c(a, b, c):
    return math.degrees(math.atan(distance(a, b) / distance(a, c)))


def get_absolute_angle_c(a, b, c):
    quarter = get_quarter(a, b, c)
    try:
        angle_c = get_angle_c(a, b, c)
    except ZeroDivisionError:
        return 360 - (90 * quarter)

    if quarter == 0:
        return round(180.0 + angle_c, 1)
    elif quarter == 1:
        return round(270.0 + (90 - angle_c), 1)
    elif quarter == 2:
        return round(angle_c, 1)
    elif quarter == 3:
        return math.fabs(round(90.0 + (90 - angle_c), 1))
