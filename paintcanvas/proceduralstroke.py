import itertools
from functools import lru_cache
import math
from PySide6 import QtGui, QtCore
from dataclasses import dataclass


MINIMAL_VECTOR_DISTANCE = 3


class Vector2D:
    def __init__(self, x, y):
        self.x = round(x, 8)
        self.y = round(y, 8)

    def __repr__(self):
        return f"({self.x}, {self.y})"

    def __sub__(self, v2):
        return Vector2D(self.x - v2.x, self.y - v2.y)

    def __add__(self, v2):
        return Vector2D(self.x + v2.x, self.y + v2.y)

    def __mul__(self, scalar):
        if isinstance(scalar, Vector2D):
            return Vector2D(self.x * scalar.x, self.y * scalar.y)
        return Vector2D(self.x * scalar, self.y * scalar)

    def __div__(self, scalar):
        return Vector2D(self.x / scalar, self.y / scalar)

    def __eq__(self, v2):
        return self.x == v2.x and self.y == v2.y

    def __hash__(self):
        return hash((self.x, self.y))

    def normalized(self):
        length = self.length()
        if not length:
            return Vector2D(0, 0)
        return self * (1 / length)

    def length_squared(self):
        return self.x ** 2 + self.y ** 2

    def length(self):
        return math.sqrt((self.x * self.x) + (self.y * self.y))


def distance_between_vectors(v1, v2):
    return math.sqrt(((v2.x - v1.x)**2) + ((v2.y - v1.y)**2))


class ProceduralStroke:
    def __init__(
            self,
            pixel_ratio=None,
            threshold=MINIMAL_VECTOR_DISTANCE,
            parent=None):

        self.parent = parent
        self.brush_radius = 10
        self.pixel_ratio = Vector2D(*pixel_ratio) if pixel_ratio else None
        self.threshold = threshold
        self._points = []
        self._cache = []
        self._qpath = None
        self._inners_cache = []
        self._outers_cache = []
        self._tail: ProceduralStroke|None = None
        self._bbox = None
        self.startend = [None, None]

    def get_points(self):
        return self._points

    def __iter__(self):
        return self._points.__iter__()

    @property
    def bbox(self):
        return self._bbox

    @property
    def qpath(self):
        if self._qpath is None:
            self.create_qpath()
        return self._qpath

    @property
    def brush_width(self):
        return self.brush_radius * 2

    @brush_width.setter
    def brush_width(self, value):
        self.brush_radius = value / 2

    def serialize(self):
        return [(
            (p.center.x, p.center.y),
            p.pressure,
            p.inner_outline_radius,
            p.outer_outline_radius)
            for p in self._points]

    @staticmethod
    def deserialize(data):
        procedural_stroke = ProceduralStroke()
        for point in data:
            center = Vector2D(*point[0])
            psp = ProceduralStrokePoint(center, *point[1:])
            procedural_stroke.append(psp)
        return procedural_stroke

    def copy(self):
        procedural_stroke = ProceduralStroke()
        procedural_stroke.pixel_ratio = self.pixel_ratio
        procedural_stroke.brush_radius = self.brush_radius
        for p in self._points:
            procedural_stroke.append(
                ProceduralStrokePoint(
                    Vector2D(p.center.x, p.center.y),
                    p.pressure,
                    p.inner_outline_radius,
                    p.outer_outline_radius))
        procedural_stroke.cache_stroke()
        procedural_stroke.create_qpath()
        return procedural_stroke

    def tail(self):
        if not self._points:
            return None
        return self._points[-1]

    def append(self, point):
        point.stroke = self
        self._points.append(point)
        if self._bbox is None:
            self._bbox = [
                point.center.x,
                point.center.y,
                point.center.x + 0.001,
                point.center.y + 0.001]
            return
        self._bbox[0] = min((self._bbox[0], point.center.x))
        self._bbox[1] = min((self._bbox[1], point.center.y))
        self._bbox[2] = max((self._bbox[2], point.center.x))
        self._bbox[3] = max((self._bbox[3], point.center.y))

    def rebuild(self):
        points = self._points[:]
        self.clear()
        for i, point in enumerate(points):
            if i == 0:
                self.append(point)
                continue
            prev_point = points[i-1]
            dist = distance_between_vectors(prev_point.center, point.center)
            if dist < self.threshold:
                continue
            self._tail = point
            if dist < self.brush_radius * 0.1:
                continue
            self.append(point)
        self.close(point.center.x, point.center.y)
        self.cache_stroke()

    def set_tail(
            self, x, y, pressure, tilt: Vector2D):
        vector = Vector2D(x, y)
        tilt = tilt or Vector2D(0, 0)
        if self.size() == 0:
            point = ProceduralStrokePoint(
                vector, self.brush_radius * pressure, tilt.x, tilt.y)
            self._tail = point
            self.append(point)
            return

        dist = distance_between_vectors(self._points[-1].center, vector)
        direction = vector - self._points[-1].center
        angle = angle_between_vectors(tilt, direction)
        inner_mult = angle_to_radius_multiplier(angle)

        direction = self._points[-1].center - vector
        angle = angle_between_vectors(tilt, direction)
        outer_mult = angle_to_radius_multiplier(angle)

        stroke_point = ProceduralStrokePoint(
            vector,
            self.brush_radius * pressure,
            self.brush_radius * pressure * inner_mult,
            self.brush_radius * pressure * outer_mult)
        self._tail = stroke_point
        if dist < self.threshold or dist < self.brush_radius * 0.25:
            return
        self.append(stroke_point)

    def size(self):
        return len(self._points)

    def clear(self):
        self._points.clear()
        self._cache.clear()
        self._inners_cache.clear()
        self._outers_cache.clear()

    def get_cache(self):
        return self._cache

    def get_inner_outline_vector(self, index):
        previous_vector = self._get_previous_vector(index)
        next_vector = self._get_next_vector(index)
        current_point = self._points[index]
        positive = is_positive_side(
            previous_vector,
            next_vector,
            current_point.center)
        return get_offset_bisector(
            previous_vector, next_vector, current_point.center,
            current_point.inner_outline_radius, positive,
            self.pixel_ratio)

    def get_outer_outline_vector(self, index):
        previous_vector = self._get_previous_vector(index)
        next_vector = self._get_next_vector(index)
        current_point = self._points[index]
        positive = is_positive_side(
            previous_vector,
            next_vector,
            current_point.center)
        return get_offset_bisector(
            previous_vector, next_vector, current_point.center,
            current_point.outer_outline_radius, not positive,
            self.pixel_ratio)

    def _get_previous_vector(self, index):
        if 0 < index:
            return self._points[index - 1].center
        point = self._points[0]
        length = (point.inner_outline_radius + point.outer_outline_radius) / 2
        vector = opposite(point.center, self._points[1].center, length=length)
        vector.x += 0.001
        return vector

    def _get_next_vector(self, index):
        if index < len(self._points) - 1:
            return self._points[index + 1].center
        point = self._points[-1]
        length = (point.inner_outline_radius + point.outer_outline_radius) / 2
        vector = opposite(point.center, self._points[-2].center, length=length)
        vector.x += 0.001
        return vector

    def cache_stroke(self, clear_cache=False):
        if clear_cache:
            self._cache.clear()
            self._inners_cache.clear()
            self._outers_cache.clear()
        if self.size() < 2:
            return
        inner = self._inners_cache.copy()
        outer = self._outers_cache.copy()
        if self._tail:
            buffer_last_point = self._points[-1]
            self._points[-1] = self._tail
        for i in range(len(self._points)):
            if i < len(inner):
                continue
            inner_vector = self.get_inner_outline_vector(i)
            outer_vector = self.get_outer_outline_vector(i)
            inner.append(inner_vector)
            outer.append(outer_vector)
            if i < len(self._points) - 2:
                self._inners_cache.append(inner_vector)
                self._outers_cache.append(outer_vector)

        self._cache.clear()
        self._cache.append(self._get_previous_vector(0))
        self._cache.extend(inner)
        self._cache.append(self._get_next_vector(len(self._points) - 1))
        self._cache.extend(reversed(outer))
        self._cache.append(self._get_previous_vector(0))
        if self._tail:
            self._points[-1] = buffer_last_point
        self.create_qpath()
        return

    def close(self, x, y):
        if self.size() < 2:
            return
        self._points[-1].center.x = x
        self._points[-1].center.y = y
        self._tail = None

    def create_qpath(self):
        self._qpath = QtGui.QPainterPath()
        for i, vector in enumerate(self.get_cache()):
            qpoint = QtCore.QPointF(vector.x, vector.y)
            if i == 0:
                self._qpath.moveTo(qpoint)
                continue
            self._qpath.lineTo(qpoint)


@dataclass(slots=True)
class ProceduralStrokePoint:
    center: Vector2D
    pressure: float
    inner_outline_radius: float
    outer_outline_radius: float
    stroke: ProceduralStroke = None


def opposite(vector1: Vector2D, vector2: Vector2D, length: float):
    vector = vector1 - vector2
    if not vector.length():
        return Vector2D(0, 0)
    return vector1 + (vector.normalized() * length)


@lru_cache()
def get_offset_bisector(
    prev_vector, next_vector, center_vector, length,
    reverse=False, pixel_ratio=None):
    V1 = (center_vector - prev_vector).normalized()
    V2 = (center_vector - next_vector).normalized()
    V = (V1 + V2)

    if V.length() == 0:
        V = Vector2D(-V1.y, V1.x)

    V = V.normalized() * length
    if pixel_ratio:
        V = V * pixel_ratio
    if reverse:
        return center_vector - V
    return center_vector + V


@lru_cache()
def is_positive_side(v1, v2, v3):
    v1v2 = v2 - v1
    v1v3 = v3 - v1
    cross_product = (v1v2.x * v1v3.y) - (v1v2.y * v1v3.x)
    return cross_product >= 0


def angle_between_vectors(v1, v2):
    dot = v1.x * v2.x + v1.y * v2.y
    norm1 = v1.length()
    norm2 = v2.length()

    if norm1 == 0 or norm2 == 0:
        return 0.0

    cos_theta = dot / (norm1 * norm2)
    cos_theta = max(-1.0, min(1.0, cos_theta))

    angle_rad = math.acos(cos_theta)

    cross = v1.x * v2.y - v1.y * v2.x
    if cross < 0:
        angle_rad = -angle_rad

    return math.degrees(angle_rad)


def angle_to_radius_multiplier(angle: float) -> float:
    if angle < 0:
        return 1.0
    if angle <= 90:
        return 1.0 + angle / 90.0
    return 1.0 + (180.0 - angle) / 90.0
