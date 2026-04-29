
# Write an Embarker Plugin

This guide explains how to create a plugin for Embarker.

---

## What is an Embarker Plugin?

An Embarker plugin extends the application by adding:

- UI elements (Toolbars, Menus, Dock Widgets)
- Event callbacks
- Integration with the application state


## Basic Plugin Structure

A plugin is a Python file containing:

```python
"""Plugin description"""
```

### Required elements:

```python
PLUGIN_NAME = 'MyPlugin'
__version__ = '1.0'
__author__ = 'Your Name'
```

## Classes

To customize the interface and create dock widgets, menus, and toolbars, you need to subclass a class provided in the API:
```python
from embarker.api import EmbarkerToolBar, EmbarkerMenu, EmbarkerDockWidget
```

Each UI class MUST define all required class constants.
If you forget them, the plugin will fail to initialize

Every constructors are similar:

```python
def __init__(self, session: Session, commands: Commands, parent=None):
```

Please refer to the corresponding documentation pages for the objects provided by the constructor: [Session](session.md) and [Commands](commands.md).

### EmbarkerToolBar

```python
class MyToolbar(EmbarkerToolBar):
    TITLE = "My Toolbar"
    TOOLBAR_AREA = QtCore.Qt.TopToolBarArea
    OBJECT_NAME = "MyToolbar"
    APPEARANCE_PRIORITY = 98
    VISIBLE_BY_DEFAULT = True
    ENABLE_DURING_PLAYBACK = True
```

### EmbarkerMenu

```python
class MyMenu(EmbarkerMenu):
    TITLE = "My Menu"
    APPEARANCE_PRIORITY = 98
```

### EmbarkerDockWidget

```python
class MyDock(EmbarkerDockWidget):
    TITLE = "My Dock"
    DOCK_AREA = QtCore.Qt.LeftDockWidgetArea
    OBJECT_NAME = "MyDock"
    APPEARANCE_PRIORITY = 98
    VISIBLE_BY_DEFAULT = False
    ENABLE_DURING_PLAYBACK = True
```

## Common methods

### def get_actions(self):

The `get_actions()` method allows you to define new application QAction.
If implemented, it must return a strictly structured list of dictionaries.

```python
def get_actions(self):
    return [{
        'id': 'TestAction',
        'text': 'TestAction',
        'category': 'Global',
        'icon': None,
        'group': None,
        'method': lambda *_: print('Hello ToolBar'),
        'checkable': False,
        'shortcut': None
    }]
```

- `id` must be unique across the entire application
- `icon` path to image.
- `method` must be callable
- `shortcut` must be a valid QKeySequence or None
- The structure must be respected strictly


### def update_view(self)

update_view() is a callback method.

It is automatically triggered when:
- the frame changes
- the application updates the UI


##  Minimal Example

```python
"""
This is a minimal example plugin
"""

import os
from PySide6 import QtWidgets, QtCore
from embarker.api import (
    EmbarkerToolBar, Session, Commands, EmbarkerMenu, EmbarkerDockWidget)
from embarker import callback


PLUGIN_NAME = 'MinimalEmbarkerPlugin'
__version__ = '1.0'
__author__ = 'David Williams'


class DockExample(EmbarkerDockWidget):
    TITLE = 'Dock example'
    DOCK_AREA = QtCore.Qt.LeftDockWidgetArea
    OBJECT_NAME = 'MEP-DockExampe'
    APPEARANCE_PRIORITY = 0
    VISIBLE_BY_DEFAULT = True
    ENABLE_DURING_PLAYBACK = True

    def __init__(self, parent=None):
        super().__init__(session)
        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(QtWidgets.QLabel('Dock Test'))
        layout.addStretch()

    def update_view(self):
        print('Current frame: ', self.session.playlist.frame)

    def get_actions(self):
        return [{
            'id': 'TestAction',
            'text': 'Test',
            'category': 'Test',
            'icon': None,
            'group': None,
            'method': lambda *_: print('Test action triggered'),
            'checkable': False,
            'shortcut': QtGui.QKeySequence('CTRL+T'),
        }]


class ToolbarExemple(EmbarkerToolBar):
    TITLE: str = "Test"
    TOOLBAR_AREA: QtCore.Qt.ToolBarArea = QtCore.Qt.TopToolBarArea
    OBJECT_NAME: str = 'TestToolbar'
    APPEARANCE_PRIORITY: int = 98
    VISIBLE_BY_DEFAULT: bool = True
    ENABLE_DURING_PLAYBACK: bool = True

    def __init__(self, parent=None):
        super().__init__(session, commands, parent=parent)
        button = QtWidgets.QPushButton('Test')
        self.addWidget(button)


class TestMenu(EmbarkerMenu):
    TITLE = 'Test'
    APPEARANCE_PRIORITY = 98

    def __init__(self, parent=None):
        super().__init__(session, commands, parent=parent)
        self.addAction('Test 1')
        self.addAction('Test 2')
        self.addAction('Test 3')
        self.addAction('Test 4')
        self.addAction('Test 5')
        self.addAction('Test 6')


# Register callback the plugin must register.
CALLBACKS = {
    callback.BEFORE_NEW_SESSION: [lambda *_: print('New session will be created')]
}

# Register UI classes the plugin must register.
UI_CLASSES = [
    TestMenu,
    TestToolbar,
    DockExample,
]
```
