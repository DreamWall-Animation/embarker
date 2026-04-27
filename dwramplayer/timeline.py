from functools import lru_cache
from PySide6 import QtGui, QtCore, QtWidgets
from PySide6.QtCore import Qt
from dwramplayer.session import Session


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
    current_frame_changed = QtCore.Signal()

    def __init__(self, session, parent=None):
        super().__init__(parent)
        self.timeline = TimelineSlider(session)
        self.playback_options = PlaybackOptionsWidget(session)

        self.timeline.current_frame_changed.connect(
            self.current_frame_changed.emit)
        self.timeline.current_frame_changed.connect(
            self.playback_options.playback_options_changed)
        self.timeline.playback_range_changed.connect(
            self.playback_options.playback_options_changed)

        self.playback_options.current_frame_changed.connect(
            self.current_frame_changed.emit)
        self.playback_options.playback_range_changed.connect(
            self.timeline.update)
        self.playback_options.current_frame_changed.connect(
            self.timeline.update)

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
    def __init__(self, session: Session):
        super().__init__()
        self.session = session

    def validate(self, string, _):
        if not string:
            return QtGui.QValidator.State.Intermediate
        if not string.isdigit():
            return QtGui.QValidator.State.Invalid
        valid = 0 <= int(string) <= self.session.playlist.frames_count
        return (
            QtGui.QValidator.State.Acceptable if
            valid else QtGui.QValidator.State.Intermediate)


class StartFrameValidator(QtGui.QValidator):
    def __init__(self, session: Session):
        super().__init__()
        self.session = session

    def validate(self, string, _):
        if not string:
            return QtGui.QValidator.State.Intermediate
        if not string.isdigit():
            return QtGui.QValidator.State.Invalid
        maximum = (
            self.session.playlist.playback_end or
            self.session.playlist.frames_count)
        valid = 0 <= int(string) <= maximum
        return (
            QtGui.QValidator.State.Acceptable if
            valid else QtGui.QValidator.State.Intermediate)


class EndFrameValidator(QtGui.QValidator):
    def __init__(self, session: Session):
        super().__init__()
        self.session = session

    def validate(self, string, _):
        if not string:
            return QtGui.QValidator.State.Intermediate
        if not string.isdigit():
            return QtGui.QValidator.State.Invalid
        minimum = self.session.playlist.playback_start or 0
        maximum = self.session.playlist.frames_count
        valid = minimum <= int(string) <= maximum
        return (
            QtGui.QValidator.State.Acceptable if
            valid else QtGui.QValidator.State.Intermediate)


class PlaybackOptionsWidget(QtWidgets.QWidget):
    current_frame_changed = QtCore.Signal()
    playback_range_changed = QtCore.Signal()

    def __init__(self, session: Session, parent=None):
        super().__init__(parent)
        self._session = session
        validator = CurrentFrameValidator(self._session)
        self.current_frame = QtWidgets.QLineEdit(text='0', fixedWidth=50)
        self.current_frame.editingFinished.connect(self.update_current_frame)
        self.current_frame.setValidator(validator)
        validator = StartFrameValidator(self._session)
        self.playback_start = QtWidgets.QLineEdit(text='0', fixedWidth=50)
        self.playback_start.editingFinished.connect(self.update_playback_options)
        self.playback_start.setValidator(validator)
        validator = EndFrameValidator(self._session)
        self.playback_end = QtWidgets.QLineEdit(text='0', fixedWidth=50)
        self.playback_end.editingFinished.connect(self.update_playback_options)
        self.playback_end.setValidator(validator)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.current_frame)
        layout.addWidget(self.playback_start)
        layout.addWidget(self.playback_end)

    def update_playback_options(self):
        self._session.playlist.playback_start = int(self.playback_start.text())
        self._session.playlist.playback_end = int(self.playback_end.text())
        self.playback_range_changed.emit()

    def update_current_frame(self):
        self._session.playlist.frame = int(self.current_frame.text())
        self.current_frame_changed.emit()

    def playback_options_changed(self):
        self.playback_start.blockSignals(True)
        self.playback_end.blockSignals(True)
        self.current_frame.blockSignals(True)
        start, end = self._session.playlist.get_playback_range()
        self.playback_start.setText(str(start))
        self.playback_end.setText(str(end))
        self.current_frame.setText(str(self._session.playlist.frame))
        self.playback_start.blockSignals(False)
        self.playback_end.blockSignals(False)
        self.current_frame.blockSignals(False)


class TimelineSlider(QtWidgets.QWidget):
    current_frame_changed = QtCore.Signal()
    playback_range_changed = QtCore.Signal()
    mouse_released = QtCore.Signal()

    def __init__(self, session: Session, parent=None):
        super().__init__(parent)
        self._session = session
        self._mlb_pressed = False
        self._mrb_pressed = False

        self.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.setFixedHeight(SLIDER_HEIGHT)
        self.handeling_range = None

    @property
    def value(self):
        return self._session.playlist.frame

    @property
    def maximum(self):
        return self._session.playlist.frames_count - 1

    def set_session(self, session):
        self._session = session
        self.update()

    def mousePressEvent(self, event):
        if not self.maximum:
            return
        if event.button() == QtCore.Qt.LeftButton:
            self._mlb_pressed = True
            self.set_value_from_point(event.position().toPoint())
        if event.button() == QtCore.Qt.RightButton:
            self._mrb_pressed = True
            self._session.playlist.playback_start = None
            self._session.playlist.playback_end = None
            self.update_playback_range_from_point(event.position().toPoint())
        self.update()

    def update_playback_range_from_point(self, point):
        value = int(point.x() / self.width() * self.count())
        if self._session.playlist.playback_start is None:
            self._session.playlist.playback_start = value
            self._session.playlist.playback_end = value
            self.playback_range_changed.emit()
            self.update()
            return

        start = self._session.playlist.playback_start
        self._session.playlist.playback_start = max((0, min((start, value))))
        end = self._session.playlist.playback_end
        end = min((self.maximum, max((end, value))))
        self._session.playlist.playback_end = end
        self.playback_range_changed.emit()
        self.update()

    def mouseMoveEvent(self, event):
        if not self.maximum:
            return
        if self._mlb_pressed is True:
            self.set_value_from_point(event.position().toPoint())
        if self._mrb_pressed is True:
            self.set_value_from_point(event.position().toPoint())
            self.update_playback_range_from_point(event.position().toPoint())
            self.playback_range_changed.emit()
        self.update()

    def set_value_from_point(self, point):
        value = int(point.x() / self.width() * self.count())
        self._session.playlist.frame = max(0, min(self.maximum, value))
        self.current_frame_changed.emit()

    def count(self):
        return self.maximum + 1

    def mouseReleaseEvent(self, _):
        self._mlb_pressed = False
        self._mrb_pressed = False
        self.mouse_released.emit()

    def mouseDoubleClickEvent(self, event):
        if event.button() != QtCore.Qt.LeftButton:
            return
        point = event.position().toPoint()
        frame = int(point.x() / self.width() * self.count())
        container = self._session.playlist.frames_containers[frame]

        pb_end = self._session.playlist.playback_end
        pb_start = self._session.playlist.playback_start
        start = self._session.playlist.first_frames[container.id]
        end = start + container.length - 1
        if pb_start == start and pb_end == end:
            self._session.playlist.playback_start = 0
            self._session.playlist.playback_end = self.maximum
        else:
            self._session.playlist.playback_start = start
            self._session.playlist.playback_end = end
        self.playback_range_changed.emit()
        self.update()

    def paintEvent(self, _):
        painter = QtGui.QPainter()
        painter.begin(self)
        try:
            drawslider(
                painter=painter,
                full_rect=self.rect(),
                count=self.count(),
                current=self.value,
                highlighted_values=self._session.playlist.frames_images.keys(),
                marked_values=self._session.get_annotated_frames(),
                play_start=self._session.playlist.playback_start,
                play_end=self._session.playlist.playback_end,
                separators=list(self._session.playlist.first_frames.values()))
        except Exception:
            import traceback
            print(traceback.format_exc())
        finally:
            painter.end()


def drawslider(
        painter: QtGui.QPainter,
        full_rect: QtCore.QRect,
        count: int,
        current: int,
        highlighted_values: list[int],
        play_start: int|None,
        play_end: int|None,
        marked_values: list[int],
        separators: list[int]):

    if count == 0:
        painter.drawRect(full_rect)
        return

    play_start = play_start if play_start is not None else 0
    play_end = play_end if play_end is not None else count - 1
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
            separators=separators)
        height = full_rect.height() - 1
        if not (play_start == 0 and play_end == count - 1):
            draw_bracket(painter, frame_width * play_start, height)
            left = min((frame_width * (play_end + 1), full_rect.right() - 1))
            draw_bracket(painter, left, height, True)
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

    # Markers
    painter.setBrush(MARKER_COLOR)
    for value in marked_values:
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


def draw_expanded_slider(
        painter: QtGui.QPainter,
        frame_width: int,
        count: int,
        current: int,
        highlighted_values: list[int],
        marked_values: list[int],
        separators: list[int]
    ):
    for i, value_rect in enumerate(get_rectangles(count, frame_width)):
        painter.setPen(Qt.PenStyle.NoPen)
        color = BG_COLOR if i % 2 else BG_COLOR_ALT
        painter.setBrush(color)
        painter.drawRect(value_rect)
        # Markers
        if i in marked_values:
            painter.setBrush(MARKER_COLOR)
            painter.drawRect(value_rect.adjusted(0, 0, 0, 0))
        if i == current:
            color = QtGui.QColor(CURSORCOLOR)
            pen = QtGui.QPen(color) if i in marked_values else Qt.NoPen
            brush = Qt.NoBrush if i in marked_values else QtGui.QBrush(color)
            painter.setPen(pen)
            painter.setBrush(brush)
            painter.drawRect(value_rect)
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
