import os
import uuid
from collections import defaultdict
from PySide6 import QtGui, QtCore

from viewportmapper import PixelViewportMapper
from paintcanvas.layerstack import LayerStack, unique_layer_name
from paintcanvas.shapes import split_pstroke, PStroke
from paintcanvas.qtutils import COLORS
from paintcanvas.selection import Selection
from paintcanvas.shapes import Bitmap


UNDOLIMIT = 50


class DrawContext:
    color = COLORS[0]
    bgcolor = COLORS[0]
    bgopacity = 255
    filled = False
    size = 5
    text_size = 50


class CanvasModel:
    GRID = 0
    STACKED = 1
    HORIZONTAL = 2
    VERTICAL = 3

    def __init__(self, viewportmapper=None, baseimage=None):
        self.locked = False
        self.id = str(uuid.uuid4())[:6]
        self.render_cache = None
        self.baseimage = baseimage or QtGui.QImage()
        size = self.baseimage.size()
        self.baseimage_wipes = QtCore.QRect(0, 0, size.width(), size.height())
        self.imagestack = []
        self.imagestack_wipes = []
        self.imagestack_layout = self.GRID
        self.comment = ''
        self.metadata = {}

        self.drawcontext = DrawContext
        self.layerstack = LayerStack()
        self.viewportmapper = viewportmapper or PixelViewportMapper()
        self.selection = Selection()

        self.wash_color = '#FFFFFF'
        self.wash_opacity = 0

        self.undostack = []
        self.redostack = []
        self.add_undo_state()

    def copy_selection(self):
        if self.selection.type == Selection.ELEMENT:
            return [self.selection.element.copy()]
        pstrokes = defaultdict(list)
        for point in self.selection:
            pstrokes[point.stroke.parent].append(point)
        result = []
        for pstroke, points in pstrokes.items():
            if len(points) == pstroke.procedurale_stroke.size():
                result.append(pstroke.copy())
                continue
            to_delete = [
                p for p in pstroke.procedurale_stroke.get_points() if
                p not in points]
            result.extend(p.copy() for p in split_pstroke(pstroke, to_delete))
        return result

    def paste(self, shapes):
        if not self.layerstack.layers:
            self.layerstack.add('Pasted data')
        for shape in shapes:
            self.layerstack.current.append(shape)
        self.add_undo_state()
        elements = []
        for shape in shapes:
            if not isinstance(shape, PStroke):
                elements.append(shape)
                continue
            elements.extend(shape.procedurale_stroke.get_points())
        self.selection.set(elements)

    def duplicate_selection(self):
        if not self.selection:
            return
        self.paste(self.copy_selection())

    @property
    def texts(self):
        return self.layerstack.texts

    def append_image(self, image: QtGui.QImage):
        self.imagestack.append(image)
        width, height = image.size().width(), image.size().height()
        self.imagestack_wipes.append(QtCore.QRect(0, 0, width, height))
        self.add_undo_state()

    def delete_image(self, index):
        del self.imagestack[index]
        del self.imagestack_wipes[index]
        self.add_undo_state()

    def duplicate_layer(self):
        if self.layerstack.current is None:
            return
        self.layerstack.duplicate_current()
        self.add_undo_state()

    def set_baseimage(self, image: QtGui.QImage):
        self.baseimage = image
        width, height = image.size().width(), image.size().height()
        self.baseimage_wipes = QtCore.QRect(0, 0, width, height)

    def add_layer(
            self, undo=True, name=None, locked=False, blend_mode=None,
            index=None):
        name = name or 'Layer'
        name = unique_layer_name(name, self.layerstack.names)
        self.layerstack.add(
            name, blend_mode=blend_mode, locked=locked, index=index)
        if undo:
            self.add_undo_state()

    def add_layer_image(self, path, blend_mode=None, undo=True):
        name = os.path.splitext(os.path.basename(path))[0]
        self.add_layer(undo=undo, name=name, blend_mode=blend_mode)
        image = QtGui.QImage(path)
        self.add_image(image)

    def add_image(self, image):
        # get viewport size rect
        size = self.viewportmapper.get_units_pixel_size()
        width = image.size().width() * size.width()
        height = image.size().height() * size.height()
        x = self.viewportmapper.origin.x()
        y = self.viewportmapper.origin.y()
        unit_rect = QtCore.QRectF(x, y, width, height)
        shape = Bitmap(image, unit_rect)
        self.add_shape(shape)
        self.add_undo_state()
        self.selection.set(shape)

    def move_layer(self, old_index, new_index):
        self.layerstack.move_layer(old_index, new_index)
        self.add_undo_state()

    def add_shape(self, shape):
        self.layerstack.current.append(shape)
        self.add_undo_state()

    def set_current_blend_mode_name(self, name):
        self.layerstack.set_current_blend_mode_name(name)
        self.add_undo_state()

    def add_undo_state(self):
        self.redostack = []
        wipes = [QtCore.QRectF(w) for w in self.imagestack_wipes]
        layers = self.layerstack.layers
        state = {
            'baseimage_wipes': QtCore.QRectF(self.baseimage_wipes),
            'imagestack': [QtGui.QImage(img) for img in self.imagestack],
            'imagestack_wipes': wipes,
            'layers': [[elt.copy() for elt in layer] for layer in layers],
            'locks': self.layerstack.locks.copy(),
            'opacities': self.layerstack.opacities.copy(),
            'blend_modes': self.layerstack.blend_modes.copy(),
            'names': self.layerstack.names.copy(),
            'visibilities': self.layerstack.visibilities.copy(),
            'current': self.layerstack.current_index,
            'wash_color': self.wash_color,
            'wash_opacity': self.wash_opacity
        }
        self.undostack.append(state)
        self.undostack = self.undostack[-UNDOLIMIT:]

    def restore_state(self, state):
        layers = [
            [elt.copy() for elt in layer if elt.is_valid]
            for layer in state['layers']]
        self.baseimage_wipes = state['baseimage_wipes']
        self.imagestack = state['imagestack']
        self.imagestack_wipes = state['imagestack_wipes']
        self.layerstack.layers = layers
        self.layerstack.locks = state['locks']
        self.layerstack.opacities = state['opacities']
        self.layerstack.names = state['names']
        self.layerstack.blend_modes = state['blend_modes']
        self.layerstack.visibilities = state['visibilities']
        self.layerstack.current_index = state['current']
        self.wash_color = state['wash_color']
        self.wash_opacity = state['wash_opacity']

    def undo(self):
        if len(self.undostack) < 2:
            return
        self.selection.clear()
        state = self.undostack.pop()
        self.redostack.append(state)
        state = self.undostack[-1] if self.undostack else self.default_state()
        self.restore_state(state)

    def redo(self):
        if not self.redostack:
            return
        state = self.redostack.pop()
        self.undostack.append(state)
        self.restore_state(state)

    def default_state(self):
        wipes = QtCore.QRectF(
            0, 0, self.baseimage.size().width(),
            self.baseimage.size().height())

        return {
            'baseimage_wipes': wipes,
            'imagestack': [],
            'imagestack_wipes': [],
            'blend_modes': [],
            'layers': [],
            'locks': [],
            'names': [],
            'opacities': [],
            'visibilities': [],
            'comment': '',
            'current': None,
            'wash_color': '#FFFFFF',
            'wash_opacity': 0,
        }

    def serialize(self):
        return {
            'wash_color': self.wash_color,
            'wash_opacity': self.wash_opacity,
            'comment': self.comment,
            'layerstack': self.layerstack.serialize(),
            'metadata': self.metadata
        }

    def deserialize(self, data):
        self.undostack = []
        self.redostack = []
        # use data.get for backward compatibility
        self.comment = data.get('comment', '')
        self.metadata = data.get('metadata', {})
        self.wash_color = data['wash_color']
        self.wash_opacity = data['wash_opacity']
        self.layerstack.deserialize(data['layerstack'])
        self.add_undo_state()

    def is_null(self):
        return (
            self.baseimage.isNull() and
            not any(self.layerstack.layers) and
            (not self.comment or self.comment == '(no text)'))
