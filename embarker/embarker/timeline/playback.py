
from functools import partial
from PySide6 import QtGui, QtWidgets
import embarker.commands as ebc


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
