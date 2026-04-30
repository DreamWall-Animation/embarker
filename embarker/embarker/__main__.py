"""
Embarker: Review and Annotation Video Player

Embarker is a lightweight video player for review and pipeline integration.
Features

    Drawn Annotations, Multi-Layer
    Support for freehand drawing with multiple annotation layers.

    Real-Time RAM Player
    Video playback fully loaded into RAM for frame-accurate real-time
    performance.

    Audio Scrubbing
    Audio feedback during timeline scrubbing.

    Python Plugin Injection
    Fully scriptable via a simple Python plugin system.

    Open Source and Free
    Distributed under an open license. No fees.

    Pipeline-Oriented
    Designed for easy integration into production pipelines.

    Minimalist and Efficient
    Focused on performance with a sober interface.

Embarker is a tool for professionals who require control and simplicity.
"""

import os
import sys
import ctypes
import platform
import argparse

from PySide6 import QtWidgets

from embarker.mainwindow import EmbarkerMainWindow
from embarker.decoder import EXTENSIONS
from embarker.resources import get_css, get_icon
import embarker.commands as ebc


FROZEN = getattr(sys, 'frozen', False)


parser = argparse.ArgumentParser()
parser.add_argument('filepaths', nargs='*', help='List of videos file paths',)
parser.add_argument('-pp', '--python_plugins', nargs='+', help='List python plugin script')
parser.add_argument('-pl', '--playlist_file', help='Playlist filepath')
parser.add_argument('-s', '--session_file', help='Session filepath')
doc = """\
Open the session data as a new file.
Embarker ignore the path opened and considere is an unsaved file.
This is important in some pipeline to avoid erasing published review which are
not supposed to be erased. This will force user to save as the review
"""
parser.add_argument(
    '-asn', '--open_session_file_as_new_file',
    default=False, action='store_true', help=doc)
parser.add_argument(
    '-osn', '--os_native_style', default=False, action='store_true')
parser.add_argument('-d', '--debug', default=False, action='store_true')
parser.add_argument('-c', '--command_verbosity', default=False, action='store_true')
parser.add_argument(
    '-env', '--environment_files', nargs='+',
    help='List additional environment files (.env)')
args = parser.parse_known_args()[0]


environment_files = args.environment_files or []
if FROZEN:
    # Add custom env file
    os.environ['HERE'] = os.path.dirname(sys.executable)
    environment_file = f'{os.path.dirname(sys.executable)}/.env'
    if os.path.exists(environment_file):
        environment_files.append(environment_file)


for environment_file in environment_files:
    try:
        with open(environment_file, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                key, _, value = line.partition("=")
                value = os.path.expandvars(value.strip())
                if '+=' in line and key.strip() in os.environ:
                    os.environ[key.strip()] += value
                else:
                    os.environ[key.strip()] = value
    except BaseException:
        continue # Invalid file


if platform.system() == 'Windows':
    # Make Windows not group python apps together in taskbar:
    id_ = 'com.dreamwall.embarker'
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(id_)


app = QtWidgets.QApplication(sys.argv)
app.setWindowIcon(get_icon('milo.ico'))


if not args.os_native_style:
    app.setStyle('fusion')
    stylesheet_filepath = get_css()
    with open(stylesheet_filepath, 'r') as f:
        app.setStyleSheet(f.read())


window = EmbarkerMainWindow()
window.setWindowIcon(get_icon('milo.ico'))
window.show()


python_plugins_modules = args.python_plugins or []
python_plugins_modules.extend(
    m for m in os.environ.get('EMBARKER_PLUGIN_PATHS', '').split(';') if m)
if FROZEN:
    directory = f'{os.path.dirname(sys.executable)}/plugins'
    python_plugins_modules.extend(
        f'{directory}/{f}' for f in os.listdir(directory)
        if f.lower().endswith(('.py', '.pyc', '.pyw')))


for module in python_plugins_modules:
    window.pluginregistry.register_plugin_module(module)
window.pluginregistry.initialize_all_plugins()


if args.filepaths:
    video_paths = [p for p in args.filepaths if p.endswith(EXTENSIONS)]
    video_paths = [os.path.expandvars(p) for p in video_paths]
    ebc.load_videos(video_paths)


if args.debug:
    os.environ['EMBARKER_DEBUG'] = '1'


if args.command_verbosity:
    os.environ['EMBARKER_COMMANDS_VERBOSITY'] = '1'


if args.playlist_file:
    ebc.load_playlist(args.playlist_file)


if args.session_file:
    ebc.open_session(
        args.session_file, as_new_file=args.open_session_file_as_new_file)


window.actionregistry.register_shortcuts()
window.store_state_as_default()
window.restore_save_state()
window.autosave.start()


app.aboutToQuit.connect(window.quit)
sys.exit(app.exec())
