
from functools import lru_cache, partial

from PySide6 import QtGui, QtCore, QtWidgets
from PySide6.QtCore import Qt

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


def ctrl_pressed():
    modifiers = QtWidgets.QApplication.keyboardModifiers()
    return modifiers == (modifiers | QtCore.Qt.ControlModifier)


def shift_pressed():
    modifiers = QtWidgets.QApplication.keyboardModifiers()
    return modifiers == (modifiers | QtCore.Qt.ShiftModifier)


def alt_pressed():
    modifiers = QtWidgets.QApplication.keyboardModifiers()
    return modifiers == (modifiers | QtCore.Qt.AltModifier)


class TimeLineWidget(QtWidgets.QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.timeline = TimelineSlider()
        self.playback_options = PlaybackOptionsWidget()

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.timeline, stretch=1)
        layout.addWidget(self.playback_options)

    def update_values(self):
        self.playback_options.playback_options_changed()
        self.timeline.update()

    def update_current_frame(self):
        self.timeline.update()
        self.playback_options.update_current_frame()


class CurrentFrameValidator(QtGui.QValidator):

    def validate(self, string, _):
        if not string:
            return QtGui.QValidator.State.Intermediate
        if not string.isdigit():
            return QtGui.QValidator.State.Invalid
        valid = 0 <= int(string) <= ebc.get_session().playlist.frames_count
        return (
            QtGui.QValidator.State.Acceptable if
            valid else QtGui.QValidator.State.Intermediate)


class StartFrameValidator(QtGui.QValidator):

    def validate(self, string, _):
        if not string:
            return QtGui.QValidator.State.Intermediate
        if not string.isdigit():
            return QtGui.QValidator.State.Invalid
        maximum = (
            ebc.get_session().playlist.playback_end or
            ebc.get_session().playlist.frames_count)
        valid = 0 <= int(string) <= maximum
        return (
            QtGui.QValidator.State.Acceptable if
            valid else QtGui.QValidator.State.Intermediate)


class EndFrameValidator(QtGui.QValidator):

    def validate(self, string, _):
        if not string:
            return QtGui.QValidator.State.Intermediate
        if not string.isdigit():
            return QtGui.QValidator.State.Invalid
        minimum = ebc.get_session().playlist.playback_start or 0
        maximum = ebc.get_session().playlist.frames_count
        valid = minimum <= int(string) <= maximum
        return (
            QtGui.QValidator.State.Acceptable if
            valid else QtGui.QValidator.State.Intermediate)


class PlaybackOptionsWidget(QtWidgets.QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        validator = CurrentFrameValidator()
        self.current_frame = QtWidgets.QLineEdit(text='0', fixedWidth=50)
        self.current_frame.editingFinished.connect(self.set_frame)
        self.current_frame.setValidator(validator)

        validator = StartFrameValidator()
        self.playback_start = QtWidgets.QLineEdit(text='0', fixedWidth=50)
        self.playback_start.editingFinished.connect(self.set_playback_start)
        self.playback_start.setValidator(validator)

        validator = EndFrameValidator()
        self.playback_end = QtWidgets.QLineEdit(text='0', fixedWidth=50)
        self.playback_end.editingFinished.connect(self.set_playback_end)
        self.playback_end.setValidator(validator)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.current_frame)
        layout.addWidget(self.playback_start)
        layout.addWidget(self.playback_end)

    def set_playback_end(self):
        ebc.set_playback_end(int(self.playback_end.text()))

    def set_playback_start(self):
        ebc.set_playback_start(int(self.playback_start.text()))

    def set_frame(self):
        ebc.set_frame(int(self.current_frame.text()))

    def playback_options_changed(self):
        self.playback_start.blockSignals(True)
        self.playback_end.blockSignals(True)
        self.current_frame.blockSignals(True)
        start, end = ebc.get_session().playlist.get_playback_range()
        self.playback_start.setText(str(start))
        self.playback_end.setText(str(end))
        self.current_frame.setText(str(ebc.get_session().playlist.frame))
        self.playback_start.blockSignals(False)
        self.playback_end.blockSignals(False)
        self.current_frame.blockSignals(False)


class MergeAnnotations(QtWidgets.QDialog) :
    def __init__(self, parent=None) :
        super().__init__(parent)
        self.setWindowTitle('Conflicting Annotations')
        self.resize(250, 100)
        label = QtWidgets.QLabel('There already exists an annotation on this frame.')
        self.merge_button = QtWidgets.QPushButton('Merge')
        self.override_button = QtWidgets.QPushButton('Override')
        self.cancel_button = QtWidgets.QPushButton('Cancel')
        layout = QtWidgets.QVBoxLayout()
        self.result = 0

        button_layout = QtWidgets.QHBoxLayout()
        button_layout.addWidget(self.merge_button)
        button_layout.addWidget(self.override_button)
        button_layout.addWidget(self.cancel_button)

        self.cancel_button.clicked.connect(partial(self.set_result, 0))
        self.merge_button.clicked.connect(partial(self.set_result, 1))
        self.override_button.clicked.connect(partial(self.set_result, 2))

        layout.addWidget(label)
        layout.addLayout(button_layout)

        self.setLayout(layout)
        self.show()

    def set_result(self, result):
        self.result = result
        self.accept()


class TimelineSlider(QtWidgets.QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.handeling_range = None
        self._mlb_pressed = False
        self._mmb_pressed = False
        self.origin_frame = None
        self.move_start_bracket = False
        self.move_end_bracket = False
        self.moving_model = None
        self.origin_frame = None

        self.remapping = False
        self.start_frame = None
        self.end_frame = None

        self.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)
        self.setFixedHeight(SLIDER_HEIGHT)
        self.setMouseTracking(True)

    @property
    def value(self):
        return ebc.get_session().playlist.frame

    @property
    def maximum(self):
        if self.end_frame :
            return self.end_frame
        return ebc.get_session().playlist.frames_count - 1

    @property
    def minimum(self):
        if not self.start_frame:
            return 0
        return self.start_frame

    def count(self):
        if self.start_frame or self.end_frame:
            return self.end_frame - self.start_frame + 1
        return ebc.get_session().playlist.frames_count

    def leftClicEvent(self, event):
        session = ebc.get_session()
        self._mlb_pressed = True
        frame = self.get_frame_from_point(event.position().toPoint())

        # Move brackets
        if not ctrl_pressed() and not shift_pressed():
            if frame == session.playlist.playback_start:
                self.move_start_bracket = True
            if frame == session.playlist.playback_end:
                self.move_end_bracket = True

        elif frame in session.get_annotated_frames():
            index = session.get_annotation_index(frame)
            if ctrl_pressed() and not shift_pressed():
                # Move Annotation
                self.origin_frame = frame
                self.moving_model = session.annotations[index]
                del session.annotations[index]

            elif shift_pressed():
                # Duplicate Annotation
                self.moving_model = session.annotations[index].copy()

        self.set_value_from_point(event.position().toPoint())

    def mousePressEvent(self, event):
        self.setFocus(QtCore.Qt.MouseFocusReason)
        if not self.maximum:
            return
        if event.button() == QtCore.Qt.LeftButton:
            self.leftClicEvent(event)

        if event.button() == QtCore.Qt.MiddleButton:
            self._mmb_pressed = True
            value = self.get_frame_from_point(event.position().toPoint())
            ebc.set_playback_range(value, value + 1)
            if ctrl_pressed():
                self.remapping = True

        self.update()

    def mouseMoveEvent(self, event):
        session = ebc.get_session()
        frame = self.get_frame_from_point(event.position().toPoint())
        annoted_frames = ebc.get_session().get_annotated_frames()
        bracket_frame = frame in [session.playlist.playback_start,
            session.playlist.playback_end]

        if frame in annoted_frames and (ctrl_pressed() or shift_pressed()):
            QtWidgets.QApplication.setOverrideCursor(
                QtCore.Qt.CursorShape.SizeHorCursor)
        elif bracket_frame and not ctrl_pressed() and not shift_pressed():
            QtWidgets.QApplication.setOverrideCursor(
                QtCore.Qt.CursorShape.SizeHorCursor)
        else :
            QtWidgets.QApplication.restoreOverrideCursor()

        if not self.maximum:
            return
        if self._mlb_pressed:
            point = event.position().toPoint()
            self.set_value_from_point(point)
            if self.move_start_bracket :
                ebc.set_playback_start(frame)
            elif self.move_end_bracket :
                ebc.set_playback_end(frame)

        if self._mmb_pressed:
            self.set_value_from_point(event.position().toPoint())
            self.update_playback_range_from_point(event.position().toPoint())

        self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == QtCore.Qt.MiddleButton:
            self._mmb_pressed = False
            if self.remapping:
                self.remapping = False
                session = ebc.get_session()
                self.start_frame = session.playlist.playback_start
                self.end_frame = session.playlist.playback_end
                self.update()

        if event.button() == QtCore.Qt.RightButton:
            self.exec_context_menu(event.position().toPoint())

        if event.button() != QtCore.Qt.LeftButton:
            return

        if True:
            self._mlb_pressed = False
            self.move_start_bracket = False
            self.move_end_bracket = False

            if not self.moving_model:
                self.origin_frame = None
                return

            frame = self.get_frame_from_point(event.position().toPoint())

            if frame not in ebc.get_session().get_annotated_frames():
                idx = ebc.get_session().get_annotation_index(frame)
                ebc.get_session().annotations[idx] = self.moving_model
                self.update()
                self.set_value_from_point(event.position().toPoint())
                ebc.set_frame(frame)
                self.moving_model = None
                self.origin_frame = None
                return

            dialog = MergeAnnotations()
            dialog.exec_()
            if dialog.result == 0:
                self.cancel()

            if dialog.result == 1:
                self.merge(event.position().toPoint())

            if dialog.result == 2:
                self.override(event.position().toPoint())

            ebc.set_frame(frame)
            self.moving_model = None
            self.origin_frame = None

    def mouseDoubleClickEvent(self, event):
        if event.button() != QtCore.Qt.LeftButton:
            return

        if self.start_frame or self.end_frame :
            self.start_frame = None
            self.end_frame = None
            return

        point = event.position().toPoint()
        frame = int(point.x() / self.width() * self.count())
        container = ebc.get_session().playlist.frames_containers[frame]

        pb_end = ebc.get_session().playlist.playback_end
        pb_start = ebc.get_session().playlist.playback_start
        start = ebc.get_session().playlist.first_frames[container.id]
        end = start + container.length - 1
        if pb_start == start and pb_end == end:
            ebc.set_playback_start(0)
            ebc.set_playback_end(self.maximum)
        else:
            ebc.set_playback_start(start)
            ebc.set_playback_end(end)
        self.update()

    def update_playback_range_from_point(self, point):
        value = self.get_frame_from_point(point)
        if ebc.get_session().playlist.playback_start is None:
            ebc.set_playback_range(value, value + 1)
            self.update()
            return

        values = (
            value,
            ebc.get_session().playlist.playback_start,
            ebc.get_session().playlist.playback_end)
        ebc.set_playback_range(min(values), max(values))
        self.update()

    def set_value_from_point(self, point):
        offset = self.start_frame if self.start_frame else 0
        value = int(point.x() / self.width() * self.count())
        frame = max(self.minimum, min(self.maximum, value + offset))
        if frame != ebc.get_frame():
            ebc.set_frame(frame)

    def get_frame_from_point(self, point):
        offset = self.start_frame if self.start_frame else 0
        value =  int(point.x() / self.width() * self.count())
        return max(self.minimum, min(self.maximum, value + offset))

    def merge(self, point):
        frame = self.get_frame_from_point(point)
        target = ebc.get_session().get_annotation_at(frame)
        target.merge(self.moving_model)

    def override(self, point):
        frame = self.get_frame_from_point(point)
        index = ebc.get_session().get_annotation_index(frame)
        ebc.get_session().annotations[index] = self.moving_model

    def cancel(self):
        if self.origin_frame is None:
            return
        index = ebc.get_session().get_annotation_index(self.origin_frame)
        ebc.get_session().annotations[index] = self.moving_model

    def exec_context_menu(self, point):
        frame = self.get_frame_from_point(point)
        annotated_frames = ebc.get_session().get_annotated_frames()
        menu = QtWidgets.QMenu()
        frame_exists = frame in annotated_frames

        delete_action = QtGui.QAction(f'Delete annotation on frame: {frame}')
        menu.addAction(delete_action)
        delete_action.setEnabled(frame_exists)

        recolor_action = QtGui.QAction(f'Change annotation color on frame: {frame}')
        menu.addAction(recolor_action)
        recolor_action.setEnabled(frame_exists)

        action = menu.exec(self.mapToGlobal(point))
        if action == delete_action:
            index = ebc.get_session().get_annotation_index(frame)
            del ebc.get_session().annotations[index]

        if action == recolor_action:
            options = QtWidgets.QColorDialog.ColorDialogOption.DontUseNativeDialog
            annotation = ebc.get_session().get_annotation_at(frame)
            default_color = annotation.metadata.get('user_color')
            default_color = MARKER_COLOR if not default_color else default_color
            color = QtWidgets.QColorDialog.getColor(
                default_color,
                parent=self,
                options=options,
                title='Change Annotation Color')
            if color.isValid():
                annotation = ebc.get_session().get_annotation_at(frame)
                annotation.metadata['user_color'] = color.name()

    def paintEvent(self, _):
        painter = QtGui.QPainter(self)
        try:
            session = ebc.get_session()
            play_start = (self.start_frame
                if self.start_frame else 0)

            moving_metadata = None
            if self.moving_model :
                metadata_color = self.moving_model.metadata.get('user_color')
                moving_metadata = metadata_color
                if not moving_metadata:
                    moving_metadata = MARKER_COLOR.name()

            draw_slider(
                painter,
                self.rect(),
                self.count(),
                play_start,
                session.playlist.frame,
                session.playlist.frames_images.keys(),
                moving_metadata,
                list(session.playlist.first_frames.values())
            )

            if play_start or self.end_frame:
                draw_zoom_slider(
                    painter,
                    self.rect(),
                    self.start_frame,
                    self.end_frame
                )

        except Exception:
            import traceback
            print(traceback.format_exc())
        finally:
            painter.end()


def draw_slider(
        painter: QtGui.QPainter,
        full_rect: QtCore.QRect,
        display_frame_count: int,
        display_frame_start: int,
        current_frame: int,
        cached_values: list[int], #highlighte values
        moving_frame: str|None,
        separators: list[int]):

    if display_frame_count == 0:
        painter.drawRect(full_rect)
        return

    width = full_rect.width()
    frame_width = width / display_frame_count

    if frame_width > 4:
        draw_expanded_slider(
            painter = painter,
            frame_width = frame_width,
            display_frame_start = display_frame_start,
            display_frame_count = display_frame_count,
            current_frame = current_frame,
            highlighted_values = cached_values,
            moving_frame = moving_frame,
            separators = separators
        )
    else:
        draw_contracted_slider(
            painter=painter,
            full_rect= full_rect,
            frame_width = frame_width,
            display_frame_start = display_frame_start,
            display_frame_count = display_frame_count,
            current_frame = current_frame,
            highlighted_values = cached_values,
            moving_frame = moving_frame,
            separators = separators
        )


def draw_expanded_slider(
        painter: QtGui.QPainter,
        frame_width: int,
        display_frame_start: int,
        display_frame_count: int,
        current_frame: int,
        highlighted_values: list[int],
        moving_frame: str|None,
        separators: list[int]):

    session = ebc.get_session()
    annotations = session.get_annotations_by_frames()

    for i, value_rect in enumerate(
            get_rectangles(display_frame_count, frame_width)):

        # Drawn checkered pattern
        painter.setPen(Qt.PenStyle.NoPen)
        color = BG_COLOR if i % 2 else BG_COLOR_ALT
        painter.setBrush(color)
        painter.drawRect(value_rect)

        # Draw current frame
        absolute_frame = i + display_frame_start
        if absolute_frame == current_frame:
            color = QtGui.QColor(CURSORCOLOR)
            pen = QtGui.QPen(color) if i in annotations else Qt.NoPen
            brush = Qt.NoBrush if i in annotations else QtGui.QBrush(color)
            painter.setPen(pen)
            painter.setBrush(brush)
            painter.drawRect(value_rect)

            # If moving an annotations, take its color
            if moving_frame:
                painter.setBrush(QtGui.QColor(moving_frame))
                painter.drawRect(value_rect.adjusted(0, 0, 0, 0))

        # Draw marker frames
        if absolute_frame in annotations:
            annotation = ebc.get_session().get_annotation_at(absolute_frame)
            if annotation :
                metadata = annotation.metadata
                painter.setBrush(
                    QtGui.QColor(QtGui.QColor(metadata.get('user_color'))
                    if metadata and metadata.get('user_color')
                    else MARKER_COLOR))
            painter.drawRect(value_rect.adjusted(0, 0, 0, 0))

        # Draw highlighted frames
        if absolute_frame in highlighted_values:
            painter.setBrush(HIGHLIGHT_COLOR)
            painter.drawRect(value_rect.adjusted(0, HIGHLIGHT_Y, 0, 0))

        # Draw separators
        if absolute_frame in separators:
            painter.setPen(QtGui.QColor(SEPARATOR_COLOR))
            painter.setBrush(QtGui.QColor(SEPARATOR_COLOR))
            painter.drawLine(value_rect.topLeft(), value_rect.bottomLeft())
            left = value_rect.left() + 2
            topleft = QtCore.QPointF(left, value_rect.top())
            bottomleft = QtCore.QPointF(left, value_rect.bottom())
            painter.drawLine(topleft, bottomleft)

    # Draw brackets
    height = SLIDER_HEIGHT - 1
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
        moving_frame: str|None,
        separators: list[int]):

    session = ebc.get_session()
    painter.setPen(Qt.PenStyle.NoPen)

    # Draw timeline, alternate color by shots
    start = 0
    for i, separator in enumerate(separators):
        separator -= display_frame_start
        if separator:
            color = BG_COLOR if i % 2 == 0 else BG_COLOR_ALT
            left_rect = frame_width * start
            right_rect = frame_width * (separator - start)
            rect = QtCore.QRectF(
                left_rect, full_rect.top(), right_rect, full_rect.height())
            painter.setBrush(color)
            painter.drawRect(rect)
            start = separator

    # Draw cursor
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(CURSORCOLOR)
    x = (get_rectangles(display_frame_count, frame_width)
        [current_frame - display_frame_start].left()
        - CURSOR_FIXED_WIDTH * 0.5)
    painter.drawRect(QtCore.QRect(x, 0, CURSOR_FIXED_WIDTH, SLIDER_HEIGHT))

    # Draw annotations
    painter.setBrush(MARKER_COLOR)
    for frame in ebc.get_session().get_annotated_frames():
        annotation = ebc.get_session().get_annotation_at(frame)
        if annotation:
            metadata = annotation.metadata
            painter.setBrush(
                QtGui.QColor(QtGui.QColor(metadata.get('user_color')) if
                metadata and metadata.get('user_color') else MARKER_COLOR))

        x = (get_rectangles(display_frame_count, frame_width)
            [frame - display_frame_start].left() + 0.5 * frame_width)

        painter.drawRect(QtCore.QRect(
            x, MARKER_Y, MARKER_FIXED_WIDTH, SLIDER_HEIGHT))

    # Draw moving annotations
    if moving_frame:
        painter.setBrush(QtGui.QColor(moving_frame))
        painter.drawRect(QtCore.QRect(x, 0, CURSOR_FIXED_WIDTH, SLIDER_HEIGHT))

    # Draw Highlights
    painter.setBrush(HIGHLIGHT_COLOR)
    display_end = display_frame_start + display_frame_count - 1
    for frame in highlighted_values:

        # Check if frame is displayed
        if display_frame_start < frame < display_end:
            x = (get_rectangles(display_frame_count, frame_width)
                [frame - display_frame_start].left())
            painter.drawRect(QtCore.QRect(
                x, HIGHLIGHT_Y, HIGHLIGHT_FIXED_WIDTH, SLIDER_HEIGHT))

    # Draw Brackets
    height = SLIDER_HEIGHT - 1
    play_start = session.playlist.playback_start
    play_end = session.playlist.playback_end
    # Dont draw bracket if it takes up all the drawn timeline
    if not play_start == display_frame_start or not play_end == display_end:
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
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(ZOOM_COLOR)
    painter.drawRect(QtCore.QRect(
        left, top, rect.width(), ZOOM_HEIGHT))

    # Draw the displayed part
    painter.setBrush(ZOOM_COLOR_ALT)
    painter.drawRect(QtCore.QRect(
        left + frame_size * display_start, top,
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


@lru_cache
def get_rectangles(count, width, height=SLIDER_HEIGHT):
    return [QtCore.QRectF(i * width, 0, width, height) for i in range(count)]


@lru_cache
def get_marker_position(value, max_value, width, thickness, center=False):
    offset = 0
    if center:
        width -= thickness
        offset = thickness / 2
    return int((value / max_value) * (width - thickness)) + offset