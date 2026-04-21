import os
import msgpack
import platform
from PySide6 import QtCore
import embarker.commands as ebc


DEFAULT_FILENAME = 'default_session'


class AutoSave(QtCore.QObject):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.timer = QtCore.QBasicTimer()
        self.schedule_auto_save = False

    def start(self):
        self.timer.start(300000, self)  # Every 5 minutes

    def restart_timer(self):
        self.timer.stop()
        self.start()

    def timerEvent(self, _):
        if ebc.get_session().is_empty():
            print('do not autosave empty session')
            return
        if ebc.get_main_window().media_player.is_playing():
            self.schedule_auto_save = True
            return
        self.auto_save()

    def auto_save(self):
        if ebc.get_session().filepath is None:
            filepath = get_default_autosave_filepath()
        else:
            directory = os.path.dirname(ebc.get_session().filepath)
            filename = os.path.basename(ebc.get_session().filepath)
            basename = os.path.splitext(filename)[0]
            filepath = get_autosave_incremental_filename(directory, basename)

        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        data = ebc.get_session().serialize()
        with open(filepath, 'wb') as f:
            print('Autosave', filepath)
            msgpack.dump(data, f)
        self.schedule_auto_save = False


def get_documents_folder():
    system = platform.system()

    if system == "Windows":
        try:
            import ctypes
            from ctypes.wintypes import MAX_PATH

            CSIDL_PERSONAL = 5  # My Documents
            SHGFP_TYPE_CURRENT = 0
            buf = ctypes.create_unicode_buffer(MAX_PATH)
            ctypes.windll.shell32.SHGetFolderPathW(
                None, CSIDL_PERSONAL, None, SHGFP_TYPE_CURRENT, buf)
            return buf.value
        except Exception:
            return os.environ.get('USERPROFILE', '') + '/Documents'
    return os.environ.get('HOME', '') + '/Documents'


def get_default_autosave_filepath():
    directory = f'{get_documents_folder()}/Embarker/autosaves'
    return get_autosave_incremental_filename(directory, DEFAULT_FILENAME)


def get_autosave_incremental_filename(directory, basename):
    if not os.path.exists(directory):
        return f'{directory}/{basename}.autosave.01.embk'
    filepaths = [
        f'{directory}/{f}' for f in os.listdir(directory) if
        not os.path.isdir(f'{directory}/{f}') and
        f.startswith(basename) and
        f.split('.')[-2].isdigit() and
        os.path.splitext(f)[-1] == '.embk']
    if not filepaths:
        return f'{directory}/{basename}.autosave.01.embk'
    filepaths.sort(key=os.path.getmtime)
    last = filepaths[-1]
    number = int(last.split('.')[-2])
    number = number + 1 if number < 5 else 1
    return f'{directory}/{basename}.autosave.{number:02d}.embk'
