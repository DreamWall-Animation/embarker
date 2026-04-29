from PySide6 import QtWidgets, QtCore, QtGui
# for API import
from paintcanvas.model import CanvasModel
from embarker import callback


class EmbarkerDockWidget(QtWidgets.QWidget):
    """
    Class parent to create a custom dock widget reacting to video state.
    Constants to configure:
        DOCK_AREA:
            Default QMainWindow dock area where the widget will be added.
        TITLE:
            Title of the dock.
        OBJECT_NAME:
            Unique Qt object name, used to save and restore state.
        APPEARANCE_PRIORITY:
            Determines the order in which plugin panels are created.
        VISIBLE_BY_DEFAULT:
            Visibility state at first startup.
        ENABLE_DURING_PLAYBACK:
            Remain accessible during playback or not.
    """
    DOCK_AREA: QtCore.Qt.DockWidgetArea
    TITLE: str
    OBJECT_NAME: str
    APPEARANCE_PRIORITY: int = 0
    VISIBLE_BY_DEFAULT: bool = True
    ENABLE_DURING_PLAYBACK: bool = True

    def update_view(self):
        """
        Callback method to implement to manage when the current frame is
        changed from the player and data must be changed.
        This is NOT triggered when playback is active.
        """
        pass

    def get_actions(self) -> dict[str, QtGui.QAction]:
        """
        Method to implement allowing to add custom actions with shortcut to
        the main application
        Output exemple:
        [
            {
                'id': 'About',
                'text': 'About',
                'category': 'Help',
                'icon': None,
                'group': None,
                'method': callable,
                'checkable': False,
                'shortcut': None,
            }, ...
        ]
        """
        return {}


class EmbarkerToolBar(QtWidgets.QToolBar):
    """
    Class parent to create a custom toolbar.
    Constants to configure:
        TOOLBAR_AREA:
            Default QMainWindow ToolBarArea where the widget will be added.
        TITLE:
            Title of the toolbar.
        OBJECT_NAME:
            Unique Qt object name, used to save and restore state.
        APPEARANCE_PRIORITY:
            Determines the order in which plugin toolbar are created.
        VISIBLE_BY_DEFAULT:
            Visibility state at first startup.
        ENABLE_DURING_PLAYBACK:
            Remain accessible during playback or not.
    """
    TOOLBAR_AREA: QtCore.Qt.ToolBarArea
    TITLE: str
    OBJECT_NAME: str
    APPEARANCE_PRIORITY: int = 0
    VISIBLE_BY_DEFAULT: bool = True
    ENABLE_DURING_PLAYBACK: bool = True

    def get_actions(self) -> dict[str, QtGui.QAction]:
        """
        Method to implement allowing to add custom actions with shortcut to
        the main application
        Output exemple:
        [
            {
                'id': 'About',
                'text': 'About',
                'category': 'Help',
                'icon': None,
                'group': None,
                'method': callable,
                'checkable': False,
                'shortcut': None,
            }, ...
        ]
        """
        return {}


class EmbarkerMenu(QtWidgets.QMenu):
    """
    Class parent to create a custom QMenu on the main window.
    Constants to configure:
        TITLE:
            Menu's title.
        APPEARANCE_PRIORITY:
            Determines the order in which plugin menus added to QMainWindows
            main menu.
    """
    TITLE: str
    APPEARANCE_PRIORITY: int = 0

    def get_actions(self) -> dict[str, QtGui.QAction]:
        """
        Method to implement allowing to add custom actions with shortcut to
        the main application
        Output exemple:
        [
            {
                'id': 'About',
                'text': 'About',
                'category': 'Help',
                'icon': None,
                'group': None,
                'method': callable,
                'checkable': False,
                'shortcut': None,
            }, ...
        ]
        """
        return {}
