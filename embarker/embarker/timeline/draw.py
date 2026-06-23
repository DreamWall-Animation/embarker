from functools import lru_cache

from PySide6 import QtGui, QtCore

import embarker.commands as ebc
from embarker import preferences


SLIDER_HEIGHT = 22
HIGHLIGHT_Y = SLIDER_HEIGHT - 4
MARKER_Y = 8
ZOOM_HEIGHT = 2
BRACKET_TRIANGLE_SIZE = 4

BG_COLOR = QtGui.QColor('#232323')
BG_COLOR_ALT = QtGui.QColor('#151515')
SEPARATOR_COLOR = QtGui.QColor('#444444')
CURSORCOLOR = QtGui.QColor('#656565')
HIGHLIGHT_COLOR = QtGui.QColor('#0088FF')
HIGHLIGHT_COLOR.setAlpha(100)
MARKER_COLOR = QtGui.QColor('#999900')
BRACKET_COLOR = QtGui.QColor('#FFF')
ZOOM_COLOR = QtGui.QColor("#5b5b5c")
ZOOM_COLOR_ALT = QtGui.QColor("#7c7e82")

CURSOR_FIXED_WIDTH = 8
HIGHLIGHT_FIXED_WIDTH = 2
MARKER_FIXED_WIDTH = 1


@lru_cache
def get_rectangles(count, width, height=SLIDER_HEIGHT):
    return [QtCore.QRectF(i * width, 0, width, height) for i in range(count)]


def draw_slider(
        painter: QtGui.QPainter,
        full_rect: QtCore.QRect,
        display_frame_count: int,
        display_frame_start: int,
        current_frame: int,
        cached_values: list[int],  # highlighted values
        moving_frame: str | None,
        separators: list[int],
        thumbnails: dict):

    if display_frame_count == 0:
        painter.drawRect(full_rect)
        return

    width = full_rect.width()
    frame_width = width / display_frame_count

    if frame_width > 4:
        draw_expanded_slider(
            painter=painter,
            full_rect=full_rect,
            frame_width=frame_width,
            display_frame_start=display_frame_start,
            display_frame_count=display_frame_count,
            current_frame=current_frame,
            highlighted_values=cached_values,
            moving_frame=moving_frame,
            separators=separators,
            thumbnails=thumbnails,
        )

    else:
        draw_contracted_slider(
            painter=painter,
            full_rect=full_rect,
            frame_width=frame_width,
            display_frame_start=display_frame_start,
            display_frame_count=display_frame_count,
            current_frame=current_frame,
            highlighted_values=cached_values,
            moving_frame=moving_frame,
            separators=separators,
            thumbnails=thumbnails,
        )


def draw_expanded_slider(
        painter: QtGui.QPainter,
        full_rect: QtCore.QRect,
        frame_width: int,
        display_frame_start: int,
        display_frame_count: int,
        current_frame: int,
        highlighted_values: list[int],
        moving_frame: str | None,
        separators: list[int],
        thumbnails: dict):

    session = ebc.get_session()
    annotations = session.get_annotations_by_frames()

    if thumbnails:
        start = 0
        separators.append(display_frame_count)
        for i, separator in enumerate(separators[:-1]):
            pixmap = thumbnails[separator]
            brush = QtGui.QBrush()
            brush.setTexture(pixmap[0])
            painter.setBrush(brush)

            separator -= display_frame_start
            left_rect = frame_width * separator
            right_rect = frame_width * (separators[i+1] - start)
            rect = QtCore.QRectF(
                left_rect, full_rect.top(), right_rect, full_rect.height())
            painter.drawRect(rect)
            start = separator

    height = int(preferences.get('timeline_height', 0)) or SLIDER_HEIGHT
    highlight_height = height - 4
    rectangles = get_rectangles(display_frame_count, frame_width, height)
    for i, value_rect in enumerate(rectangles):
        # Drawn checkered pattern
        absolute_frame = i + display_frame_start
        if not thumbnails:
            painter.setPen(QtCore.Qt.PenStyle.NoPen)
            color = BG_COLOR if i % 2 else BG_COLOR_ALT
            painter.setBrush(color)
            painter.drawRect(value_rect)

        # Draw marker frames
        if absolute_frame in annotations:
            annotation = ebc.get_session().get_annotation_at(absolute_frame)
            if annotation:
                metadata = annotation.metadata
                painter.setBrush(
                    QtGui.QColor(metadata.get('user_color')
                                 if metadata and metadata.get('user_color')
                                 else MARKER_COLOR))
            painter.drawRect(value_rect.adjusted(0, 0, 0, 0))

        # Draw highlighted frames
        if absolute_frame in highlighted_values:
            painter.setBrush(HIGHLIGHT_COLOR)
            painter.setPen(QtCore.Qt.PenStyle.NoPen)
            painter.drawRect(value_rect.adjusted(0, highlight_height, 0, 0))

        # Draw separators
        if absolute_frame in separators:
            painter.setPen(QtGui.QColor(SEPARATOR_COLOR))
            painter.setBrush(QtGui.QColor(SEPARATOR_COLOR))
            painter.drawLine(value_rect.topLeft(), value_rect.bottomLeft())
            left = value_rect.left() + 2
            topleft = QtCore.QPointF(left, value_rect.top())
            bottomleft = QtCore.QPointF(left, value_rect.bottom())
            painter.drawLine(topleft, bottomleft)

        # Draw current frame
        if absolute_frame == current_frame:
            CURSORCOLOR.setAlpha(255)
            if thumbnails:
                CURSORCOLOR.setAlpha(150)
            pen = (QtGui.QPen(CURSORCOLOR) if i in annotations
                   else QtCore.Qt.NoPen)
            brush = (QtCore.Qt.NoBrush
                     if i in annotations else QtGui.QBrush(CURSORCOLOR))
            painter.setPen(pen)
            painter.setBrush(brush)
            painter.drawRect(value_rect)

            # If moving an annotations, take its color
            if moving_frame:
                painter.setBrush(QtGui.QColor(moving_frame))
                painter.drawRect(value_rect.adjusted(0, 0, 0, 0))

    # Draw brackets
    play_start = session.playlist.playback_start
    play_end = session.playlist.playback_end
    display_end = display_frame_start + display_frame_count - 1

    # Dont draw bracket if it takes up all the drawn timeline
    if not play_start == display_frame_start or not play_end == display_end:
        bracket_start = (play_start - display_frame_start) * frame_width
        bracket_end = (play_end - display_frame_start + 1) * frame_width
        draw_bracket(painter, bracket_start, height, out=False)
        draw_bracket(painter, bracket_end, height, out=True)


def draw_contracted_slider(
        painter: QtGui.QPainter,
        full_rect: QtCore.QRect,
        frame_width: int,
        display_frame_start: int,
        display_frame_count: int,
        current_frame: int,
        highlighted_values: list[int],
        moving_frame: str | None,
        separators: list[int],
        thumbnails: dict):

    session = ebc.get_session()
    painter.setPen(QtCore.Qt.PenStyle.NoPen)

    # Draw timeline, alternate color by shots, or use thumbnails
    start = 0
    height = int(preferences.get('timeline_height', 0)) or SLIDER_HEIGHT
    height_highlight = height - 4
    marker_height = height / 2

    separators.append(display_frame_count)
    for i, separator in enumerate(separators[:-1]):
        if thumbnails:
            pixmap = thumbnails[separator]
            brush = QtGui.QBrush()
            brush.setTexture(pixmap[0])
            painter.setBrush(brush)
        else:
            color = BG_COLOR if i % 2 == 0 else BG_COLOR_ALT
            painter.setBrush(color)

        separator -= display_frame_start
        left_rect = frame_width * separator
        right_rect = frame_width * (separators[i+1] - start)
        rect = QtCore.QRectF(
            left_rect, full_rect.top(), right_rect, full_rect.height())
        painter.drawRect(rect)
        start = separator

    # Draw cursor
    painter.setPen(QtCore.Qt.PenStyle.NoPen)
    CURSORCOLOR.setAlpha(255)
    if thumbnails:
        CURSORCOLOR.setAlpha(150)

    painter.setBrush(CURSORCOLOR)
    x = (get_rectangles(display_frame_count, frame_width, height)
         [current_frame - display_frame_start].left()
         - CURSOR_FIXED_WIDTH * 0.5)
    painter.drawRect(QtCore.QRect(x, 0, CURSOR_FIXED_WIDTH, height))

    # Draw annotations
    painter.setBrush(MARKER_COLOR)
    for frame in ebc.get_session().get_annotated_frames():
        annotation = ebc.get_session().get_annotation_at(frame)
        if annotation:
            metadata = annotation.metadata
            painter.setBrush(
                QtGui.QColor(metadata.get('user_color'))
                if metadata and metadata.get('user_color')
                else MARKER_COLOR)

        x = (get_rectangles(display_frame_count, frame_width, height)
             [frame - display_frame_start].left() + 0.5 * frame_width)

        painter.drawRect(QtCore.QRect(
            x, marker_height, MARKER_FIXED_WIDTH, height))

    # Draw moving annotations
    if moving_frame:
        painter.setBrush(QtGui.QColor(moving_frame))
        painter.drawRect(QtCore.QRect(x, 0, CURSOR_FIXED_WIDTH, height))

    # Draw Highlights
    painter.setBrush(HIGHLIGHT_COLOR)
    display_end = display_frame_start + display_frame_count - 1
    for frame in highlighted_values:

        # Check if frame is displayed
        if display_frame_start < frame < display_end:
            x = (get_rectangles(display_frame_count, frame_width, height)
                 [frame - display_frame_start].left())
            painter.drawRect(QtCore.QRect(
                x, height_highlight, HIGHLIGHT_FIXED_WIDTH, height))

    # Draw Brackets
    play_start = session.playlist.playback_start or 0
    play_end = (session.playlist.playback_end
                or session.playlist.frames_count - 1)

    # Dont draw bracket if it takes up all the drawn timeline
    if play_start != display_frame_start or play_end != display_end:
        bracket_start = (play_start - display_frame_start) * frame_width
        bracket_end = (play_end - display_frame_start + 1) * frame_width
        draw_bracket(painter, bracket_start, height, out=False)
        draw_bracket(painter, bracket_end, height, out=True)


def draw_zoom_slider(
        painter: QtGui.QPainter,
        rect: QtCore.QRect,
        display_start: int,
        display_end: int):

    session = ebc.get_session()
    left = rect.left()
    top = rect.top()
    frame_size = rect.width() / session.playlist.frames_count

    # Draw the whole timeline
    painter.setPen(QtCore.Qt.PenStyle.NoPen)
    painter.setBrush(ZOOM_COLOR)
    painter.drawRect(QtCore.QRect(
        left, top, rect.width(), ZOOM_HEIGHT))

    # Draw the displayed part
    painter.setBrush(ZOOM_COLOR_ALT)
    painter.drawRect(QtCore.QRect(
        left + frame_size * display_start,
        top,
        frame_size * (display_end - display_start),
        ZOOM_HEIGHT + 1))


def draw_bracket(painter: QtGui.QPainter, left, height, out=False):
    t_size = -BRACKET_TRIANGLE_SIZE if out else BRACKET_TRIANGLE_SIZE
    painter.setPen(QtGui.QColor(BRACKET_COLOR))
    painter.setBrush(QtGui.QColor(BRACKET_COLOR))
    # Separator line
    topleft = QtCore.QPointF(left, 0)
    painter.drawLine(topleft, QtCore.QPointF(left, height))
    # Top triangle
    triangle = QtGui.QPolygonF()
    triangle.append(topleft)
    triangle.append(QtCore.QPoint(left + t_size, 0))
    triangle.append(QtCore.QPoint(left, BRACKET_TRIANGLE_SIZE))
    triangle.append(topleft)
    painter.drawPolygon(triangle)
    # Bottom triangle
    topleft = QtCore.QPointF(left, height - BRACKET_TRIANGLE_SIZE)
    triangle = QtGui.QPolygonF()
    triangle.append(topleft)
    triangle.append(QtCore.QPoint(left + t_size, height))
    triangle.append(QtCore.QPoint(left, height))
    triangle.append(topleft)
    painter.drawPolygon(triangle)
