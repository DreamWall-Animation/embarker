import os
import base64
from functools import partial

from PySide6 import QtWidgets, QtCore, QtGui
from PySide6.QtCore import Qt

from viewportmapper import NDCViewportMapper
from paintcanvas.canvas import Canvas, CanvasModel
from paintcanvas.widget import SliderSetValueAtClickPosition

import embarker.commands as ebc
from embarker import callback
from embarker.actions import get_default_actions
from embarker.actionregistry import ActionRegistry
from embarker.autosave import AutoSave
from embarker.resources import get_icon
from embarker.player import MediaPlayer
from embarker.pluginregistry import PluginRegistry
from embarker.pluginmanager import PluginManager
from embarker.playlist import Playlist
from embarker.preferences import Preferences
from embarker.decoder import EXTENSIONS
from embarker.relocator import MovieRelocator
from embarker.session import Session
from embarker.shorcutmanager import ShortcutManager
from embarker.timeline import TimeLineWidget, TimelineSlider


WINDOW_TITLE = 'Embarker'

from PySide6 import QtWidgets


class EmbarkerMainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Embarker')
        self.setObjectName('EMBARKER-MAIN-WINDOW')
        self.preferences = Preferences()

        self._clipboard = None

        self.docks = []
        self.toolbars = []
        self.menus = []

        self.zen_mode = False
        self.window_sates = None
        self.viewportmapper = NDCViewportMapper()
        self.default_state = None

        playlist = Playlist()
        self.session = Session(playlist)
        self.actionregistry = ActionRegistry()
        self.pluginregistry = PluginRegistry()
        self.autosave = AutoSave()

        self.media_player = MediaPlayer(self.viewportmapper, playlist)
        self.media_player.current_frame_changed.connect(
            self.current_frame_changed)
        self.media_player.playing_state_changed.connect(
            self.playing_state_changed)

        model = CanvasModel(viewportmapper=self.viewportmapper)
        self.canvas = Canvas(model)
        self.canvas.scrub.connect(self.scrub)
        self.canvas.panzoom_changed.connect(self.media_player.update)
        self.canvas.size_changed.connect(self.media_player.update)
        self.canvas.updated.connect(self.drawed)

        self.shapesettings = self.canvas.get_shape_settings_widget()
        self.shapesettings.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding,
            QtWidgets.QSizePolicy.Fixed)
        self.toolsettings = self.canvas.get_tool_settings_widget()
        self.toolsettings.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding,
            QtWidgets.QSizePolicy.Fixed)
        self.veilsettings = self.canvas.get_wash_settings_widget()
        self.brightness = SliderSetValueAtClickPosition(QtCore.Qt.Horizontal)
        self.brightness.setMinimum(0)
        self.brightness.setMaximum(200)
        self.brightness.setValue(100)
        self.brightness.valueChanged.connect(self.set_brightness)

        self.layerview = self.canvas.get_layer_view()
        self.layerview.edited.connect(self.update)

        self.timeline = TimeLineWidget()
        self.media_player.current_frame_changed.connect(
            self.timeline.update_values)
        self.volume_slider = VolumeSlider()

        self.plugin_manager = PluginManager(self.pluginregistry, self)
        self.shortcut_manager = ShortcutManager(self.actionregistry, self)

        self.movie_relocator = MovieRelocator(self)
        self.recent_session_menu = QtWidgets.QMenu('Recent sessions')
        self.recent_session_menu.aboutToShow.connect(self.show_recent_sessions)

        self.actionregistry.add_actions(get_default_actions(self))
        self.actionregistry.add_actions(self.canvas.get_canvas_actions())
        self.actionregistry.add_actions(self.canvas.get_tool_actions())
        self.actionregistry.create_actions()

        playback_actions = (
            'PrevAnnotation', 'PrevVideo', 'PrevFrame', 'Stop', 'PlayPause',
            'NextFrame', 'NextVideo', 'NextAnnotation')
        playback_buttons = []
        for action_id in playback_actions:
            button = QtWidgets.QToolButton()
            button.setDefaultAction(self.actionregistry.get(action_id))
            playback_buttons.append(button)

        toggle_loop = QtWidgets.QToolButton()
        toggle_loop.setDefaultAction(self.actionregistry.get('ToggleLoopMode'))

        mute_button = QtWidgets.QToolButton()
        mute_button.setDefaultAction(self.actionregistry.get('ToggleMute'))
        self.volume_button = QtWidgets.QToolButton()
        self.volume_button.setIcon(get_icon('volume.png'))
        self.volume_button.released.connect(self.show_volume_slider)

        # Toobars and docks
        file_toolbar = QtWidgets.QToolBar()
        file_toolbar.setWindowTitle('Files')
        file_toolbar.setObjectName('Files')
        file_toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        file_toolbar.addAction(self.actionregistry.get('OpenVideos'))
        file_toolbar.addAction(self.actionregistry.get('OpenSession'))
        file_toolbar.addAction(self.actionregistry.get('SaveSession'))
        file_toolbar.addAction(self.actionregistry.get('ExportImage'))
        file_toolbar.addAction(self.actionregistry.get('ExportImages'))

        tools_toolbar = QtWidgets.QToolBar()
        tools_toolbar.setWindowTitle('Tools')
        tools_toolbar.setObjectName('Tools')
        tools_toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        tools_toolbar.addActions(
            self.actionregistry.list_category_actions('Tool'))

        zoom_toolbar = QtWidgets.QToolBar()
        zoom_toolbar.setWindowTitle('Zoom')
        zoom_toolbar.setObjectName('Zoom')
        zoom_toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        zoom_toolbar.addWidget(self.canvas.get_zoom_label_widget())

        layerstack_dock = self.get_dock_widget(
            self.layerview, 'Layers', 'Layers')
        shapesettings_dock = self.get_dock_widget(
            self.shapesettings, 'Shape settings', 'Shape settings')
        toolsettings_dock = self.get_dock_widget(
            self.toolsettings, 'Tool settings', 'Tool settings')

        imagesettings = QtWidgets.QWidget()
        imagesettings_layout = QtWidgets.QFormLayout(imagesettings)
        imagesettings_layout.setContentsMargins(0, 0, 0, 0)
        imagesettings_layout.setSpacing(0)
        imagesettings_layout.addRow('Veil', self.veilsettings)
        imagesettings_layout.addRow('Brightness', self.brightness)

        imagesettings_dock = self.get_dock_widget(
            imagesettings, 'Image settings', 'Image settings')

        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, file_toolbar)
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, tools_toolbar)
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, zoom_toolbar)
        self.addDockWidget(Qt.LeftDockWidgetArea, toolsettings_dock)
        self.addDockWidget(Qt.LeftDockWidgetArea, shapesettings_dock)
        self.addDockWidget(Qt.LeftDockWidgetArea, imagesettings_dock)
        self.addDockWidget(Qt.LeftDockWidgetArea, layerstack_dock)

        docks = sorted(
            self.docks,
            key=lambda cls: cls.APPEARANCE_PRIORITY,
            reverse=True)

        for widget in docks:
            dock = QtWidgets.QDockWidget()
            dock.setWindowTitle(widget.TITLE)
            dock.setObjectName(widget.OBJECT_NAME)
            dock.setWidget(widget)
            self.addDockWidget(widget.DOCK_AREA, dock)

        # Layouts
        stack_layout = QtWidgets.QStackedLayout()
        stack_layout.setContentsMargins(0, 0, 0, 0)
        stack_layout.setSpacing(0)
        stack_layout.setStackingMode(QtWidgets.QStackedLayout.StackAll)
        stack_layout.addWidget(self.media_player)
        stack_layout.addWidget(self.canvas)

        self.playback_widget = QtWidgets.QWidget()
        self.playback_widget.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Minimum,
            QtWidgets.QSizePolicy.Policy.Minimum)
        playback_layout = QtWidgets.QHBoxLayout(self.playback_widget)
        playback_layout.setSizeConstraint(
            QtWidgets.QBoxLayout.SizeConstraint.SetMinimumSize)
        playback_layout.setContentsMargins(0, 0, 0, 0)
        playback_layout.setSpacing(0)
        for button in playback_buttons:
            playback_layout.addWidget(button)
        playback_layout.addWidget(self.timeline)
        playback_layout.addWidget(toggle_loop)
        playback_layout.addWidget(self.volume_button)
        playback_layout.addWidget(mute_button)

        widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addLayout(stack_layout, 15)
        layout.addWidget(self.playback_widget, 0)

        self.setCentralWidget(widget)
        self.create_application_menu()
        self.actionregistry.get('Canvas>Navigation').trigger()

    def show_relocator(self):
        self.movie_relocator.show()

    def store_state_as_default(self):
        self.default_state = self.saveState()

    def restore_default_state(self):
        self.restoreState(self.default_state)

    def restore_save_state(self):
        states = self.preferences.get('window_states')
        if not states:
            return
        states = QtCore.QByteArray(base64.b64decode(states))
        self.restoreState(states)
        tools_settings = self.preferences.get('tools_settings', None)
        if tools_settings is not None:
            self.canvas.restore_tools_settings(tools_settings)
            self.toolsettings.deserialize(tools_settings)

        state = self.preferences.get('loopmode', False)
        self.session.playlist.playback_loop = state
        self.actionregistry.get('ToggleLoopMode').setChecked(state)

        state = self.preferences.get('mute', False)
        self.actionregistry.get('ToggleMute').setChecked(state)

        state = self.preferences.get('mute_annotations', False)
        self.session.playlist.mute_annotations = state
        self.canvas.mute = state
        self.actionregistry.get('ToggleMuteAnnotations').setChecked(state)

        QtCore.QTimer.singleShot(1, self.restore_window_geometry)

    def save_states(self):
        switched = False
        if self.zen_mode:
            self.switch_zenmode()
            switched = True
        states = base64.b64encode(bytes(self.saveState())).decode('utf-8')
        self.preferences.set('window_states', states)
        if switched:
            self.switch_zenmode()

    def save_tools_states(self):
        geometry = [
            self.geometry().left(), self.geometry().top(),
            self.geometry().width(), self.geometry().height()]
        self.preferences.set('geometry', geometry)
        self.preferences.set('maximized', self.isMaximized())
        if self.media_player.is_playing:
            self.media_player.blockSignals(True)
            self.media_player.stop()
        self.toolsettings.sync_tools(self.canvas.tools)
        self.preferences.set('tools_settings', self.toolsettings.serialize())

    def restore_window_geometry(self):
        if self.preferences.get('geometry'):
            rect = QtCore.QRect(*self.preferences.get('geometry'))
            self.move(rect.topLeft())
            if not self.preferences.get('maximized'):
                self.setGeometry(rect)
        if self.preferences.get('maximized'):
            self.showMaximized()

    def get_dock_widget(self, widget, window_title, object_name):
        dock = QtWidgets.QDockWidget()
        dock.setWindowTitle(window_title)
        dock.setObjectName(object_name)
        dock.setWidget(widget)
        return dock

    def closeEvent(self, event):
        callback.perform(callback.ON_APPLICATION_EXIT, self.session, self)
        self.save_states()
        super().closeEvent(event)

    def create_application_menu(self):
        file_menu = QtWidgets.QMenu('&File', self)
        file_menu.addAction(self.actionregistry.get('NewSession'))
        file_menu.addAction(self.actionregistry.get('OpenSession'))
        file_menu.addMenu(self.recent_session_menu)
        file_menu.addSeparator()
        file_menu.addAction(self.actionregistry.get('OpenVideos'))
        file_menu.addAction(self.actionregistry.get('ImportPlaylist'))
        file_menu.addAction(self.actionregistry.get('ImportSessionAnnotations'))
        file_menu.addSeparator()
        file_menu.addAction(self.actionregistry.get('SaveSession'))
        file_menu.addAction(self.actionregistry.get('SaveSessionAs'))
        file_menu.addAction(self.actionregistry.get('ExportVideoSessionAs'))
        file_menu.addSeparator()
        file_menu.addAction(self.actionregistry.get('RelocateFileVideos'))
        file_menu.addSeparator()
        file_menu.addAction(self.actionregistry.get('Exit'))

        self.menuBar().addMenu(file_menu)

        edit_menu = QtWidgets.QMenu('Edit', self)
        edit_menu.addAction(self.actionregistry.get('Canvas>Undo'))
        edit_menu.addAction(self.actionregistry.get('Canvas>Redo'))
        edit_menu.addSeparator()
        edit_menu.addAction(self.actionregistry.get('Copy'))
        edit_menu.addAction(self.actionregistry.get('Paste'))
        edit_menu.addAction(self.actionregistry.get('Canvas>Duplicate'))
        edit_menu.addAction(self.actionregistry.get('DeleteCurrentAnnotation'))
        edit_menu.addSeparator()
        edit_menu.addAction(self.actionregistry.get('Canvas>ClearSelection'))
        edit_menu.addSeparator()
        self.menuBar().addMenu(edit_menu)

        playlist_menu = QtWidgets.QMenu('Pla&ylist', self)
        playlist_menu.addAction(self.actionregistry.get('AddVideos'))
        playlist_menu.addAction(self.actionregistry.get('InsertVideos'))
        playlist_menu.addAction(self.actionregistry.get('InsertVideosAfter'))
        playlist_menu.addSeparator()
        playlist_menu.addAction(self.actionregistry.get('RemoveCurrentVideo'))
        self.menuBar().addMenu(playlist_menu)

        export_menu = QtWidgets.QMenu('E&xport')
        export_menu.addAction(self.actionregistry.get('ExportImage'))
        export_menu.addAction(self.actionregistry.get('ExportImages'))
        self.menuBar().addMenu(export_menu)

        zoom_menu = QtWidgets.QMenu('Zoom')
        zoom_menu.addAction(self.actionregistry.get('Zoom1'))
        zoom_menu.addAction(self.actionregistry.get('Zoom2'))
        zoom_menu.addAction(self.actionregistry.get('Zoom3'))
        zoom_menu.addAction(self.actionregistry.get('Zoom4'))

        dock_menu = DocksMenu(self)
        toolbar_menu = ToolbarMenu(self)

        view = QtWidgets.QMenu('&View')
        view.addAction(self.actionregistry.get('ResetCanvas'))
        view.addSeparator()
        view.addAction(self.actionregistry.get('ToggleOnionSkin'))
        view.addSeparator()
        view.addAction(self.actionregistry.get('ZenMode'))
        view.addAction(self.actionregistry.get('FullScreen'))
        view.addAction(self.actionregistry.get('DefaultState'))
        view.addAction(self.actionregistry.get('ToggleMuteAnnotations'))
        view.addSeparator()
        view.addMenu(zoom_menu)
        view.addSeparator()
        view.addMenu(dock_menu)
        view.addMenu(toolbar_menu)
        self.menuBar().addMenu(view)

        tools = QtWidgets.QMenu('&Tools')
        tools.addActions(self.actionregistry.list_category_actions('Tool'))
        self.menuBar().addMenu(tools)

        preferences = QtWidgets.QMenu('&Preferences')
        preferences.addAction(
            self.actionregistry.get('DisplayShortcutManager'))
        preferences.addAction(
            self.actionregistry.get('DisplayPluginManagerWindow'))
        preferences.addAction(
            self.actionregistry.get('DisplayEnvironment'))
        preferences.addSeparator()
        preferences.addAction(
            self.actionregistry.get('ImportPreferences'))
        preferences.addAction(
            self.actionregistry.get('ExportPreferences'))
        self.menuBar().addMenu(preferences)

        help_menu = QtWidgets.QMenu('&Help', self)
        help_menu.addAction(self.actionregistry.get('Documentation'))
        help_menu.addAction(self.actionregistry.get('AboutDreamwall'))
        help_menu.addAction(self.actionregistry.get('AboutTools'))
        help_menu.addAction(self.actionregistry.get('About'))
        self.menuBar().addMenu(help_menu)

    @ebc.catch_error
    def copy(self):
        if QtWidgets.QApplication.clipboard().image():
            QtWidgets.QApplication.clipboard().clear()
        self._clipboard = self.canvas.copy()

    @ebc.catch_error
    def paste(self):
        if not QtWidgets.QApplication.clipboard().image():
            self.canvas.paste(self._clipboard)
            self.actionregistry.get('Canvas>Transform').trigger()
            return
        if not self._clipboard and QtWidgets.QApplication.clipboard().image():
            self.canvas.paste()
            self.actionregistry.get('Canvas>Transform').trigger()
            return
        if not self._clipboard:
            return
        msg = QtWidgets.QMessageBox(self)
        msg.setWindowTitle('Multi-clipboard detected')
        msg.setText(
            'The clipboard contains both image and vector drawing data.')
        msg.setIcon(QtWidgets.QMessageBox.Question)
        msg.setStandardButtons(
            QtWidgets.QMessageBox.Apply |
            QtWidgets.QMessageBox.Yes |
            QtWidgets.QMessageBox.Cancel)
        msg.setDefaultButton(QtWidgets.QMessageBox.Yes)

        msg.button(QtWidgets.QMessageBox.Yes).setText('Image')
        msg.button(QtWidgets.QMessageBox.Apply).setText('Vector drawing')
        msg.button(QtWidgets.QMessageBox.Cancel).setText('Cancel')
        result = msg.exec_()
        if result == QtWidgets.QMessageBox.Cancel:
            return
        if result == QtWidgets.QMessageBox.Yes:
            self.canvas.paste()
        if result == QtWidgets.QMessageBox.No:
            self.canvas.paste(self._clipboard)
        self.actionregistry.get('Canvas>Transform').trigger()

    def show_recent_sessions(self):
        self.recent_session_menu.clear()
        recent_sessions = self.preferences.get('recent_sessions_files', [])
        if not recent_sessions:
            action = QtGui.QAction(self, 'No session history')
            action.setEnabled(False)
            self.recent_session_menu.addAction(action)
            return
        for session_file in recent_sessions:
            action = QtGui.QAction(os.path.basename(session_file), self)
            action.triggered.connect(
                partial(ebc.open_session, session_file))
            self.recent_session_menu.addAction(action)

    def switch_zenmode(self):
        if self.zen_mode is False:
            widget = QtWidgets.QApplication.focusWidget()
            action = self.actionregistry.get('ZenMode')
            # HACK: In case if the shortcut is set on Tab (default value).
            # We only apply the zen mode if the focus is on the Canvas/Timeline
            # Else we have to reimplement the focus next children which is
            # eaten by the QShortcut.
            short_cut_is_tab = (
                action.shortcut().matches(QtGui.QKeySequence(Qt.Key_Tab))
                == QtGui.QKeySequence.ExactMatch)
            if short_cut_is_tab:
                zen_classes = (Canvas, TimeLineWidget, TimelineSlider)
                if not isinstance(widget, zen_classes):
                    self.focusNextChild()
                    return
            self.window_sates = self.saveState()
            for dock in self.findChildren(QtWidgets.QDockWidget):
                dock.setVisible(False)
            for toolbar in self.findChildren(QtWidgets.QToolBar):
                area = self.toolBarArea(toolbar)
                if area != Qt.NoToolBarArea and toolbar.isVisible():
                    toolbar.setVisible(False)
            self.playback_widget.setVisible(False)
            self.menuBar().hide()
            self.zen_mode = True
        else:
            self.playback_widget.show()
            self.menuBar().show()
            self.restoreState(self.window_sates)
            self.window_sates = None
            self.zen_mode = False

    def sizeHint(self):
        return QtCore.QSize(1400, 800)

    def prompt_for_video(self):
        filepaths, _ = QtWidgets.QFileDialog.getOpenFileNames(
            self, 'Open videos', os.path.expanduser('~'),
            filter=' '.join(f'*.{e}' for e in EXTENSIONS))
        if filepaths:
            ebc.new_session()
            ebc.load_videos(filepaths)

    def toggle_fullscreen(self):
        if not self.isFullScreen():
            self.showFullScreen()
        else:
            self.showNormal()

    def drawed(self):
        self.timeline.update()
        self.session.add_annotation_at(
            self.session.playlist.frame, self.canvas.model)
        for dock in self.docks:
            dock.update_view()

    def current_frame_changed(self):
        if self.media_player.is_playing():
            return
        self.session.clear_empty_annotations()
        frame = self.session.playlist.frame
        self.canvas.model = self.session.get_annotation_at(
            frame, self.viewportmapper)
        self.layerview.update()
        self.veilsettings.update()
        if not self.canvas.model.is_null():
            self.canvas.update()
        for dock in self.docks:
            dock.update_view()

    def playing_state_changed(self, state):
        if not state:
            if self.autosave.schedule_auto_save is True:
                self.autosave.auto_save()
            for widget in self.docks + self.toolbars:
                if widget.ENABLE_DURING_PLAYBACK is False:
                    widget.setEnabled(True)
        else:
            self.session.cache_annotations(force=False)
            self.current_frame_changed()
            for widget in self.docks + self.toolbars:
                if widget.ENABLE_DURING_PLAYBACK is False:
                    widget.setEnabled(False)
        self.canvas.mute = (
            state or self.preferences.get('mute_annotations', False))

    def set_pixel_size(self, pixel_size):
        self.viewportmapper.set_viewport_pixel_size(pixel_size)
        self.canvas.panzoom_changed.emit()

    def update_title(self):
        if not self.session.filepath:
            self.setWindowTitle(WINDOW_TITLE)
            return

        self.setWindowTitle(f'{WINDOW_TITLE} - {self.session.filepath}')

    def scrub(self, offset):
        start, end = self.session.playlist.get_playback_range()
        frame = self.session.playlist.frame + offset
        frame = min((end, max((start, frame))))
        ebc.set_frame(frame)

    def show_volume_slider(self):
        self.volume_slider.show()
        pos = self.volume_button.mapToGlobal(QtCore.QPoint(0, 0))
        pos.setY(pos.y() - self.volume_slider.height())
        self.volume_slider.move(pos)

    def set_brightness(self, value):
        self.media_player.brightness = value / 100
        self.media_player.update()

    def show_environment(self):
        env_widget = QtWidgets.QTextEdit()
        t = '\n'.join([f'{k}={v}' for k, v in os.environ.items()])
        env_widget.setText(t)
        env_widget.setReadOnly(True)
        dialog = QtWidgets.QDialog()
        dialog.setWindowTitle('Environment')
        layout = QtWidgets.QVBoxLayout(dialog)
        layout.addWidget(env_widget)
        dialog.exec_()

    def quit(self):
        self.save_tools_states()



class DocksMenu(QtWidgets.QMenu):
    def __init__(self, mainwindow, parent=None):
        super().__init__('Panels', parent)
        self.mainwindow = mainwindow
        self.aboutToShow.connect(self.populate_menu)

    def populate_menu(self):
        self.clear()
        actions = [
            d.toggleViewAction()
            for d in self.mainwindow.findChildren(QtWidgets.QDockWidget)]
        actions.sort(key=lambda a: a.text())
        self.addActions(actions)


class ToolbarMenu(QtWidgets.QMenu):
    def __init__(self, mainwindow, parent=None):
        super().__init__('Toolbars', parent)
        self.mainwindow = mainwindow
        self.aboutToShow.connect(self.populate_menu)

    def populate_menu(self):
        self.clear()
        actions = [
            d.toggleViewAction()
            for d in self.mainwindow.findChildren(QtWidgets.QToolBar)
            if d.parent() == self.mainwindow]
        actions.sort(key=lambda a: a.text())
        self.addActions(actions)


class VolumeSlider(QtWidgets.QWidget):
    def __init__(self, parent=None):
        flags = QtCore.Qt.WindowType.Popup | QtCore.Qt.FramelessWindowHint | QtCore.Qt.Window
        super().__init__(parent, flags)
        self.slider = QtWidgets.QSlider()
        self.slider.setMinimum(0)
        self.slider.setMaximum(100)
        self.slider.setValue(100)
        self.slider.valueChanged.connect(ebc.set_volume)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.slider)