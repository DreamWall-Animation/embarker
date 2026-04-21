
from PySide6 import QtCore
from PySide6.QtGui import QPainter
from paintcanvas.shapes import (
    PStroke, Stroke, Arrow, Rectangle, Circle, Bitmap, Text, Line,
    deserialize_shape)
from paintcanvas.mathutils import distance_qline_qpoint


THRESHOLD = 1
UNDOLIMIT = 30
BLEND_MODE_NAMES = {
    QPainter.CompositionMode_Clear: 'Clear',
    QPainter.CompositionMode_ColorBurn: 'Colorburn',
    QPainter.CompositionMode_ColorDodge: 'Colordodge',
    QPainter.CompositionMode_Darken: 'Darken',
    QPainter.CompositionMode_Destination: 'Destination',
    QPainter.CompositionMode_DestinationAtop: 'Destination Atop',
    QPainter.CompositionMode_DestinationIn: 'Destination In',
    QPainter.CompositionMode_DestinationOut: 'Destination Out',
    QPainter.CompositionMode_DestinationOver: 'Destination Over',
    QPainter.CompositionMode_Difference: 'Difference',
    QPainter.CompositionMode_Exclusion: 'Exclusion',
    QPainter.CompositionMode_HardLight: 'Hardlight',
    QPainter.CompositionMode_Lighten: 'Lighten',
    QPainter.CompositionMode_Multiply: 'Multiply',
    QPainter.CompositionMode_Overlay: 'Overlay',
    QPainter.CompositionMode_Plus: 'Plus',
    QPainter.CompositionMode_Screen: 'Screen',
    QPainter.CompositionMode_SoftLight: 'Softlight',
    QPainter.CompositionMode_Source: 'Source',
    QPainter.CompositionMode_SourceAtop: 'Source Atop',
    QPainter.CompositionMode_SourceIn: 'Source In',
    QPainter.CompositionMode_SourceOut: 'Source Out',
    QPainter.CompositionMode_SourceOver: 'Source Over',
    QPainter.CompositionMode_Xor: 'Xor',
}
BLEND_MODE_FOR_NAMES = {v: k for k, v in BLEND_MODE_NAMES.items()}


class LayerStack:
    def __init__(self):
        super().__init__()
        self.layers = []
        self.locks = []
        self.names = []
        self.opacities = []
        self.blend_modes = []
        self.visibilities = []
        self.solo = None

        self.current_index = None

    def serialize(self):
        return {
            'type': 'layerstack',
            'layers': [[s.serialize() for s in layer] for layer in self.layers],
            'locks': self.locks,
            'names': self.names,
            'current_index': self.current_index,
            'opacities': self.opacities,
            'blend_modes': [BLEND_MODE_NAMES[bm] for bm in self.blend_modes],
            'visibilities': self.visibilities,
            'solo': self.solo}

    def deserialize(self, data):
        self.locks = data['locks']
        self.names = data['names']
        self.current_index = data['current_index']
        self.opacities = data['opacities']
        bms = [BLEND_MODE_FOR_NAMES[bm] for bm in data['blend_modes']]
        self.blend_modes = bms
        self.visibilities = data['visibilities']
        self.solor = data['solo']
        self.layers = [
            [deserialize_shape(s) for s in l] for l in data['layers']]

    @property
    def texts(self):
        return [
            shape.text for layer in self.layers for shape in layer
            if isinstance(shape, Text)]

    def add(
            self, name, blend_mode: QPainter.CompositionMode=None,
            locked=False, index=None):
        blend_mode = blend_mode or QPainter.CompositionMode_SourceOver
        if index is None:
            index = len(self.layers)
        self.layers.insert(index, [])
        self.locks.insert(index, locked)
        self.opacities.insert(index, 255)
        self.blend_modes.insert(index, blend_mode)
        self.names.insert(index, name)
        self.visibilities.insert(index, True)
        self.current_index = len(self.layers) - 1

    def duplicate_current(self):
        if self.current is None:
            return
        index = self.current_index
        new_layer = [shape.copy() for shape in self.current]
        self.layers.insert(index, new_layer)
        self.opacities.insert(index, self.opacities[index])
        self.blend_modes.insert(index, self.blend_modes[index])
        name = unique_layer_name(self.names[index], self.names)
        self.names.insert(index, name)
        self.visibilities.insert(index, self.visibilities[index])
        self.locks.insert(index, self.locks[index])

    @property
    def current_blend_mode_name(self):
        if self.current_index is None:
            return BLEND_MODE_NAMES[QPainter.CompositionMode_SourceOver]
        return BLEND_MODE_NAMES[self.blend_modes[self.current_index]]

    def set_current_blend_mode_name(self, name):
        if not self.current_index:
            return
        self.blend_modes[self.current_index] = BLEND_MODE_FOR_NAMES[name]

    @property
    def is_locked(self):
        if self.current_index is None:
            return False
        return self.locks[self.current_index]

    @property
    def current(self):
        if self.current_index is None:
            return
        return self.layers[self.current_index]

    def move_layer(self, old_index, new_index):
        if new_index > old_index:
            new_index -= 1
        self.layers.insert(new_index, self.layers.pop(old_index))
        self.locks.insert(new_index, self.locks.pop(old_index))
        self.names.insert(new_index, self.names.pop(old_index))
        self.blend_modes.insert(new_index, self.blend_modes.pop(old_index))
        self.opacities.insert(new_index, self.opacities.pop(old_index))
        self.visibilities.insert(new_index, self.visibilities.pop(old_index))
        self.current_index = new_index

    def remove(self, element):
        if self.current:
            self.current.remove(element)

    def delete(self, index=None):
        if not index and self.current:
            index = self.layers.index(self.current)
        if index is None:
            return
        if index != self.current_index:
            return
        self.layers.pop(index)
        self.visibilities.pop(index)
        self.opacities.pop(index)
        self.blend_modes.pop(index)
        self.locks.pop(index)
        self.names.pop(index)

        if not self.layers:
            self.current_index = None
            return
        self.current_index = index - 1

    def find_element_at(self, viewport_point, viewportmapper):
        if not self.current:
            return
        for layer in reversed(self.layers):
            for element in reversed(layer):
                if isinstance(element, (Arrow, Rectangle, Circle, Text, Line)):
                    for p in (element.start, element.end):
                        if is_point_hover_element(p, viewport_point, viewportmapper):
                            return p
                if is_point_hover_element(element, viewport_point, viewportmapper):
                    return element

    def __iter__(self):
        return zip(
            self.layers,
            self.names,
            self.blend_modes,
            self.locks,
            self.visibilities,
            self.opacities).__iter__()

    def __getitem__(self, index):
        return (
            self.layers[index],
            self.names[index],
            self.blend_modes[index],
            self.locks[index],
            self.visibilities[index],
            self.opacities[index])

    def __len__(self):
        return len(self.layers)


def is_point_hover_element(element, viewport_point, viewportmapper):
    if isinstance(viewport_point, QtCore.QPointF):
        viewport_point = viewport_point.toPoint()

    if isinstance(element, (QtCore.QPoint, QtCore.QPointF)):
        element = viewportmapper.to_viewport_coords(element)
        rect = QtCore.QRectF(element.x() - 10, element.y() - 10, 20, 20)
        return rect.contains(viewport_point)

    elif isinstance(element, Stroke):
        return is_point_hover_stroke(element, viewport_point, viewportmapper)

    elif isinstance(element, PStroke):
        return is_point_hover_pstroke(element, viewport_point, viewportmapper)

    elif isinstance(element, (Arrow, Line)):
        start = viewportmapper.to_viewport_coords(element.start)
        end = viewportmapper.to_viewport_coords(element.end)
        line = QtCore.QLineF(start, end)
        distance = distance_qline_qpoint(line, viewport_point)
        pixel = viewportmapper.get_units_pixel_size().width()
        return (
            distance <=
            viewportmapper.to_viewport(element.linewidth * pixel) + THRESHOLD)

    elif isinstance(element, Text):
        rect = QtCore.QRectF(element.start, element.end)
        rect = viewportmapper.to_viewport_rect(rect)
        return rect.contains(viewport_point)

    elif isinstance(element, Rectangle):
        rect = QtCore.QRectF(element.start, element.end)
        rect = viewportmapper.to_viewport_rect(rect)
        if element.filled:
            return rect.contains(viewport_point)
        lines = (
            (rect.topLeft(), rect.bottomLeft()),
            (rect.topLeft(), rect.topRight()),
            (rect.topRight(), rect.bottomRight()),
            (rect.bottomLeft(), rect.bottomRight()))
        for line in lines:
            line = QtCore.QLineF(*line)
            tshld = viewportmapper.to_viewport(element.linewidth) + THRESHOLD
            if distance_qline_qpoint(line, viewport_point) <= tshld:
                return True
        return False
    elif isinstance(element, Circle):
        # TODO
        return False
    elif isinstance(element, Bitmap):
        rect = viewportmapper.to_viewport_rect(element.rect)
        return rect.contains(viewport_point)


def is_point_hover_pstroke(stroke, viewport_point, viewportmapper):
    path = stroke.create_qpath()
    point = viewportmapper.to_units_coords(viewport_point)
    return path.contains(point)


def is_point_hover_stroke(stroke, viewport_point, viewportmapper):
    start = None
    for stroke_point, size in stroke:
        size = viewportmapper.to_viewport(size) + THRESHOLD
        stroke_point = viewportmapper.to_viewport_coords(stroke_point)
        if start is None:
            start = stroke_point
            continue
        end = stroke_point
        line = QtCore.QLineF(start, end)
        distance = distance_qline_qpoint(line, viewport_point)
        start = stroke_point
        if distance <= size:
            return True
    return False


def unique_layer_name(name, names):
    if name not in names:
        return name

    template = '{name} ({n})'
    i = 1
    while template.format(name=name, n=i) in names:
        i += 1
        continue
    return template.format(name=name, n=i)
