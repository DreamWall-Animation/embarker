from abc import abstractmethod
from PySide6 import QtCore


class ViewportMapper():
    @abstractmethod
    def __init__(self):
        pass

    @abstractmethod
    def apply_viewport_offset(self, offset: QtCore.QPointF):
        pass

    @abstractmethod
    def to_viewport(self, value: float) -> float:
        pass

    @abstractmethod
    def to_units(self, pixels: int) -> float:
        pass

    @abstractmethod
    def to_viewport_coords(self, units_point: QtCore.QRectF) -> QtCore.QRectF:
        pass

    @abstractmethod
    def to_units_coords(self, pixels_point: QtCore.QRectF) -> QtCore.QRectF:
        pass

    @abstractmethod
    def to_viewport_rect(self, units_rect: QtCore.QRectF) -> QtCore.QRectF:
        pass

    @abstractmethod
    def to_units_rect(self, pixels_rect: QtCore.QRectF) -> QtCore.QRectF:
        pass

    @abstractmethod
    def zoom_in(self, factor=10.0) -> float:
        pass

    @abstractmethod
    def zoom_out(self, factor=10.0) -> float:
        pass

    @abstractmethod
    def zoom_with_pivot(self, factor: float, pivot: QtCore.QPoint):
        pass

    @abstractmethod
    def set_zoom_with_pivot(self, factor: float, pivot: QtCore.QPoint):
        pass

    @abstractmethod
    def center_on_point(self, units_center: QtCore.QPointF) -> QtCore.QPointF:
        pass

    @abstractmethod
    def focus(self, units_rect: QtCore.QRectF) -> QtCore.QPointF:
        pass
