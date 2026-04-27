"""
NDC Mapper to match the following shader:
    #version 330 core
    in vec2 position;
    in vec2 texCoord;
    uniform float zoom;
    uniform vec2 origin;
    uniform vec2 aspect;
    out vec2 vTexCoord;
    void main() {
        vec2 scaled = position * zoom * aspect;
        gl_Position = vec4(scaled + origin, 0.0, 1.0);
        vTexCoord = texCoord;
    }
"""

from PySide6.QtCore import QPoint, QPointF, QRectF, QSize
from viewportmapper.abstract import ViewportMapper


class NDCViewportMapper(ViewportMapper):
    """
    Map OpenGL normalized units coordinates with Viewport pixel coordinates.

    Image size is used to get image ratio to fit to width OR height depending
    on viewport ratio.
    """
    def __init__(self, zoom=1.0, origin=None, view_size=None, image_size=None):

        self.zoom: float = zoom
        self.origin: QPointF = origin or QPointF(0, 0)

        self._view_size: QSize = QSize(1, 1)
        self.view_ratio: float = 1.0
        self._image_size: QSize = QSize(1, 1)
        self.image_ratio: float = 1.0
        self.image_widget_ratio: float = 1.0
        self.snap_to_width: bool = True
        self.aspect: QPointF = QPointF(1.0, 1.0)

        if view_size:
            self.view_size = view_size
        if image_size:
            self.image_size = image_size

    # Setters to cache values asked for every frames:
    @property
    def image_size(self) -> QSize:
        return self._image_size

    @image_size.setter
    def image_size(self, size: QSize):
        self._image_size = size
        self.image_ratio = size.width() / size.height()
        self.update_image_widget_ratio()

    @property
    def view_size(self) -> QSize:
        return self._view_size

    @view_size.setter
    def view_size(self, size: QSize):
        self._view_size = size
        self.view_ratio = size.width() / size.height()
        self.update_image_widget_ratio()

    def update_image_widget_ratio(self):
        aspect = self.view_ratio / self.image_ratio
        self.snap_to_width = aspect < 1.0
        if self.snap_to_width:
            self.view_half = self.view_size.width() / 2
            self.aspect = QPointF(1.0, aspect)
        else:
            self.view_half = self.view_size.height() / 2
            self.aspect = QPointF(1 / aspect, 1.0)

    def get_pixel_size(self):
        vs = self.view_size
        if self.snap_to_width:
            return vs.width() / self.image_size.width() * self.zoom
        else:
            return vs.height() / self.image_size.height() * self.zoom

    def set_pixel_size(self, size):
        vs = self.view_size
        if self.snap_to_width:
            self.zoom = self.image_size.width() / vs.width() * size
        else:
            self.zoom = self.image_size.height() / vs.height() * size

    # Viewport conversions methods:
    def to_viewport(self, value: float) -> float:
        return value * self.view_half * self.zoom

    def to_units(self, pixels_value: int) -> float:
        return pixels_value / self.view_half / self.zoom

    def to_units_vector(self, vector: QPointF) -> float:
        if self.snap_to_width:
            return QPointF(
                vector.x() / self.view_half,
                -vector.y() / self.view_half * self.image_ratio)
        else:
            return QPointF(
                vector.x() / self.view_half / self.image_ratio,
                -vector.y() / self.view_half)

    def to_viewport_coords(self, pos: QPointF) -> QPointF:
        """
        Convert from shader-space units to viewport (pixel) coordinates.
        (0,0) is top-left in the viewport.
        """
        # Shader step: scaled = pos * zoom * aspect + origin
        x = (pos.x() * self.zoom * self.aspect.x()) + self.origin.x()
        y = (pos.y() * self.zoom * self.aspect.y()) + self.origin.y()

        # Map from [-1, 1] NDC to [0, 1]
        normalized = QPointF(
            (x + 1.0) * 0.5,
            (y + 1.0) * 0.5)

        # Convert to pixel coords and flip Y
        x_px = normalized.x() * self.view_size.width()
        y_px = (1.0 - normalized.y()) * self.view_size.height()

        return QPointF(x_px, y_px)

    def to_units_coords(self, viewport_pos: QPointF) -> QPointF:
        """
        Convert from viewport (pixel) coordinates to shader-space units.
        (0,0) is top-left in the viewport.
        """
        # Normalize to [0, 1]
        norm_x = viewport_pos.x() / self.view_size.width()
        norm_y = 1.0 - (viewport_pos.y() / self.view_size.height())  # flip Y

        # Map to [-1, 1]
        ndc_x = norm_x * 2.0 - 1.0
        ndc_y = norm_y * 2.0 - 1.0

        # Reverse the shader transform
        units_x = (ndc_x - self.origin.x()) / (self.zoom * self.aspect.x())
        units_y = (ndc_y - self.origin.y()) / (self.zoom * self.aspect.y())

        return QPointF(units_x, units_y)

    def to_viewport_rect(self, units_rect: QRectF) -> QRectF:
        top_left = self.to_viewport_coords(units_rect.topLeft())
        bottom_right = self.to_viewport_coords(units_rect.bottomRight())
        return QRectF(top_left, bottom_right)

    def to_units_rect(self, pixels_rect: QRectF) -> QRectF:
        top_left = self.to_units_coords(pixels_rect.topLeft())
        bottom_right = self.to_units_coords(pixels_rect.bottomRight())
        return QRectF(top_left, bottom_right)

    # Navigation methods
    def apply_viewport_offset(self, pixel_offset: QPoint):
        self.origin += self.to_units_vector(pixel_offset)

    def zoom_in(self, factor=10.0) -> float:
        self.zoom += self.zoom * factor
        self.zoom = min(self.zoom, 5.0)
        if 0.9 < self.zoom < 1.1:
            self.zoom = 1.0

    def zoom_out(self, factor=10.0) -> float:
        self.zoom -= self.zoom * factor
        self.zoom = max(self.zoom, .025)
        if 0.9 < self.zoom < 1.1:
            self.zoom = 1.0

    def zoom_with_pivot(
            self, factor: float, viewport_pivot: QPoint, relative=True):
        """
        Zoom using a viewport pivot point, such that the point under the cursor
        remains in place.
        """
        # Convert viewport pivot to shader-space coordinates before zooming
        units_before = self.to_units_coords(viewport_pivot)

        # Apply zoom
        if relative:
            if factor > 0:
                self.zoom_in(abs(factor))
            else:
                self.zoom_out(abs(factor))
        else:
            self.zoom = factor

        # Convert the same shader-space point back to new viewport coordinates
        # after zoom:
        new_viewport_pos = self.to_viewport_coords(units_before)

        # Compute the difference and apply as an offset to origin
        offset = viewport_pivot - new_viewport_pos
        self.origin += self.to_units_vector(offset)

    def set_zoom_with_pivot(self, factor: float, viewport_pivot: QPoint):
        self.zoom_with_pivot(factor, viewport_pivot, relative=False)

    def focus(self, units_rect: QRectF) -> QPointF:
        self.zoom = min([
            self.view_size.width() / units_rect.width(),
            self.view_size.height() / units_rect.height()])
        self.zoom *= 0.8
        self.zoom = max(self.zoom, .1)
        self.origin = units_rect.center()


if __name__ == '__main__':
    vm = NDCViewportMapper()
    vm.view_size = QSize(400, 400)
    vm.image_size = QSize(800, 400)

    assert vm.origin.x() == 0
    assert vm.get_pixel_size() == 0.5

    assert vm.to_viewport(1) == 200
    assert vm.to_units(400) == 2

    assert vm.to_units_coords(QPoint(200, 200)) == QPointF(0, 0)
    assert vm.to_units_coords(QPointF(0, 100)) == QPointF(-1, 1)

    assert vm.to_viewport_coords(QPointF(0, 0)) == QPointF(200, 200)
    assert vm.to_viewport_coords(QPointF(-1, -1)) == QPointF(0, 300)

    vm.set_pixel_size(1)
    assert vm.get_pixel_size() == 1

    # Change origin (-1;-1 = left;bottom)
    vm.zoom = 1
    vm.origin = QPointF(0.5, 0.5)
    assert vm.to_units_coords(QPointF(200, 200)) == QPointF(-.5, -1.0)

    # Change zoom
    vm.origin = QPointF(0, 0)
    assert vm.to_viewport(1) == 200
    vm.zoom = .5
    assert vm.to_viewport(1) == 100
    assert vm.to_units_coords(QPointF(200, 200)) == QPointF(0, 0)
    assert vm.to_units_coords(QPoint(0, 0)) == QPointF(-2, 4)
    assert vm.to_units_coords(QPoint(350, 350)) == QPointF(1.5, -3)

    # Change origin with zoom
    vm.origin = QPointF(1, -1)
    vm.zoom = .5
    assert vm.to_units_coords(QPointF(400, 400)) == QPointF(0, 0)
    assert vm.to_units_coords(QPointF(200, 200)) == QPointF(-2, 4)
