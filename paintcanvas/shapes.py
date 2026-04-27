import base64
from copy import deepcopy
from PySide6 import QtGui, QtCore


class Text:
    TYPE = 'text'
    TOP_LEFT = 0
    TOP_RIGHT = 1
    TOP_CENTER = 2
    CENTER_LEFT = 3
    CENTER = 4
    CENTER_RIGHT = 5
    BOTTOM_LEFT = 6
    BOTTOM_CENTER = 7
    BOTTOM_RIGHT = 8

    def __init__(
            self, start, text, color, bgcolor, bgopacity, text_size, filled):
        self.text = text
        self.start = start
        self.end = None
        self.color = color
        self.filled = filled
        self.bgcolor = bgcolor
        self.bgopacity = bgopacity
        self.text_size = text_size
        self.alignment = self.TOP_LEFT

    def handle(self, point):
        self.end = point

    @property
    def is_valid(self):
        return self.end is not None

    def copy(self):
        text = Text(
            self.start, self.text, self.color,
            self.bgcolor, self.bgopacity,
            self.text_size, self.filled)
        text.end = self.end
        text.alignment = self.alignment
        return text

    def serialize(self):
        return {
            'type': self.TYPE,
            'text': self.text,
            'start': self.start.toTuple(),
            'end': self.end.toTuple(),
            'color': self.color,
            'filled': self.filled,
            'bgcolor': self.bgcolor,
            'bgopacity': self.bgopacity,
            'text_size': self.text_size,
            'alignment': self.alignment}

    @staticmethod
    def deserialize(data):
        del data['type']
        alignment = data.pop('alignment')
        text = Text(**data)
        text.alignment = alignment
        return text


class Bitmap:
    TYPE = 'bitmap'

    def __init__(self, image: QtGui.QImage, rect):
        self.image = image
        self.rect = rect

    def offset(self, offset):
        self.rect.moveTopLeft(self.rect.topLef() + offset)

    def copy(self):
        return Bitmap(QtGui.QImage(self.image), QtCore.QRectF(self.rect))

    def serialize(self):
        byte_array = QtCore.QByteArray()
        buffer = QtCore.QBuffer(byte_array)
        buffer.open(QtCore.QIODevice.WriteOnly)
        self.image.save(buffer, 'PNG')
        image_data = base64.b64encode(byte_array.data()).decode('utf-8')
        return {
            'type': self.TYPE,
            'image': image_data,
            'rect': [
                *self.rect.topLeft().toTuple(),
                self.rect.width(),
                self.rect.height()]}

    @staticmethod
    def deserialize(data):
        image_data = base64.b64decode(data['image'])
        byte_array = QtCore.QByteArray(image_data)
        qimage = QtGui.QImage()
        qimage.loadFromData(byte_array, 'PNG')
        return Bitmap(
            image=qimage,
            rect=QtCore.QRectF(*data['rect']))


class Rectangle:
    TYPE = 'rectangle'

    def __init__(self, start, color, bgcolor, bgopacity, linewidth, filled):
        self.start = start
        self.end = None
        self.color = color
        self.filled = filled
        self.bgcolor = bgcolor
        self.bgopacity = bgopacity
        self.linewidth = linewidth

    def handle(self, point):
        self.end = point

    @property
    def is_valid(self):
        return self.end is not None

    def copy(self):
        rect = Rectangle(
            self.start, self.color, self.bgcolor, self.bgopacity,
            self.linewidth, self.filled)
        rect.end = self.end
        return rect

    def serialize(self):
        return {
            'type': self.TYPE,
            'start': self.start.toTuple(),
            'end': self.end.toTuple(),
            'color': self.color,
            'filled': self.filled,
            'bgcolor': self.bgcolor,
            'bgopacity': self.bgopacity,
            'linewidth': self.linewidth,}

    @classmethod
    def deserialize(cls, data):
        del data['type']
        end = QtCore.QPointF(*data.pop('end'))
        data['start'] = QtCore.QPointF(*data['start'])
        rectangle = cls(**data)
        rectangle.end = end
        return rectangle


class Circle(Rectangle):
    TYPE = 'circle'

    def copy(self):
        rect = Circle(
            self.start, self.color, self.bgcolor, self.bgopacity,
            self.linewidth, self.filled)
        rect.end = self.end
        return rect


class Line:
    TYPE = 'line'

    def __init__(self, start, color, linewidth):
        self.linewidth = linewidth
        self.color = color
        self.start = start
        self.end = None

    @property
    def line(self):
        return QtCore.QLineF(self.start, self.end)

    def handle(self, point):
        self.end = point

    @property
    def is_valid(self):
        return self.end is not None

    def copy(self):
        line = Line(self.start, self.color, self.linewidth)
        line.end = self.end
        return line

    def serialize(self):
        return {
            'type': self.TYPE,
            'linewidth': self.linewidth,
            'start': self.start.toTuple(),
            'end': self.end.toTuple(),
            'color': self.color}

    @staticmethod
    def deserialize(data):
        del data['type']
        end = QtCore.QPointF(*data.pop("end"))
        rectangle = Line(**data)
        rectangle.end = end
        return rectangle


class Arrow:
    TYPE = 'arrow'

    def __init__(self, start, color, linewidth):
        self.start = start
        self.end = None
        self.color = color
        self.linewidth = linewidth
        self.headsize = linewidth * 3

    @property
    def line(self):
        return QtCore.QLineF(self.start, self.end)

    def handle(self, point):
        self.end = point

    @property
    def is_valid(self):
        return self.end is not None

    def copy(self):
        arrow = Arrow(self.start, self.color, self.linewidth)
        arrow.end = self.end
        arrow.headsize = self.headsize
        return arrow

    def serialize(self):
        return {
            'type': self.TYPE,
            'linewidth': self.linewidth,
            'headsize': self.headsize,
            'start': self.start.toTuple(),
            'end': self.end.toTuple(),
            'color': self.color}

    @staticmethod
    def deserialize(data):
        del data['type']
        arrow = Arrow(
            start=QtCore.QPointF(*data['start']),
            color=data['color'],
            linewidth=data['linewidth'])
        arrow.end = QtCore.QPointF(*data['end'])
        arrow.headsize = data['headsize']
        return arrow

    def __repr__(self):
        return (
            f'Arrow: start:{self.start}, end:{self.end}, '
            f'{self.linewidth}, {self.headsize}')


class Stroke:
    TYPE = 'stroke'
    def __init__(self, start, color, size):
        self.points = [[start, size]]
        self.color = color

    def add_point(self, point, size):
        self.points.append([point, size])

    @property
    def is_valid(self):
        return len(self.points) > 1

    def __iter__(self):
        return self.points.__iter__()

    def __getitem__(self, index):
        return self.points[index]

    def __setitem__(self, index, value):
        self.points[index] = value

    def __len__(self):
        return len(self.points)

    def copy(self):
        stroke = Stroke(None, None, None)
        stroke.points = deepcopy(self.points)
        stroke.color = self.color
        return stroke

    def __repr__(self):
        return str(self.points)

    def serialize(self):
        return {
            'type': self.TYPE,
            'color': self.color,
            'points': [(p.toTuple(), s) for p, s in self.points]
        }

    @staticmethod
    def deserialize(data):
        stroke = Stroke(None, None, None)
        stroke.points = [(QtCore.QPointF(*p), s) for p, s in data['points']]
        stroke.color = data['color']
        return stroke


def deserialize_shape(data):
    cls = {
        'text': Text,
        'bitmap': Bitmap,
        'rectangle': Rectangle,
        'circle': Circle,
        'line': Line,
        'arrow': Arrow,
        'stroke': Stroke,
    }.get(data['type'])
    if cls is None:
        raise ValueError(f'Unkown shape type: {data["type"]}')
    return cls.deserialize(data)