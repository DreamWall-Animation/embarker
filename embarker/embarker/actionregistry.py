from PySide6 import QtGui
from embarker import preferences
import embarker.commands as ebc

class ActionRegistry:
    def __init__(self):
        self.descriptions = {}
        self.actions = {}
        self.groups = {}

    def add_actions(self, action_descriptions):
        ids = [a['id'] for a in action_descriptions]
        existing = [id_ for id_ in ids if id_ in self.descriptions]
        if existing:
            raise ValueError(f'Some actions already registered: {existing}')
        self.descriptions.update({a['id']: a for a in action_descriptions})

    def get(self, action_id):
        return self.actions.get(action_id)

    def existing_shortcuts(self):
        existing_shortcuts = preferences.get('shortcuts', {}).copy()
        for action_id, description in self.descriptions.items():
            if description['shortcut'] and action_id not in existing_shortcuts:
                existing_shortcuts[action_id] = description['shortcut']
        return existing_shortcuts

    def remove(self, action_id):
        del self.actions[action_id]
        del self.descriptions[action_id]

    def create_actions(self):
        for action_id, action_description in self.descriptions.items():
            if action_id in self.actions:
                continue
            action = QtGui.QAction(
                action_description['text'], ebc.get_main_window())
            action.triggered.connect(action_description['method'])
            if action_description['icon']:
                action.setIcon(action_description['icon'])
            if action_description['group']:
                group = self.groups.setdefault(
                    action_description['group'],
                    QtGui.QActionGroup(ebc.get_main_window()))
                group.addAction(action)
                group.setExclusive(bool(action_description['group']))
            if action_description['checkable']:
                action.setCheckable(True)
            self.actions[action_id] = action
            ebc.get_main_window().addAction(action)

    def register_shortcuts(self):
        shortcut_overrides = preferences.get('shortcuts', {})
        for action_id, action in self.actions.items():
            description = self.descriptions[action_id]
            seq = shortcut_overrides.get(action_id, ...)
            seq = seq if seq is not ... else description['shortcut']
            seq = seq if seq is not None else QtGui.QKeySequence()
            action.setShortcut(QtGui.QKeySequence(seq))

    def list_category_actions(self, category):
        return [
            a for id_, a in self.actions.items()
            if self.descriptions[id_]['category'] == category]

