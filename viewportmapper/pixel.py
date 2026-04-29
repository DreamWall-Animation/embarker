from PySide6 import QtCore
from viewportmapper.abstract import ViewportMapper


class PixelViewportMapper(ViewportMapper):
    """
    Used to translate/map between:
        - abstract/data/units coordinates
        - viewport/display/pixels coordinates
    """
    def __init__(self, zoom=1.0, origin=None, view_size=None):
        self.zoom: float = zoom
        self.origin: QtCore.QPointF = (
            QtCore.QPointF(*origin) if origin else QtCore.QPointF(0, 0))
        # We need the viewport size to be able to center the view or to
        # automatically set zoom from selection:
        self.view_size = view_size or QtCore.QSize(300, 300)

    def apply_viewport_offset(self, offset: QtCore.QPointF):
        self.origin -= offset

    def to_viewport(self, value: float) -> float:
        return value * self.zoom

    def to_units(self, pixels: int) -> float:
        return pixels / self.zoom

    def to_viewport_coords(self, units_point: QtCore.QRectF) -> QtCore.QRectF:
        return QtCore.QPointF(
            self.to_viewport(units_point.x()) - self.origin.x(),
            self.to_viewport(units_point.y()) - self.origin.y())

    def to_units_coords(self, pixels_point: QtCore.QRectF) -> QtCore.QRectF:
        return QtCore.QPointF(
            self.to_units(pixels_point.x() + self.origin.x()),
            self.to_units(pixels_point.y() + self.origin.y()))

    def to_viewport_rect(self, units_rect: QtCore.QRectF) -> QtCore.QRectF:
        return QtCore.QRectF(
            (units_rect.left() * self.zoom) - self.origin.x(),
            (units_rect.top() * self.zoom) - self.origin.y(),
            units_rect.width() * self.zoom,
            units_rect.height() * self.zoom)

    def to_units_rect(self, pixels_rect: QtCore.QRectF) -> QtCore.QRectF:
        top_left = self.to_units_coords(pixels_rect.topLeft())
        width = self.to_units(pixels_rect.width())
        height = self.to_units(pixels_rect.height())
        return QtCore.QRectF(top_left.x(), top_left.y(), width, height)

    def get_units_pixel_size(self):
        return QtCore.QSizeF(1, 1)

    def get_pixel_size_ratio(self):
        return QtCore.QSizeF(1, 1)

    def get_viewport_pixel_size(self):
        # TODO
        raise NotImplementedError

    def set_viewport_pixel_size(self, size):
        # TODO
        raise NotImplementedError

    def zoom_in(self, factor=10.0) -> float:
        self.zoom += self.zoom * factor
        self.zoom = min(self.zoom, 5.0)

    def zoom_out(self, factor=10.0) -> float:
        self.zoom -= self.zoom * factor
        self.zoom = max(self.zoom, .025)

    def zoom_with_pivot(self, factor: float, pivot: QtCore.QPoint):
        abspoint = self.to_units_coords(pivot)
        if factor > 0:
            self.zoom_in(abs(factor))
        else:
            self.zoom_out(abs(factor))
        relcursor = self.to_viewport_coords(abspoint)
        vector = relcursor - pivot
        self.origin = self.origin + vector

    def set_zoom_with_pivot(self, factor: float, pivot: QtCore.QPoint):
        abspoint = self.to_units_coords(pivot)
        self.zoom = factor
        relcursor = self.to_viewport_coords(abspoint)
        vector = relcursor - pivot
        self.origin = self.origin + vector

    def center_on_point(self, units_center: QtCore.QPointF) -> QtCore.QPointF:
        """Given current zoom and viewport size, set the origin point."""
        self.origin = QtCore.QPointF(
            units_center.x() * self.zoom - self.view_size.width() / 2,
            units_center.y() * self.zoom - self.view_size.height() / 2)

    def focus(self, units_rect: QtCore.QRectF) -> QtCore.QPointF:
        self.zoom = min([
            float(self.view_size.width()) / units_rect.width(),
            float(self.view_size.height()) / units_rect.height()])
        self.zoom *= 0.8
        self.zoom = max(self.zoom, .1)
        self.center_on_point(units_rect.center())

    def from_ndc(
            self,
            image_width: int, image_height: int,
            origin: tuple[int],
            zoom: float):
        """
        In OpenGL: zoom 1 = fit to width, origin is the center
        With PixelViewportMapper: zoom 1 = 1unit=1pixel, origin is top right
        This translates OpenGL zoom & pan to PixelViewportMapper's space
        """
        vp_width = self.view_size.width()
        vp_height = self.view_size.height()

        # Zoom
        vp_zoom = vp_width / image_width * zoom
        # Origin (scale topleft from center):
        px_offset_x = origin[0] * (vp_width / 2)
        px_offset_y = -origin[1] * (vp_height / 2)
        origin_x = (image_width * vp_zoom - vp_width) / 2 - px_offset_x
        origin_y = (image_height * vp_zoom - vp_height) / 2 - px_offset_y

        # Set values
        self.zoom = vp_zoom
        self.origin.setX(origin_x)
        self.origin.setY(origin_y)

    def to_ndc(self, image_width, image_height) -> tuple[float, float, float]:
        """
        NDC = normalized device coordinates
        In OpenGL: zoom 1 = fit to width, origin is the center
        With PixelViewportMapper: zoom 1 = 1unit=1pixel, origin is top right
        This translates PixelViewportMapper's pan and zoom to OpenGL's space
        """
        w = self.view_size.width()
        h = self.view_size.height()
        z = self.zoom
        x = self.origin.x()
        y = self.origin.y()

        gl_zoom = (self.zoom * image_width) / w
        gl_origin_x = (x - (image_width * z - w) / 2) / (w / 2)
        gl_origin_y = (y - (image_height * z - h) / 2) / (h / 2)

        return gl_zoom, gl_origin_x, -gl_origin_y
