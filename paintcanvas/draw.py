import time
from PySide6 import QtGui, QtCore

from viewportmapper import ViewportMapper, NDCViewportMapper
from paintcanvas.shapes import (
    PStroke, Arrow, Circle, Stroke, Rectangle, Bitmap, Text, Line)

from paintcanvas.proceduralstroke import ProceduralStrokePoint
from paintcanvas.geometry import get_shape_rect, ensure_positive_rect
from paintcanvas.selection import selection_rect, Selection
from paintcanvas.model import CanvasModel


def draw_onion_skin(painter: QtGui.QPainter, onionskin, viewportmapper):
    rect = None
    for pixmap, opacity in onionskin:
        if pixmap is None or opacity == 0.0:
            continue
        if rect is None:
            pw, ph = pixmap.size().toTuple()
            uw, uh = viewportmapper.get_units_pixel_size().toTuple()
            width = pw * uw
            height = ph * uh
            rect = QtCore.QRectF(-width / 2, -height / 2, width, height)
            rect = viewportmapper.to_viewport_rect(rect)
        painter.setOpacity(opacity)
        pixmap = pixmap.scaled(rect.size().toSize())
        painter.drawPixmap(rect.toRect(), pixmap)


def draw_layer(
        painter: QtGui.QPainter, layer, blend_mode, opacity, viewportmapper):
    if not painter.isActive():
        return
    painter.setOpacity(opacity / 255)
    painter.setCompositionMode(blend_mode)
    for element in layer:
        draw_layer_element(painter, element, viewportmapper)
    painter.setOpacity(1)
    painter.setCompositionMode(QtGui.QPainter.CompositionMode_SourceOver)


def draw_layer_element(painter, element, viewportmapper, v=False):
    if isinstance(element, PStroke):
        if v is True:
            print("draw stroke")
        draw_pstroke(painter, element, viewportmapper)
    elif isinstance(element, Stroke):
        draw_stroke(painter, element, viewportmapper)
    elif isinstance(element, Arrow):
        draw_arrow(painter, element, viewportmapper)
    elif isinstance(element, Circle):
        draw_shape(painter, element, painter.drawEllipse, viewportmapper)
    elif isinstance(element, Rectangle):
        draw_shape(painter, element, painter.drawRect, viewportmapper)
    elif isinstance(element, Bitmap):
        draw_bitmap(painter, element, viewportmapper)
    elif isinstance(element, Text):
        draw_text(painter, element, viewportmapper)
    elif isinstance(element, Line):
        draw_line(painter, element, viewportmapper)


def _get_text_alignment_flags(alignment):
    return [
        (QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop),
        (QtCore.Qt.AlignRight | QtCore.Qt.AlignTop),
        (QtCore.Qt.AlignHCenter | QtCore.Qt.AlignTop),
        (QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter),
        (QtCore.Qt.AlignCenter),
        (QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter),
        (QtCore.Qt.AlignLeft | QtCore.Qt.AlignBottom),
        (QtCore.Qt.AlignHCenter | QtCore.Qt.AlignBottom),
        (QtCore.Qt.AlignRight | QtCore.Qt.AlignBottom)][alignment]


def draw_text(painter, text, viewportmapper):
    if not text.is_valid:
        return
    rect = get_shape_rect(text, viewportmapper)
    rect = ensure_positive_rect(rect)
    if text.filled:
        color = text.bgcolor if text.filled else QtCore.Qt.transparent
        color = QtGui.QColor(color)
        if text.bgopacity != 255:
            color.setAlpha(text.bgopacity)
        painter.setPen(QtCore.Qt.transparent)
        painter.setBrush(color)
        painter.drawRect(rect)

    painter.setBrush(QtCore.Qt.transparent)
    painter.setPen(QtGui.QColor(text.color))
    font = QtGui.QFont()
    size = viewportmapper.get_units_pixel_size().width()
    size = max((viewportmapper.to_viewport(text.text_size * size), 0.001))
    font.setPointSizeF(size)
    painter.setFont(font)
    alignment = _get_text_alignment_flags(text.alignment)
    option = QtGui.QTextOption()
    option.setWrapMode(QtGui.QTextOption.WrapAtWordBoundaryOrAnywhere)
    option.setAlignment(alignment)
    painter.drawText(rect, text.text, option)


def draw_bitmap(painter, bitmap, viewportmapper):
    painter.setBrush(QtCore.Qt.transparent)
    painter.setPen(QtCore.Qt.transparent)
    rect = viewportmapper.to_viewport_rect(bitmap.rect)
    painter.drawImage(rect, bitmap.image)


def draw_shape(painter, shape, drawer, viewportmapper):
    if not shape.is_valid:
        return
    color = QtGui.QColor(shape.color)
    pen = QtGui.QPen(color)
    pen.setCapStyle(QtCore.Qt.RoundCap)
    pen.setJoinStyle(QtCore.Qt.MiterJoin)
    linewidth = viewportmapper.get_units_pixel_size().width() * shape.linewidth
    pen.setWidthF(viewportmapper.to_viewport(linewidth))
    painter.setPen(pen)
    state = shape.filled
    if state:
        color = QtGui.QColor(shape.bgcolor)
        color.setAlpha(shape.bgopacity)
        painter.setBrush(color)
    else:
        painter.setBrush(QtGui.QColor(0, 0, 0, 0))
    rect = QtCore.QRectF(
        viewportmapper.to_viewport_coords(shape.start),
        viewportmapper.to_viewport_coords(shape.end))
    drawer(rect)


def draw_line(painter, line, viewportmapper):
    if not line.is_valid:
        return
    color = QtGui.QColor(line.color)
    pen = QtGui.QPen(color)
    pen.setCapStyle(QtCore.Qt.RoundCap)
    pen.setJoinStyle(QtCore.Qt.MiterJoin)
    linewidth = viewportmapper.get_units_pixel_size().width() * line.linewidth
    pen.setWidthF(viewportmapper.to_viewport(linewidth))
    painter.setPen(pen)
    painter.setBrush(color)
    qline = QtCore.QLineF(
        viewportmapper.to_viewport_coords(line.start),
        viewportmapper.to_viewport_coords(line.end))
    painter.drawLine(qline)


def draw_arrow(painter, arrow, viewportmapper):
    if not arrow.is_valid:
        return
    line = QtCore.QLineF(
        viewportmapper.to_viewport_coords(arrow.start),
        viewportmapper.to_viewport_coords(arrow.end))
    center = line.p2()
    degrees = line.angle()
    pixel_size = viewportmapper.get_units_pixel_size().width()
    offset = viewportmapper.to_viewport(arrow.headsize * pixel_size)
    triangle = QtGui.QPolygonF([
        QtCore.QPoint(center.x() - offset, center.y() - offset),
        QtCore.QPoint(center.x() + offset, center.y()),
        QtCore.QPoint(center.x() - offset, center.y() + offset),
        QtCore.QPoint(center.x() - offset, center.y() - offset)])

    transform = QtGui.QTransform()
    transform.translate(center.x(), center.y())
    transform.rotate(-degrees)
    transform.translate(-center.x(), -center.y())
    triangle = transform.map(triangle)
    path = QtGui.QPainterPath()
    path.setFillRule(QtCore.Qt.WindingFill)
    path.addPolygon(triangle)

    color = QtGui.QColor(arrow.color)
    pen = QtGui.QPen(color)
    pen.setCapStyle(QtCore.Qt.RoundCap)
    pen.setJoinStyle(QtCore.Qt.MiterJoin)
    pen.setWidthF(viewportmapper.to_viewport(arrow.linewidth * pixel_size))
    painter.setPen(pen)
    painter.setBrush(color)
    painter.drawLine(line)
    painter.drawPath(path)


def draw_pstroke(painter, stroke, viewportmapper):
    painter.setPen(QtCore.Qt.NoPen)
    color = QtGui.QColor(stroke.color)
    color.setAlpha(stroke.bgopacity)
    painter.setBrush(color)
    path = viewportmapper.to_viewport_path(stroke.procedurale_stroke.qpath)
    path.setFillRule(QtCore.Qt.WindingFill)
    painter.drawPath(path)


def draw_stroke(painter, stroke, viewportmapper):
    pen = QtGui.QPen(QtGui.QColor(stroke.color))
    pen.setCapStyle(QtCore.Qt.RoundCap)
    start = None
    for point, size in stroke:
        if start is None:
            start = viewportmapper.to_viewport_coords(point)
            continue
        pen.setWidthF(viewportmapper.to_viewport(size))
        painter.setPen(pen)
        end = viewportmapper.to_viewport_coords(point)
        painter.drawLine(start, end)
        start = end


def draw_element_selection(painter, selection, viewportmapper):
    rect = get_shape_rect(selection.element, viewportmapper)
    if rect is None:
        return
    painter.setRenderHint(QtGui.QPainter.Antialiasing, False)
    painter.setPen(QtCore.Qt.yellow)
    painter.setBrush(QtCore.Qt.NoBrush)
    painter.drawRect(rect)
    painter.setRenderHint(QtGui.QPainter.Antialiasing, True)


def draw_subobjects_selection(painter, selection, viewportmapper):
    painter.setRenderHint(QtGui.QPainter.Antialiasing, False)
    painter.setBrush(QtCore.Qt.yellow)
    painter.setPen(QtCore.Qt.black)
    if len(selection) < 1000:
        for element in selection:
            if isinstance(element, (QtCore.QPoint, QtCore.QPointF)):
                point = viewportmapper.to_viewport_coords(element)
                painter.drawRect(point.x() - 2, point.y() - 2, 4, 4)
            if isinstance(element, ProceduralStrokePoint):
                point = QtCore.QPointF(element.center.x, element.center.y)
                point = viewportmapper.to_viewport_coords(point)
                painter.drawRect(point.x() - 2, point.y() - 2, 4, 4)

    rect = viewportmapper.to_viewport_rect(selection_rect(selection))
    painter.setBrush(QtCore.Qt.transparent)
    painter.setPen(QtCore.Qt.black)
    painter.drawRect(rect)
    pen = QtGui.QPen(QtCore.Qt.white)
    pen.setWidth(1)
    pen.setStyle(QtCore.Qt.DashLine)
    offset = round((time.time() * 10) % 10, 3)
    pen.setDashOffset(offset)
    painter.setPen(pen)
    painter.drawRect(rect)
    painter.setRenderHint(QtGui.QPainter.Antialiasing, True)


def render_annotation(
        viewportmapper: ViewportMapper,
        painter: QtGui.QPainter = None,
        model: CanvasModel = None):
    painter.setRenderHint(QtGui.QPainter.Antialiasing)
    if model.wash_opacity:
        painter.setPen(QtCore.Qt.NoPen)
        color = QtGui.QColor(model.wash_color)
        color.setAlpha(model.wash_opacity)
        painter.setBrush(color)
        rect = QtCore.QRect(0, 0, *viewportmapper.view_size.toTuple())
        painter.drawRect(rect)
    for layer, _, blend_mode, _, visible, opacity in model.layerstack:
        if not visible:
            continue
        draw_layer(painter, layer, blend_mode, opacity, viewportmapper)


def draw_selection(painter, selection, viewportmapper):
    if selection.type == Selection.SUBOBJECTS:
        draw_subobjects_selection(painter, selection, viewportmapper)
    elif selection.type == Selection.ELEMENT:
        draw_element_selection(painter, selection, viewportmapper)


def create_selection_pixmap(model, selection, viewportmapper):
    pixmap = QtGui.QPixmap(viewportmapper.image_size)
    pixmap.fill(QtCore.Qt.transparent)
    painter = QtGui.QPainter(pixmap)
    ndc_viewportmapper = NDCViewportMapper(
        view_size=viewportmapper.image_size,
        image_size=viewportmapper.image_size)
    render_annotation(
        viewportmapper=ndc_viewportmapper,
        painter=painter,
        model=model)
    rect = selection.get_rect(force_compute=True)
    rect = ndc_viewportmapper.to_viewport_rect(rect)
    rect = ensure_positive_rect(rect)
    painter.end()
    return pixmap.copy(rect.toRect())