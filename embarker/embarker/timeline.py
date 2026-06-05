
from functools import lru_cache, partial

from PySide6 import QtGui, QtCore, QtWidgets
from PySide6.QtCore import Qt

import embarker.commands as ebc
from embarker import preferences


SLIDER_HEIGHT = 22
HIGHLIGHT_Y = SLIDER_HEIGHT - 4
MARKER_Y = 8
BRACKET_TRIANGLE_SIZE = 4
BG_COLOR = QtGui.QColor('#232323')
BG_COLOR_ALT = QtGui.QColor('#151515')
SEPARATOR_COLOR = QtGui.QColor('#444444')
CURSORCOLOR = QtGui.QColor('#656565')
HIGHLIGHT_COLOR = QtGui.QColor('#0088FF')
HIGHLIGHT_COLOR.setAlpha(100)
MARKER_COLOR = QtGui.QColor('#999900')
BRACKET_COLOR = QtGui.QColor('#FFF')

CURSOR_FIXED_WIDTH = 8
HIGHLIGHT_FIXED_WIDTH = 2
MARKER_FIXED_WIDTH = 1


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
        return ebc.get_session().playlist.frames_count - 1

    def exec_context_menu(self, point):
        frame = self.get_frame_from_point(point)
        annotated_frames = ebc.get_session().get_annotated_frames()
        menu = QtWidgets.QMenu()
        frame_exists: bool = frame in annotated_frames

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
            value = int(event.pos().x() / self.width() * self.count())
            ebc.set_playback_range(value, value + 1)
        self.update()

    def mouseMoveEvent(self, event):
        session = ebc.get_session()
        frame = self.get_frame_from_point(event.position().toPoint())
        annoted_frames = ebc.get_session().get_annotated_frames()
        bracket_frame: bool = frame in [session.playlist.playback_start,
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

        if event.button() == QtCore.Qt.RightButton:
            self.exec_context_menu(event.position().toPoint())

        if event.button() != QtCore.Qt.LeftButton:
            return

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

    def paintEvent(self, _):
        painter = QtGui.QPainter(self)
        try:
            # Will maybe change this so we have annotation in the canvas
            marked_frames = ebc.get_session().get_annotated_frames()
            moving_metadata = None
            if self.moving_model :
                metadata_color = self.moving_model.metadata.get('user_color')
                moving_metadata = metadata_color
                if not moving_metadata:
                    moving_metadata = MARKER_COLOR.name()

            drawslider(
                painter=painter,
                full_rect=self.rect(),
                count=self.count(),
                current=self.value,
                highlighted_values=ebc.get_session().playlist.frames_images.keys(),
                marked_values=marked_frames,
                play_start=ebc.get_session().playlist.playback_start,
                play_end=ebc.get_session().playlist.playback_end,
                moving_frame=moving_metadata,
                separators=list(ebc.get_session().playlist.first_frames.values()))

        except Exception:
            import traceback
            print(traceback.format_exc())
        finally:
            painter.end()

    def update_playback_range_from_point(self, point):
        value = int(point.x() / self.width() * self.count())
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
        value = int(point.x() / self.width() * self.count())
        frame = max(0, min(self.maximum, value))
        if frame != ebc.get_frame():
            ebc.set_frame(frame)

    def get_frame_from_point(self, point) :
        value =  int(point.x() / self.width() * self.count())
        return max(0, min(self.maximum, value))

    def count(self):
        return self.maximum + 1

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


def draw_slider_brackets(
        painter, rect, play_start, play_end, count, frame_width):
    height = rect.height() - 1
    play_start = play_start if play_start is not None else 0
    play_end = play_end if play_end is not None else count - 1
    if not (play_start == 0 and play_end == count - 1):
        draw_bracket(painter, frame_width * play_start, height)
        left = min((frame_width * (play_end + 1), rect.right() - 1))
        draw_bracket(painter, left, height, True)


def drawslider(
        painter: QtGui.QPainter,
        full_rect: QtCore.QRect,
        count: int,
        current: int,
        highlighted_values: list[int],
        play_start: int|None,
        play_end: int|None,
        marked_values: list[int],
        moving_frame: str|None,
        separators: list[int]):

    if count == 0:
        painter.drawRect(full_rect)
        return

    width = full_rect.width()
    frame_width = width / count
    max_value = count - 1

    if frame_width > 4:
        draw_expanded_slider(
            painter=painter,
            frame_width=frame_width,
            count=count,
            current=current,
            highlighted_values=highlighted_values,
            marked_values=marked_values,
            moving_frame=moving_frame,
            separators=separators)
        draw_slider_brackets(
            painter, full_rect, play_start, play_end, count, frame_width)
        return

    painter.setPen(Qt.PenStyle.NoPen)
    # flat bg
    start = 0
    separators.append(count)
    painter.setPen(Qt.PenStyle.NoPen)
    for i, separator in enumerate(separators):
        if not separator:
            continue
        color = BG_COLOR if i % 2 == 0 else BG_COLOR_ALT
        left = frame_width * start
        video_width = frame_width * (separator - start)
        rect = QtCore.QRectF(
            left, full_rect.top(), video_width, full_rect.height())
        painter.setBrush(color)
        painter.drawRect(rect)
        # draw_separator(painter, left, rect.height())
        start = separator

    # Draw cursor
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(CURSORCOLOR)
    x = get_marker_position(current, max_value, width, CURSOR_FIXED_WIDTH)
    painter.drawRect(QtCore.QRect(x, 0, CURSOR_FIXED_WIDTH, SLIDER_HEIGHT))
    if moving_frame:
        painter.setBrush(QtGui.QColor(moving_frame))
        painter.drawRect(QtCore.QRect(x, 0, CURSOR_FIXED_WIDTH, SLIDER_HEIGHT))

    # Markers
    painter.setBrush(MARKER_COLOR)
    for value in marked_values:
        annotation = ebc.get_session().get_annotation_at(value)
        if annotation :
            metadata = annotation.metadata
            painter.setBrush(QtGui.QColor(QtGui.QColor(metadata.get('user_color')) if
                metadata and metadata.get('user_color') else MARKER_COLOR))
        x = get_marker_position(
            value, max_value, width, MARKER_FIXED_WIDTH, True)
        painter.drawRect(QtCore.QRect(
            x, MARKER_Y, MARKER_FIXED_WIDTH, SLIDER_HEIGHT))

    # Highlights
    painter.setBrush(HIGHLIGHT_COLOR)
    for value in highlighted_values:
        x = get_marker_position(
            value, max_value, width, HIGHLIGHT_FIXED_WIDTH, True)
        painter.drawRect(QtCore.QRect(
            x, HIGHLIGHT_Y, HIGHLIGHT_FIXED_WIDTH, SLIDER_HEIGHT))

    draw_slider_brackets(
        painter, full_rect, play_start, play_end, count, frame_width)


def draw_expanded_slider(
        painter: QtGui.QPainter,
        frame_width: int,
        count: int,
        current: int,
        highlighted_values: list[int],
        marked_values: list[int],
        moving_frame: QtGui.QColor|None,
        separators: list[int]
    ):
    for i, value_rect in enumerate(get_rectangles(count, frame_width)):
        painter.setPen(Qt.PenStyle.NoPen)
        color = BG_COLOR if i % 2 else BG_COLOR_ALT
        painter.setBrush(color)
        painter.drawRect(value_rect)
        # Markers
        if i in marked_values:
            annotation = ebc.get_session().get_annotation_at(i)
            if annotation :
                metadata = annotation.metadata
                metadata = annotation.metadata
                painter.setBrush(QtGui.QColor(QtGui.QColor(metadata.get('user_color')) if
                    metadata and metadata.get('user_color') else MARKER_COLOR))

            painter.drawRect(value_rect.adjusted(0, 0, 0, 0))
        if i == current:
            color = QtGui.QColor(CURSORCOLOR)
            pen = QtGui.QPen(color) if i in marked_values else Qt.NoPen
            brush = Qt.NoBrush if i in marked_values else QtGui.QBrush(color)
            painter.setPen(pen)
            painter.setBrush(brush)
            painter.drawRect(value_rect)

            if moving_frame:
                painter.setBrush(QtGui.QColor(moving_frame))
                painter.drawRect(value_rect.adjusted(0, 0, 0, 0))
        painter.setPen(Qt.PenStyle.NoPen)
        # Highlights
        if i in highlighted_values:
            painter.setBrush(HIGHLIGHT_COLOR)
            painter.drawRect(value_rect.adjusted(0, HIGHLIGHT_Y, 0, 0))
        if i in separators:
            painter.setPen(QtGui.QColor(SEPARATOR_COLOR))
            painter.setBrush(QtGui.QColor(SEPARATOR_COLOR))
            painter.drawLine(value_rect.topLeft(), value_rect.bottomLeft())
            left = value_rect.left() + 2
            topleft = QtCore.QPointF(left, value_rect.top())
            bottomleft = QtCore.QPointF(left, value_rect.bottom())
            painter.drawLine(topleft, bottomleft)


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


def ctrl_pressed():
    modifiers = QtWidgets.QApplication.keyboardModifiers()
    return modifiers == (modifiers | QtCore.Qt.ControlModifier)


def shift_pressed():
    modifiers = QtWidgets.QApplication.keyboardModifiers()
    return modifiers == (modifiers | QtCore.Qt.ShiftModifier)


def alt_pressed():
    modifiers = QtWidgets.QApplication.keyboardModifiers()
    return modifiers == (modifiers | QtCore.Qt.AltModifier)
