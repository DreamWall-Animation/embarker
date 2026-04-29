from PySide6 import QtWidgets, QtCore, QtGui
from embarker.api import EmbarkerDockWidget
import embarker.commands as ebc


PLUGIN_NAME = 'Onion Skin'
__version__ = '1.0'
__author__ = 'David Williams'


class OnionSkin(EmbarkerDockWidget):
    TITLE = "Onion Skin"
    DOCK_AREA = QtCore.Qt.LeftDockWidgetArea
    OBJECT_NAME = 'Onion-Skin'
    APPEARANCE_PRIORITY = 98
    VISIBLE_BY_DEFAULT = False
    ENABLE_DURING_PLAYBACK = False

    def __init__(self, parent=None):
        super().__init__( parent)
        self.before = QtWidgets.QLineEdit(
            str(len(ebc.get_session().onionskin.before_opacities)))
        self.before.setValidator(QtGui.QIntValidator(bottom=1, top=20))
        self.before.editingFinished.connect(self.update_onionskin)
        self.after = QtWidgets.QLineEdit(
            str(len(ebc.get_session().onionskin.before_opacities)))
        self.after.setValidator(QtGui.QIntValidator(bottom=1, top=20))
        self.after.editingFinished.connect(self.update_onionskin)

        layout = QtWidgets.QFormLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addRow('Before', self.before)
        layout.addRow('After', self.after)

        self.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding,
            QtWidgets.QSizePolicy.Fixed)

    def update_onionskin(self):
        before = int(self.before.text())
        ebc.get_session().onionskin.before_opacities = [
            (1 / (before + 1)) * (i + 1) for i in range(before)]
        after = int(self.after.text())
        ebc.get_session().onionskin.after_opacities = list(reversed(
            [(1 / (after + 1)) * (i + 1) for i in range(after)]))
        ebc.set_frame(ebc.get_session().playlist.frame)