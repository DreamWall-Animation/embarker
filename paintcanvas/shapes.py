import base64
import itertools
from dataclasses import replace
from copy import deepcopy
from PySide6 import QtGui, QtCore
from paintcanvas.proceduralstroke import ProceduralStroke, Vector2D


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
            self, start, text, color, bgcolor, bgopacity, text_size, filled,
            end=None, alignment=TOP_LEFT):

        self.text = text
        self.start: QtCore.QPointF = start
        self.end: QtCore.QPointF = end or QtCore.QPointF()
        self.color = color
        self.filled = filled
        self.bgcolor = bgcolor
        self.bgopacity = bgopacity
        self.text_size = text_size
        self.alignment = alignment

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
        data['start'] = QtCore.QPointF(*data['start'])
        data['end'] = QtCore.QPointF(*data['end'])
        return Text(**data)


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
        end = QtCore.QPointF(*data.pop('end'))
        start = QtCore.QPointF(*data.pop('start'))
        line = Line(start, **data)
        line.end = end
        return line


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


class PStroke:
    TYPE = 'p-stroke'

    def __init__(self, color, bgopacity, size, pixel_ratio, threshold=None):
        self.procedurale_stroke = ProceduralStroke(
            pixel_ratio, threshold, parent=self)
        self.procedurale_stroke.brush_width = size
        self.bgopacity = bgopacity
        self.color = color
        self.qpath = None

    def tail(self):
        psp = self.procedurale_stroke.tail()
        return QtCore.QPointF(psp.center.x, psp.center.y)

    def create_qpath(self):
        path = QtGui.QPainterPath()
        path.setFillRule(QtCore.Qt.WindingFill)
        for i, vector in enumerate(self.procedurale_stroke.get_cache()):
            qpoint = QtCore.QPointF(vector.x, vector.y)
            if i == 0:
                path.moveTo(qpoint)
                continue
            path.lineTo(qpoint)
        return path

    @property
    def is_valid(self):
        if self.procedurale_stroke is None:
            return False
        return 1 < self.procedurale_stroke.size()

    def serialize(self):
        ratio = self.procedurale_stroke.pixel_ratio
        return {
            'type': self.TYPE,
            'color': self.color,
            'bgopacity': self.bgopacity,
            'pixel_ratio': (ratio.x, ratio.y),
            'size': self.procedurale_stroke.brush_radius,
            'stroke': self.procedurale_stroke.serialize()}

    @staticmethod
    def deserialize(data):
        del data['type']
        stroke = PStroke(
            color=data['color'],
            bgopacity=data['bgopacity'],
            pixel_ratio=data['pixel_ratio'],
            size=data['size'])
        stroke.procedurale_stroke = ProceduralStroke.deserialize(
            data['stroke'])
        stroke.procedurale_stroke.brush_width = data['size']
        stroke.procedurale_stroke.pixel_ratio = Vector2D(*data['pixel_ratio'])
        stroke.procedurale_stroke.cache_stroke()
        stroke.procedurale_stroke.parent = stroke
        return stroke

    @property
    def rect(self):
        bbox = self.procedurale_stroke.bbox
        if not bbox:
            return
        return QtCore.QRect(
            bbox[0], bbox[1], bbox[2] - bbox[0], bbox[3], bbox[1])

    def copy(self):
        ratio = self.procedurale_stroke.pixel_ratio
        stroke = PStroke(
            color=self.color,
            bgopacity=self.bgopacity,
            size=self.procedurale_stroke.brush_radius,
            pixel_ratio=(ratio.x, ratio.y),
            threshold=self.procedurale_stroke.threshold)
        stroke.procedurale_stroke = self.procedurale_stroke.copy()
        stroke.procedurale_stroke.parent = stroke
        return stroke

    def __iter__(self):
        return iter(QtCore.QPointF(psp.center.x, psp.center.y) for psp in self.procedurale_stroke)


class Stroke:
    TYPE = 'stroke'
    def __init__(self, start, color, size):
        self.points = [[start, size]]
        self._bbox =  [start.x(), start.y(), start.x(), start.y()]
        self.color = color

    def add_point(self, point, size):
        self.points.append([point, size])
        self.update_bbox(point)

    def update_bbox(self, point):
        self._bbox[0] = min((self._bbox[0], point.x()))
        self._bbox[1] = min((self._bbox[1], point.y()))
        self._bbox[2] = max((self._bbox[2], point.x()))
        self._bbox[3] = max((self._bbox[3], point.y()))

    def compute_bbox(self):
        left, top, right, bottom = None, None, None, None
        for point, _ in self.points:
            left = point.x() if left is None else min((left, point.x()))
            top = point.y() if top is None else min((top, point.y()))
            right = point.x() if right is None else max((right, point.x()))
            bottom = point.y() if bottom is None else max((bottom, point.x()))
        self._bbox = [left, top, right, bottom]

    @property
    def rect(self):
        if self._bbox is None:
            return None
        return QtCore.QRectF(
            self._bbox[0],
            self._bbox[1],
            self._bbox[2] - self._bbox[0],
            self._bbox[3] - self._bbox[1])

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
        'p-stroke': PStroke,
        'stroke': Stroke,
    }.get(data['type'])
    if cls is None:
        raise ValueError(f'Unkown shape type: {data["type"]}')
    return cls.deserialize(data)


def split_pstroke(pstroke, pspoint_to_delete):
    current_array = []
    point_arrays = []

    # Split stroke points in multiple arrays
    for pspoint in pstroke.procedurale_stroke:
        if pspoint.stroke != pstroke.procedurale_stroke:
            continue
        if pspoint not in pspoint_to_delete:
            current_array.append(pspoint)
        elif current_array:
            point_arrays.append(current_array)
            current_array = []

    # Add last point array if missing
    if not current_array and not point_arrays:
        return []
    if not point_arrays or point_arrays[-1] is not current_array:
        point_arrays.append(current_array)

    # Create new PStroke from procedural points arrays
    strokes = []
    for point_array in point_arrays:
        if len(point_array) < 1:
            continue
        ratio = pstroke.procedurale_stroke.pixel_ratio
        stroke = PStroke(
            color=pstroke.color,
            bgopacity=pstroke.bgopacity,
            size=pstroke.procedurale_stroke.brush_width,
            pixel_ratio=(ratio.x, ratio.y),
            threshold=pstroke.procedurale_stroke.threshold)
        for pspoint in point_array:
            stroke.procedurale_stroke.append(replace(pspoint))
        stroke.procedurale_stroke.cache_stroke()
        strokes.append(stroke)
    return strokes


def split_stroke_data(stroke, points):
    all_points = [p for p, _ in stroke]
    indexes = [
        i for (i, p1), p2 in itertools.product(enumerate(all_points), points)
        if p1 is p2]
    indexes = [i for i in range(len(stroke)) if i not in indexes]
    if not indexes:
        return []
    groups = []
    buff_index = None
    for index in indexes:
        if buff_index is None:
            group = [stroke[index]]
            buff_index = index
            continue
        if index - buff_index == 1:
            group.append(stroke[index])
            buff_index = index
            continue
        groups.append(group)
        group = []
        buff_index = index
    groups.append(group)
    return [group for group in groups if len(group) > 1]

