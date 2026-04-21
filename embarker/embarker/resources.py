import os
from os.path import dirname
from PySide6.QtGui import QIcon


def get_icon(filename):
    return QIcon(f'{dirname(__file__)}/icons/{filename}')


def get_css():
    return f'{os.path.dirname(__file__)}/css/dark.css'