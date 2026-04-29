from PySide6 import QtCore
from paintcanvas.geometry import points_rect
from paintcanvas.shapes import (
    Arrow, Rectangle, Circle, Stroke, Bitmap, Text, Line, PStroke)
from paintcanvas.proceduralstroke import ProceduralStrokePoint


class Selection:
    NO = 0
    SUBOBJECTS = 1
    ELEMENT = 2

    def __init__(self):
        self.sub_elements = []
        self.element = None
        self.mode = 'replace'
        self._rect = None

    def get_rect(self, force_compute=False):
        # if self.mode == self.ELEMENT:
        #     if isinstance(self.element, )
        if self._rect is None or force_compute:
            self._rect = selection_rect(self)
        return self._rect

    def clear_cache(self):
        self._rect = None

    def set(self, elements):
        self._rect = None
        if isinstance(elements, Selection):
            self.element = elements.element
            self.sub_elements = elements.sub_elements
            return
        types = (
            QtCore.QPoint, QtCore.QPointF, PStroke, ProceduralStrokePoint,
            Arrow, Rectangle, Circle, Stroke, Bitmap, Text, Line)
        if isinstance(elements, types):
            self.sub_elements = []
            self.element = elements
            return
        if self.mode == 'add':
            return None if elements is None else self.add(elements)
        elif self.mode == 'replace':
            return self.clear() if elements is None else self.replace(elements)
        elif self.mode == 'invert':
            return None if elements is None else self.invert(elements)
        elif self.mode == 'remove':
            if elements is None:
                return
            for element in elements:
                if element in self.sub_elements:
                    self.remove(element)

    @property
    def type(self):
        if self.element is not None:
            return self.ELEMENT
        return self.SUBOBJECTS if self.sub_elements else self.NO

    def replace(self, elements):
        self._rect = None
        self.sub_elements = elements

    def add(self, elements):
        self._rect = None
        self.sub_elements.extend([s for s in elements if s not in self])

    def remove(self, shape):
        self._rect = None
        self.sub_elements.remove(shape)

    def invert(self, elements):
        self._rect = None
        for element in elements:
            if element not in self.sub_elements:
                self.add([element])
            else:
                self.remove(element)

    def clear(self):
        self._rect = None
        self.sub_elements = []
        self.element = None

    def __bool__(self):
        if isinstance(self.sub_elements, Selection):
            return True
        return bool(self.sub_elements) or bool(self.element)

    __nonzero__ = __bool__

    def __len__(self):
        return len(self.sub_elements)

    def __getitem__(self, i):
        return self.sub_elements[i]

    def __iter__(self):
        return self.sub_elements.__iter__()


def selection_rect(selection):
    if selection.type != selection.SUBOBJECTS:
        return
    points = []
    for element in selection:
        if isinstance(element, (QtCore.QPoint, QtCore.QPointF)):
            points.append(element)
        elif isinstance(element, ProceduralStrokePoint):
            points.append(QtCore.QPointF(element.center.x, element.center.y))
        elif isinstance(element, Stroke):
            points.extend(point for point, _ in element)
        elif isinstance(element, (Arrow, Rectangle, Circle, Text, Line)):
            points.extend((element.start, element.end))
        # elif isinstance(element, Bitmap):
        # TODO:
        #     points.extend((element.rect.topLeft(), element.bottomRight()))
        #     draw_bitmap(painter, element, viewportmapper)
    return points_rect(points)


