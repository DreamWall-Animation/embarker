
from functools import partial
from PySide6 import QtWidgets


class MergeAnnotationsDialog(QtWidgets.QDialog):
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
