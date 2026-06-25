
from functools import partial

from PySide6 import QtGui, QtCore, QtWidgets

import embarker.commands as ebc
from embarker import preferences

from embarker.timeline.draw import (
    DEFAULT_SLIDER_HEIGHT, MARKER_COLOR, draw_slider, draw_zoom_slider)


THUMBNAIL_HEIGHT = 200


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


class MergeAnnotations(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Conflicting Annotations')
        self.resize(250, 100)
        text = 'There already exists an annotation on this frame.'
        label = QtWidgets.QLabel(text)
        self.merge_button = QtWidgets.QPushButton('Merge')
        self.override_button = QtWidgets.QPushButton('Override')
        self.cancel_button = QtWidgets.QPushButton('Cancel')
        self.result = 0

        button_layout = QtWidgets.QHBoxLayout()
        button_layout.addWidget(self.merge_button)
        button_layout.addWidget(self.override_button)
        button_layout.addWidget(self.cancel_button)

        self.cancel_button.clicked.connect(partial(self.set_result, 0))
        self.merge_button.clicked.connect(partial(self.set_result, 1))
        self.override_button.clicked.connect(partial(self.set_result, 2))

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(label)
        layout.addLayout(button_layout)

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
        self.thumbnail = None
        self.thumbnails = dict()  # hold resized pixmap for optimisation

        self.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding,
            QtWidgets.QSizePolicy.Expanding)
        self.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)
        self.setFixedHeight(preferences.get(
            'timeline_height', DEFAULT_SLIDER_HEIGHT))
        self.setMouseTracking(True)

    @property
    def value(self):
        return ebc.get_session().playlist.frame

    @property
    def maximum(self):
        if self.end_frame:
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

    def event(self, event):
        if event.type() != QtCore.QEvent.ToolTip:
            self.thumbnail = None
            return super().event(event)

        position = event.pos().toPointF()
        frame = self.get_frame_from_point(position)
        ctr_idx = ebc.get_session().playlist.get_container_index(frame)
        # Create a copy of the container, to not break reading head
        cur_container = ebc.get_session().playlist.containers[ctr_idx]
        frame = ebc.get_session().playlist.frames_frames[frame]
        thumbnail, width = cur_container.thumbnail(
            THUMBNAIL_HEIGHT, frame)
        offset = QtCore.QPoint(-width / 2, -THUMBNAIL_HEIGHT - 14)
        global_pos = event.globalPos() + offset

        self.thumbnail = QtWidgets.QLabel()
        self.thumbnail.setPixmap(thumbnail)
        self.thumbnail.setWindowFlag(
            QtCore.Qt.ToolTip | QtCore.Qt.FramelessWindowHint)
        self.thumbnail.move(global_pos)
        self.thumbnail.show()
        return super().event(event)

    def left_click_event(self, event):
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
            self.left_click_event(event)

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
        bracket_frame = frame in [
            session.playlist.playback_start, session.playlist.playback_end]

        if frame in annoted_frames and (ctrl_pressed() or shift_pressed()):
            QtWidgets.QApplication.setOverrideCursor(
                QtCore.Qt.CursorShape.SizeHorCursor)
        elif bracket_frame and not ctrl_pressed() and not shift_pressed():
            QtWidgets.QApplication.setOverrideCursor(
                QtCore.Qt.CursorShape.SizeHorCursor)
        else:
            QtWidgets.QApplication.restoreOverrideCursor()

        if not self.maximum:
            return
        if self._mlb_pressed:
            point = event.position().toPoint()
            self.set_value_from_point(point)
            if self.move_start_bracket:
                ebc.set_playback_start(frame)
            elif self.move_end_bracket:
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

        if self.start_frame or self.end_frame:
            self.start_frame = None
            self.end_frame = None
            self.update()
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
        value = int(point.x() / self.width() * self.count())
        return max(self.minimum, min(self.maximum, value + offset))

    def zoom(self):
        if self.start_frame or self.end_frame:
            self.start_frame = None
            self.end_frame = None
            self.update()
            return

        session = ebc.get_session()
        self.start_frame = session.playlist.playback_start
        self.end_frame = session.playlist.playback_end
        self.update()

    def reset(self):
        self.start_frame = None
        self.end_frame = None
        ebc.get_session().playlist.playback_start = None
        ebc.get_session().playlist.playback_end = None
        self.update()

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

        zoom_action = ebc.get_action('ZoomTimeline')
        menu.addAction(zoom_action)

        reset_action = ebc.get_action('ResetTimeline')
        menu.addAction(reset_action)

        delete_action = QtGui.QAction(f'Delete annotation on frame: {frame}')
        menu.addAction(delete_action)
        delete_action.setEnabled(frame_exists)

        text = f'Change annotation color on frame: {frame}'
        recolor_action = QtGui.QAction(text)
        menu.addAction(recolor_action)
        recolor_action.setEnabled(frame_exists)

        action = menu.exec(self.mapToGlobal(point))

        if action == delete_action:
            index = ebc.get_session().get_annotation_index(frame)
            del ebc.get_session().annotations[index]

        if action == recolor_action:
            options = QtWidgets.QColorDialog.DontUseNativeDialog
            annotation = ebc.get_session().get_annotation_at(frame)
            default_color = annotation.metadata.get('user_color')
            default_color = default_color or MARKER_COLOR
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
            play_start = self.start_frame or 0

            moving_metadata = None
            if self.moving_model:
                metadata_color = self.moving_model.metadata.get('user_color')
                moving_metadata = metadata_color
                if not moving_metadata:
                    moving_metadata = MARKER_COLOR.name()

            if preferences.get('timeline_draw_style') == 'Thumbnails':
                self.thumbnails = {}
                count = 0
                for container in ebc.get_session().playlist.containers:
                    # contains pixmap and width
                    height = preferences.get(
                        'timeline_height', DEFAULT_SLIDER_HEIGHT)
                    self.thumbnails[count] = container.thumbnail(height)
                    count += container.length
            else:
                self.thumbnails = None

            draw_slider(
                painter,
                self.rect(),
                self.count(),
                play_start,
                session.playlist.frame,
                session.playlist.frames_images.keys(),
                moving_metadata,
                list(session.playlist.first_frames.values()),
                self.thumbnails,
            )

            # draw mini slider for zoom preview
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
