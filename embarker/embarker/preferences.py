import os
import yaml
import shutil
import platform


PREFERENCES_FILEPATH = os.getenv('EMBARKER_PREFERENCES_FILEPATH')
PREFERENCES_FILENAME = os.getenv('EMBARKER_PREFERENCES_FILENAME')
PREFERENCES_VERSION = 1


def _get_preferences_filepath():
    if PREFERENCES_FILEPATH:
        return PREFERENCES_FILEPATH
    filename = PREFERENCES_FILENAME or 'embarker.yaml'
    home = os.path.expanduser("~")
    if platform.system() =='"Windows':
        return os.path.join(os.getenv("APPDATA"), 'dreamwall', filename)
    elif platform.system() == 'Darwin':
        return os.path.join(
            home, 'Library', 'Application Support',
            'dreamwall', filename)
    else:
        return os.path.join(
            home, ".config", 'dreamwall', filename)

_preferences = []


def get(key, default=''):
    return _preferences[0].get(key, default)


def set(key, value):
    dir_ = os.path.dirname(_preferences[0].file_path)
    if not os.path.exists(dir_):
        os.makedirs(dir_)
    prefs = _preferences[0].get_all()
    prefs[key] = value
    _preferences[0]._write_prefs(prefs)


def delete(key):
    prefs = _preferences[0].get_all()
    if key in prefs:
        del prefs[key]
    _preferences[0]._write_prefs(prefs)


def import_preferences(filepath):
    prefs = _preferences[0].get_all()
    prefs.import_(filepath)


def delete_all():
    _preferences[0].backup()
    _preferences[0]._write_prefs({})


class Preferences:
    def __init__(self):
        self.file_path = _get_preferences_filepath()
        _preferences.append(self)

    def _write_prefs(self, data, filepath=None):
        with open(filepath or self.file_path, 'w') as f:
            return yaml.safe_dump(data, f)

    def export(self, filepath):
        self._write_prefs(self.get_all(), filepath)

    def import_(self, filepath):
        with open(filepath, 'r') as f:
            try:
                data = yaml.safe_load(f)
                self._write_prefs(data)
            except BaseException as e:
                raise ValueError('Fail to load preferences')

    def backup(self):
        if os.path.exists(self.file_path):
            backup_file(self.file_path)

    def get_all(self):
        if not os.path.exists(self.file_path):
            return dict(version=PREFERENCES_VERSION)
        try:
            with open(self.file_path, 'r') as f:
                data = yaml.safe_load(f) or dict(version=PREFERENCES_VERSION)
                if data['version'] != PREFERENCES_VERSION:
                    return dict(version=PREFERENCES_VERSION)
                return data
        except BaseException as e:
            self.backup()
            print(f'WARNING: moved non-readable prefs: "{self.file_path}"')
            return dict(version=PREFERENCES_VERSION)

    def get(self, key, default=''):
        return self.get_all().get(key, default)

    def set(self, key, value):
        dir_ = os.path.dirname(self.file_path)
        if not os.path.exists(dir_):
            os.makedirs(dir_)
        prefs = self.get_all()
        prefs[key] = value
        self._write_prefs(prefs)

    def delete(self, key):
        prefs = self.get_all()
        if key in prefs:
            del prefs[key]
        self._write_prefs(prefs)

    def delete_all(self):
        self.backup()
        self._write_prefs({})

    def __repr__(self):
        return super().__repr__()


def backup_file(file_path):
    new_path = f'{file_path}.bak'
    i = 0
    while os.path.exists(new_path):
        new_path = f'{file_path}.bak{i}'
        i += 1
    shutil.copy2(file_path, new_path)
