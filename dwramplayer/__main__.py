
import os
import sys
from PySide6 import QtWidgets

from dwramplayer.mainwindow import MainWindow
from dwramplayer.plugin import extract_module_available_dock
from dwramplayer.playlist import EXTENSIONS
import argparse


parser = argparse.ArgumentParser()
parser.add_argument('filepaths', nargs='+', help='List of videos file paths')
parser.add_argument('-pp', '--python_plugins', nargs='+', help='List python plugin script')
parser.add_argument('-osn', '--os_native_style', default=False, action='store_true')

args = parser.parse_args()

app = QtWidgets.QApplication(sys.argv)
if not args.os_native_style:
    stylesheet_filepath = f'{os.path.dirname(__file__)}/dark.css'
    with open(stylesheet_filepath, 'r') as f:
        app.setStyleSheet(f.read())


python_plugins_modules = args.python_plugins or []
python_plugins_modules.extend(
    m for m in os.environ.get('DWRAMPLAYER_PLUGINS', '').split(';') if m)

plugin_classes = []
if python_plugins_modules:
    for module_filepath in python_plugins_modules:
        plugin_classes.extend(extract_module_available_dock(module_filepath))
plugin_classes.sort(key=lambda cls: cls.APPEARANCE_PRIORITY)
print(plugin_classes, python_plugins_modules)
window = MainWindow(plugin_classes=plugin_classes)
window.show()

if args.filepaths:
    video_paths = [p for p in args.filepaths if p.endswith(EXTENSIONS)]
    video_paths = [os.path.expandvars(p) for p in video_paths]
    window.load_videos(video_paths)
        # video_paths = [
        #     os.path.expandvars(
        #         '$SAMPLES/ep311_sq0060_sh0880_spline_v003.mov'),
        #     os.path.expandvars(
        #         '$SAMPLES/movie-0030-0290_compositing.0001.mp4'),
        #     # os.path.expandvars(
        #     #     '$SAMPLES/MAINPASS_CHR_Beauty/MAINPASS_CHR_Beauty_1_00001.exr')
        # ]
    # if video_paths:
    #     window.load_videos(video_paths)



sys.exit(app.exec())


# if __name__ == '__main__':



#     window.show()
#     window.move(300, 150)
#     sys.exit(app.exec())