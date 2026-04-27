from os.path import dirname
from PySide6.QtGui import QIcon


def get_icon(filename):
    return QIcon(f'{dirname(__file__)}/{filename}')
