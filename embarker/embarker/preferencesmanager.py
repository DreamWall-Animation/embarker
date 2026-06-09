import os
from PySide6 import QtWidgets, QtCore, QtGui
from embarker import preferences
from embarker.autosave import get_documents_folder
import embarker.commands as ebc

class PreferencesWindow(QtWidgets.QWidget):

    def __init__(self, parent=None):
        super().__init__(parent, QtCore.Qt.Tool)
        self.setWindowTitle('Preferences')

        self.preferences = {
            "Autosave" : AutosaveWidget(),
            "User Color" : UserColorWidget()
        }

        self.categories = PreferencesCategoriesModel(
            list(self.preferences.keys()))
        self.categories_view = QtWidgets.QListView(parent)
        self.categories_view.setModel(self.categories)
        self.categories_view.selectionModel().selectionChanged.connect(
            lambda _:self.change_option_panel())
        index = self.categories.index(0, 0)
        self.categories_view.selectionModel().select(
            index, QtCore.QItemSelectionModel.Select)

        items_layout = QtWidgets.QVBoxLayout()
        for item in self.preferences.keys():
            self.preferences[item].setVisible(False)
            items_layout.addWidget(self.preferences[item])
        items_layout.addStretch()

        layout = QtWidgets.QHBoxLayout(self)
        layout.addWidget(self.categories_view)
        layout.addLayout(items_layout)
        layout.setStretchFactor(self.categories_view, 1)
        layout.setStretchFactor(items_layout, 3)
        self.change_option_panel()

    def sizeHint(self):
        return QtCore.QSize(800, 600)

    def change_option_panel(self):
        index = self.categories_view.selectionModel().selectedRows()[0].row()
        key = list(self.preferences.keys())[index]
        for item_key in self.preferences.keys() :
            self.preferences[item_key].setVisible(item_key == key)


class PreferencesCategoriesModel(QtCore.QAbstractListModel):

    def __init__(self, values, parent=None):
          super().__init__(parent)
          self.values =values

    def data(self, index, role=None):
        if role == QtCore.Qt.ItemDataRole.DisplayRole :
            return self.values[index.row()]
        return None

    def rowCount(self, parent=None):
        return len(self.values)


class AutosaveWidget(QtWidgets.QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        timer = self.get_timer()

        timer_label = QtWidgets.QLabel("Autosave Timer (in seconds)")
        int_validator = QtGui.QIntValidator()
        self.timer_line = QtWidgets.QLineEdit()
        self.timer_line.setText(str(timer))
        self.timer_line.setValidator(int_validator)

        filepath_label = QtWidgets.QLabel("Autosave Filepath")
        self.filepath_line = QtWidgets.QLineEdit("")
        self.filepath_line.setText(self.get_filepath())

        save_button = QtWidgets.QPushButton("Save changes")
        save_button.clicked.connect(lambda _: self.save_settings())
        reset_button = QtWidgets.QPushButton("Reset Settings")
        reset_button.clicked.connect(lambda _: self.reset_settings())

        layout = QtWidgets.QFormLayout(self)
        layout.addRow(timer_label, self.timer_line)
        layout.addRow(filepath_label, self.filepath_line)
        buttons_layout = QtWidgets.QHBoxLayout()
        buttons_layout.addWidget(reset_button)
        buttons_layout.addWidget(save_button)
        layout.addRow(QtWidgets.QLabel(), buttons_layout)

    def get_timer(self):
        if preferences.get('autosave_timer'):
            # divide by 100 for seconds instead of ms
            return round(int(preferences.get('autosave_timer')) / 1000)
        return 30 # default value

    def get_filepath(self):
        if preferences.get('autosave_filepath'):
            return preferences.get('autosave_filepath')
        return get_documents_folder()

    def save_settings(self):
        preferences.set('autosave_timer', int(self.timer_line.text()) * 1000)
        filepath = self.filepath_line.text()
        if not os.path.exists(filepath):
            self.filepath_line.setText(self.get_filepath())
            filepath = self.filepath_line.text()
        preferences.set('autosave_filepath', filepath)
        autosave = ebc.get_main_window().autosave
        autosave.restart_timer()

    def reset_settings(self):
        self.filepath_line.setText(get_documents_folder())
        self.timer_line.setText('300')
        preferences.delete('autosave_timer')
        preferences.delete('autosave_filepath')


class UserColorWidget(QtWidgets.QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.user_color = QtGui.QColor('#999900')
        if preferences.get('user_color'):
            self.user_color = QtGui.QColor(preferences.get('user_color'))

        label_text = QtWidgets.QLabel('User Color Options')
        self.open_dialog_button = QtWidgets.QPushButton('Change User Color')
        self.open_dialog_button.clicked.connect(self.open_color_window)
        self.reset_color_button = QtWidgets.QPushButton('Reset Color')
        self.reset_color_button.clicked.connect(self.delete_user_color)

        color_label = QtWidgets.QLabel()
        canvas = QtGui.QPixmap(150, 50)
        canvas.fill(self.user_color)
        self.paint_contour(canvas)
        color_label.setPixmap(canvas)

        self.layout = QtWidgets.QFormLayout(self)
        self.layout.addRow(label_text, self.open_dialog_button)
        self.layout.addRow(QtWidgets.QLabel(), self.reset_color_button)
        self.layout.addRow(QtWidgets.QLabel(), color_label)

    def delete_user_color(self):
        preferences.delete('user_color')
        self.user_color = QtGui.QColor('#999900')
        self.refresh_color()

    def refresh_color(self):
        self.layout.removeRow(2)
        color_label = QtWidgets.QLabel()
        canvas = QtGui.QPixmap(150, 50)
        canvas.fill(self.user_color)
        self.paint_contour(canvas)
        color_label.setPixmap(canvas)
        self.layout.addRow(QtWidgets.QLabel(), color_label)

    def paint_contour(self, canvas):
        painter = QtGui.QPainter(canvas)
        pen = QtGui.QPen(QtCore.Qt.black)
        pen.setWidth(8)
        painter.setPen(pen)
        painter.drawRect(0, 0, 150, 50)
        painter.end()

    def open_color_window(self):
        options = QtWidgets.QColorDialog.ColorDialogOption.DontUseNativeDialog
        color = QtWidgets.QColorDialog.getColor(
            self.user_color.name(),
            parent=self,
            options=options,
            title='Pick user color')
        if color.isValid() :
            preferences.get('user_color')
            preferences.set('user_color', color.name())
            self.change_user_color(color)

    def change_user_color(self, color):
        self.user_color = color
        self.user_color.setAlpha(255)
        self.refresh_color()


def reset_preferences(_):
    r =  QtWidgets.QMessageBox.question(
        None,
        'Reset preferences ?',
        'This action is not undoable.\nWould you like to continue?')
    if r == QtWidgets.QMessageBox.Yes:
        preferences.delete_all()
