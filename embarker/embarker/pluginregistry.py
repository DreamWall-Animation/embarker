import os
import traceback
from PySide6 import QtWidgets, QtCore
from embarker import callback
from embarker.api import (
    EmbarkerDockWidget, EmbarkerToolBar, EmbarkerMenu)
from embarker.plugin import extract_module_available_ui_classes, unload_plugin
import embarker.commands as ebc


class PluginRegistry(QtCore.QObject):
    changed = QtCore.Signal()

    def __init__(self):
        super().__init__()
        self.plugins_modules = {}

    def sort_plugin_by_names(self):
        self.plugins_modules = {
            m: d for m, d in
            sorted(self.plugins_modules.items(), key=lambda v: v[1]['name'])}

    def register_plugin_module(self, plugin_module_path):
        plugin_module_path = os.path.normpath(plugin_module_path)
        if plugin_module_path in self.plugins_modules:
            raise ValueError(
                f"Module already registered: {plugin_module_path}")
        n = f'{os.path.splitext(os.path.basename(plugin_module_path))[-1]}'
        self.plugins_modules[plugin_module_path] = {
            'id': None,
            'name': n,
            'toolbars': [],
            'description': '',
            'classes': [],
            'loaded': False,
            'callbacks': {},
            'docks': []}
        self.sort_plugin_by_names()
        self.changed.emit()

    def load_plugin_module(self, plugin_module_path, initialize_classes=False):
        if plugin_module_path not in self.plugins_modules:
            self.register_plugin_module(plugin_module_path)
        try:
            plugin_id, module, classes = extract_module_available_ui_classes(
                plugin_module_path)
        except BaseException:
            self.plugins_modules[plugin_module_path] = {
                'id': plugin_module_path,
                'name': '---',
                'author': '---',
                'version': '---',
                'description': traceback.format_exc(),
                'actions': [],
                'classes': [],
                'menus': [],
                'loaded': False,
                'docks': [],
                'callbacks': {},
                'toolbars': []}
            return
        a = getattr(module, '__author__', getattr(module, "__authors__", ""))
        callbacks = getattr(module, 'CALLBACKS', {})
        self.plugins_modules[plugin_module_path] = {
            'id': plugin_id,
            'name': module.PLUGIN_NAME,
            'author': a,
            'version': f'{getattr(module, "__version__", "---")}',
            'description': module.__doc__,
            'actions': [],
            'classes': classes,
            'loaded': True,
            'docks': [],
            'callbacks': callbacks,
            'menus': [],
            'toolbars': []}
        self.sort_plugin_by_names()
        self.changed.emit()
        # Register callbacks
        for event, functions in callbacks.items():
            for function in functions:
                callback.register_callback(event, plugin_id, function)
        # Initialize UIs. This is not done at startup, the class init is
        # deffered to ensure the order of initialization works around plugins
        if not initialize_classes:
            return
        classes = self.plugins_modules[plugin_module_path]['classes']
        classes.sort(key=lambda cls: cls.APPEARANCE_PRIORITY, reverse=True)
        callback.perform(callback.ON_PLUGIN_STARTUP, plugin_id)
        for cls in classes:
            self.initialize_plugin_class(plugin_module_path, cls)

    def unload_plugin_module(self, plugin_module_path):
        if self.plugins_modules[plugin_module_path]['id'] is None:
            return
        plugin_module_path = os.path.normpath(plugin_module_path)

        docks = self.plugins_modules[plugin_module_path]['docks']
        for dock in docks:
            ebc.get_main_window().removeDockWidget(dock)
            ebc.get_main_window().docks.remove(dock.widget())
            dock.close()
            dock.deleteLater()
            dock.widget().deleteLater()
        self.plugins_modules[plugin_module_path]['docks'] = []

        toolbars = self.plugins_modules[plugin_module_path]['toolbars']
        for toolbar in toolbars:
            ebc.get_main_window().toolbars.remove(toolbar)
            ebc.get_main_window().removeToolBar(toolbar)
            toolbar.close()
            toolbar.deleteLater()

        menus = self.plugins_modules[plugin_module_path]['menus']
        for menu in menus:
            ebc.get_main_window().menuBar().removeAction(menu.menuAction())
            ebc.get_main_window().menus.remove(menu)
            menu.deleteLater()

        actions = self.plugins_modules[plugin_module_path]['actions']
        for action_id in actions:
            action = ebc.get_main_window().actionregistry.get(action_id)
            ebc.get_main_window().removeAction(action)
            ebc.get_main_window().actionregistry.remove(action_id)
            action.deleteLater()
        self.plugins_modules[plugin_module_path]['actions'] = []
        self.plugins_modules[plugin_module_path]['loaded'] = False
        unload_plugin(self.plugins_modules[plugin_module_path]['id'])
        callback.unregister_callbacks(
            self.plugins_modules[plugin_module_path]['id'])
        self.plugins_modules[plugin_module_path]['id'] = None
        self.changed.emit()

    def initialize_plugin_class(self, plugin_module, cls):
        if issubclass(cls, EmbarkerDockWidget):
            actions = self.initialize_dock(plugin_module, cls)
        elif issubclass(cls, EmbarkerToolBar):
            actions = self.initialize_toolbar(plugin_module, cls)
        elif issubclass(cls, EmbarkerMenu):
            actions = self.initialize_menu(plugin_module, cls)
        else:
            raise ValueError(
                f'{cls} does not inherit from DwEmbarker api classes')
        ids = [a['id'] for a in actions]
        self.plugins_modules[plugin_module]['actions'].extend(ids)
        ebc.get_main_window().actionregistry.add_actions(actions)
        ebc.get_main_window().actionregistry.create_actions()
        self.changed.emit()

    def initialize_menu(self, plugin_module, cls):
        menu: EmbarkerMenu = cls()
        menu.setTitle(menu.TITLE)
        self.plugins_modules[plugin_module]['menus'].append(menu)
        ebc.get_main_window().menus.append(menu)
        ebc.get_main_window().menuBar().addMenu(menu)
        return menu.get_actions()

    def initialize_toolbar(self, plugin_module, cls):
        toolbar = cls()
        toolbar.setWindowTitle(toolbar.TITLE)
        toolbar.setObjectName(toolbar.OBJECT_NAME)
        ebc.get_main_window().addToolBar(toolbar.TOOLBAR_AREA, toolbar)
        ebc.get_main_window().toolbars.append(toolbar)
        self.plugins_modules[plugin_module]['toolbars'].append(toolbar)
        if not toolbar.VISIBLE_BY_DEFAULT:
            toolbar.hide()
        return toolbar.get_actions()

    def initialize_dock(self, plugin_module, cls):
        widget = cls()
        dock = QtWidgets.QDockWidget()
        dock.setWindowTitle(widget.TITLE)
        dock.setObjectName(widget.OBJECT_NAME)
        dock.setWidget(widget)
        ebc.get_main_window().addDockWidget(widget.DOCK_AREA, dock)
        self.plugins_modules[plugin_module]['docks'].append(dock)
        ebc.get_main_window().docks.append(widget)
        if not widget.VISIBLE_BY_DEFAULT:
            dock.hide()
        return widget.get_actions()

    def initialize_all_plugins(self):
        modules_to_load = [
            m for m, d in self.plugins_modules.items()
            if d is None or d['loaded'] is False]
        for module_path in modules_to_load:
            self.load_plugin_module(module_path)
            callback.perform(
                callback.ON_PLUGIN_STARTUP,
                plugin_id=self.plugins_modules[module_path]['id'])
        classes = [
            (cls, module)
            for module, d in self.plugins_modules.items()
            for cls in d['classes']
            if d is not None and d['loaded'] is True]
        classes.sort(key=lambda data: data[0].APPEARANCE_PRIORITY, reverse=True)
        for cls, module in classes:
            self.initialize_plugin_class(module, cls)
