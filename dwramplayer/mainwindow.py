import os
import sys
import json
import msgpack
from functools import partial

from PySide6 import QtWidgets, QtGui, QtCore
from PySide6.QtCore import Qt

from viewportmapper import NDCViewportMapper
from paintcanvas.canvas import Canvas, CanvasModel

from dwramplayer.icons import get_icon
from dwramplayer.player import MediaPlayer
from dwramplayer.plugin import DwRamPlayerDockWidget
from dwramplayer.playlist import Playlist
from dwramplayer.timeline import TimeLineWidget
from dwramplayer.playlist import EXTENSIONS
from dwramplayer.session import Session


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, plugin_classes: list[DwRamPlayerDockWidget]|None=None):
        super().__init__()
        self.setWindowTitle('DW RamPlayer')
        self._actions = dict()
        self.zen_mode = False
        self.window_sates = None

        playlist = Playlist()
        self.session = Session(playlist)
        self.viewportmapper = NDCViewportMapper()

        self.media_player = MediaPlayer(self.viewportmapper, playlist)
        self.media_player.current_frame_changed.connect(
            self.current_frame_changed)
        self.media_player.playing_state_changed.connect(
            self.playing_state_changed)

        self.canvas_model = CanvasModel(viewportmapper=self.viewportmapper)

        self.canvas = Canvas(self.canvas_model)
        self.canvas.panzoom_changed.connect(self.media_player.update)
        self.canvas.size_changed.connect(self.media_player.update)
        self.canvas.updated.connect(self.drawed)

        self.layerview = self.canvas.get_layer_view()
        self.layerview.edited.connect(self.update)

        self.shapesettings = self.canvas.get_shape_settings_widget()
        self.toolsettings = self.canvas.get_tool_settings_widget()
        self.washsettings = self.canvas.get_wash_settings_widget()

        self.timeline = TimeLineWidget(self.session)
        self.timeline.current_frame_changed.connect(
            self.current_frame_changed)
        self.timeline.current_frame_changed.connect(
            self.media_player.play_current_frame)
        self.timeline.current_frame_changed.connect(
            self.media_player.play_audio_frame)
        self.media_player.current_frame_changed.connect(
            self.timeline.update_values)

        self._actions.update(self.get_actions())
        self._actions.update(self.canvas.all_actions)

        self.plugin_docks = []
        for cls in plugin_classes:
            widget = cls(self.session)
            self.plugin_docks.append(widget)
            self._actions.update(widget.get_actions())

        previous_button = QtWidgets.QToolButton()
        previous_button.setDefaultAction(self._actions['PrevFrame'])
        play_button = QtWidgets.QToolButton()
        play_button.setDefaultAction(self._actions['PlayPause'])
        next_button = QtWidgets.QToolButton()
        next_button.setDefaultAction(self._actions['NextFrame'])
        toggle_loop = QtWidgets.QToolButton()
        toggle_loop.setDefaultAction(self._actions['ToggleLoopMode'])

        # Toobars and docks
        file_toolbar = QtWidgets.QToolBar()
        file_toolbar.setWindowTitle('Files')
        file_toolbar.setObjectName('Files')
        file_toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        file_toolbar.addAction(self._actions['OpenVideos'])
        file_toolbar.addAction(self._actions['OpenSession'])
        file_toolbar.addAction(self._actions['SaveSessionAs'])
        file_toolbar.addAction(self._actions['ExportImage'])
        file_toolbar.addAction(self._actions['ExportImages'])

        tools_toolbar = QtWidgets.QToolBar()
        tools_toolbar.setWindowTitle('Tools')
        tools_toolbar.setObjectName('Tools')
        tools_toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        tools_toolbar.addActions(list(self.canvas.tool_actions.values()))

        info_toolbar = QtWidgets.QToolBar()
        info_toolbar.setWindowTitle('Infos')
        info_toolbar.setObjectName('Infos')
        info_toolbar.addWidget(self.canvas.get_zoom_label_widget())
        info_toolbar.addAction(self._actions['Help'])

        layerstack_dock = QtWidgets.QDockWidget()
        layerstack_dock.setWindowTitle('Layers')
        layerstack_dock.setObjectName('Layers')
        layerstack_dock.setWidget(self.layerview)

        shapesettings_dock = QtWidgets.QDockWidget()
        shapesettings_dock.setWindowTitle('Shape settings')
        shapesettings_dock.setObjectName('Shape settings')
        shapesettings_dock.setWidget(self.shapesettings)

        toolsettings_dock = QtWidgets.QDockWidget()
        toolsettings_dock.setWindowTitle('Tool settings')
        toolsettings_dock.setObjectName('Tool settings')
        toolsettings_dock.setWidget(self.toolsettings)

        washsettings_dock = QtWidgets.QDockWidget()
        washsettings_dock.setWindowTitle('Wash settings')
        washsettings_dock.setObjectName('Wash settings')
        washsettings_dock.setWidget(self.washsettings)

        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, file_toolbar)
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, tools_toolbar)
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, info_toolbar)
        self.addDockWidget(Qt.LeftDockWidgetArea, toolsettings_dock)
        self.addDockWidget(Qt.LeftDockWidgetArea, shapesettings_dock)
        self.addDockWidget(Qt.LeftDockWidgetArea, washsettings_dock)
        self.addDockWidget(Qt.LeftDockWidgetArea, layerstack_dock)

        for widget in self.plugin_docks:
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
        playback_layout.addWidget(previous_button)
        playback_layout.addWidget(play_button)
        playback_layout.addWidget(next_button)
        playback_layout.addWidget(self.timeline)
        playback_layout.addWidget(toggle_loop)

        widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addLayout(stack_layout, 15)
        layout.addWidget(self.playback_widget, 0)

        self.addActions(list(self._actions.values()))
        self.register_shortcuts()

        self.setCentralWidget(widget)

    def switch_zenmode(self):
        if self.zen_mode is False:
            self.window_sates = self.saveState()
            for dock in self.findChildren(QtWidgets.QDockWidget):
                dock.setVisible(False)
            for toolbar in self.findChildren(QtWidgets.QToolBar):
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

    def load_videos(self, video_paths, container_ids=None):
        self.media_player.load_videos(video_paths, container_ids)
        self.session.playback_start = None
        self.session.playback_end = None
        self.timeline.update_values()

    def register_shortcuts(self):
        actions = self._actions
        actions['Canvas>Undo'].setShortcut('CTRL+Z')
        actions['Canvas>Redo'].setShortcut('CTRL+Y')
        actions['Canvas>DeleteSelection'].setShortcut('DEL')
        # actions['Canvas>Navigation'].setShortcut('')
        actions['Canvas>Move'].setShortcut('Z')
        actions['Canvas>Transform'].setShortcut('CTRL+T')
        actions['Canvas>Selection'].setShortcut('S')
        actions['Canvas>Draw'].setShortcut('B')
        actions['Canvas>Smooth Draw'].setShortcut('N')
        actions['Canvas>Eraser'].setShortcut('E')
        actions['Canvas>Line'].setShortcut('L')
        actions['Canvas>Rectangle'].setShortcut('R')
        actions['Canvas>Circle'].setShortcut('C')
        actions['Canvas>Arrow'].setShortcut('A')
        actions['Canvas>Text'].setShortcut('T')
        actions['Help'].setShortcut(QtGui.QKeySequence(Qt.Key.Key_H))
        actions['FullScreen'].setShortcut(QtGui.QKeySequence(Qt.Key.Key_F11))
        sequence = QtGui.QKeySequence(Qt.CTRL | Qt.Key_Right)
        actions['NextAnnotation'].setShortcut(sequence)
        actions['NextFrame'].setShortcut(QtGui.QKeySequence(Qt.Key_Right))
        sequence = QtGui.QKeySequence(Qt.SHIFT | Qt.Key_Right)
        actions['NextVideo'].setShortcut(sequence)
        actions['PrevAnnotation'].setShortcut(
            QtGui.QKeySequence(Qt.CTRL | Qt.Key_Left))
        actions['PrevFrame'].setShortcut(QtGui.QKeySequence(Qt.Key_Left))
        sequence = QtGui.QKeySequence(Qt.SHIFT | Qt.Key_Left)
        actions['PrevVideo'].setShortcut(sequence)
        actions['ResetCanvas'].setShortcut(QtGui.QKeySequence(Qt.Key_F))
        actions['SetPlaybackStart'].setShortcut(QtGui.QKeySequence(Qt.Key.Key_I))
        actions['SetPlaybackEnd'].setShortcut(QtGui.QKeySequence(Qt.Key.Key_O))
        actions['ToggleLoopMode'].setShortcut(QtGui.QKeySequence(Qt.Key.Key_L))
        actions['ZenMode'].setShortcut(QtGui.QKeySequence(Qt.Key.Key_Tab))
        actions['Zoom1'].setShortcut(QtGui.QKeySequence(Qt.Key.Key_1))
        actions['Zoom2'].setShortcut(QtGui.QKeySequence(Qt.Key.Key_2))
        actions['Zoom3'].setShortcut(QtGui.QKeySequence(Qt.Key.Key_3))
        actions['Zoom4'].setShortcut(QtGui.QKeySequence(Qt.Key.Key_4))

    def get_actions(self):
        actions = {
            'ExportCurrentFrame': QtGui.QAction('Export current frame', self),
            'ExportImage': QtGui.QAction(
                get_icon('export_image.png'),
                'Export current annotation', self),
            'ExportImages': QtGui.QAction(
                get_icon('export_images.png'), 'Export annotations', self),
            'FullScreen': QtGui.QAction('Toggle full screen', self),
            'Help': QtGui.QAction(get_icon('help.png'), 'Help', self),
            'OpenVideos': QtGui.QAction(
                get_icon('open_videos.png'), 'Open videos', self),
            'OpenSession': QtGui.QAction(
                get_icon('open_session.png'), 'Open session', self),
            'NextAnnotation': QtGui.QAction('Next annotation', self),
            'NextFrame': QtGui.QAction(
                get_icon('next_frame.svg'),
                'Next frame', self),
            'NextVideo': QtGui.QAction('Next video', self),
            'PrevAnnotation': QtGui.QAction('Previous annotation', self),
            'PrevFrame': QtGui.QAction(
                get_icon('previous_frame.svg'),
                'Previous frame', self),
            'PrevVideo': QtGui.QAction('Previous video', self),
            'PlayPause': QtGui.QAction(
                get_icon('play_pause.svg'),
                'Play/Pause', self),
            'ResetCanvas': QtGui.QAction('Reset canvas zoom', self),
            'SaveSessionAs': QtGui.QAction(
                get_icon('save.png'),
                'Save session as', self),
            'SetPlaybackStart': QtGui.QAction('Set playback start', self),
            'SetPlaybackEnd': QtGui.QAction('Set playback end', self),
            'ToggleLoopMode': QtGui.QAction(
                get_icon('loop.png'),
                'Loop On/Off', self),
            'ZenMode': QtGui.QAction('Toggle zen mode', self),
            'Zoom1': QtGui.QAction('Zoom to 100%', self),
            'Zoom2': QtGui.QAction('Zoom to 150%', self),
            'Zoom3': QtGui.QAction('Zoom to 200%', self),
            'Zoom4': QtGui.QAction('Zoom to 300%', self),
        }

        actions['ExportImage'].triggered.connect(self.export_current_frame)
        actions['ExportImages'].triggered.connect(self.export_annoted_frames)
        actions['Help'].triggered.connect(self.show_help)
        actions['FullScreen'].triggered.connect(self.toggle_fullscreen)
        actions['OpenVideos'].triggered.connect(self.prompt_for_video)
        actions['OpenSession'].triggered.connect(self.open_session)
        actions['NextAnnotation'].triggered.connect(self.set_next_annotation)
        actions['NextFrame'].triggered.connect(self.media_player.next_frame)
        actions['NextVideo'].triggered.connect(self.set_next_video)
        actions['PrevAnnotation'].triggered.connect(
            self.set_previous_annotation)
        actions['PrevFrame'].triggered.connect(
            self.media_player.previous_frame)
        actions['PrevVideo'].triggered.connect(self.set_previous_video)
        actions['PlayPause'].triggered.connect(self.media_player.play_pause)
        actions['PlayPause'].setShortcut(QtGui.QKeySequence(Qt.Key_Space))
        actions['ResetCanvas'].triggered.connect(self.reset_canvas)
        actions['SaveSessionAs'].triggered.connect(self.save_as)
        actions['SetPlaybackStart'].triggered.connect(self.set_playback_start)
        actions['SetPlaybackEnd'].triggered.connect(self.set_playback_end)
        actions['ToggleLoopMode'].setCheckable(True)
        actions['ToggleLoopMode'].setChecked(True)
        actions['ToggleLoopMode'].toggled.connect(self.toggle_loop_mode)
        actions['ZenMode'].triggered.connect(self.switch_zenmode)
        actions['Zoom1'].triggered.connect(partial(self.set_pixel_size, 1))
        actions['Zoom2'].triggered.connect(partial(self.set_pixel_size, 1.5))
        actions['Zoom3'].triggered.connect(partial(self.set_pixel_size, 2))
        actions['Zoom4'].triggered.connect(partial(self.set_pixel_size, 3))
        return actions

    def set_next_annotation(self):
        annotated_frames = self.session.get_annotated_frames()
        self._set_next_marked_frames(annotated_frames)

    def set_previous_annotation(self):
        annotated_frames = self.session.get_annotated_frames()
        self._set_previous_marked_frames(annotated_frames)

    def set_next_video(self):
        first_frames = self.session.playlist.first_frames.values()
        self._set_next_marked_frames(list(first_frames))

    def set_previous_video(self):
        first_frames = self.session.playlist.first_frames.values()
        self._set_previous_marked_frames(list(first_frames))

    def _set_next_marked_frames(self, marked_frames):
        if not marked_frames:
            return
        frame = min((
            f for f in marked_frames if
            f > self.session.playlist.frame),
            default=marked_frames[0])
        self.media_player.set_frame(frame)

    def _set_previous_marked_frames(self, marked_frames):
        if not marked_frames:
            return
        frame = max((
            f for f in marked_frames if
            f < self.session.playlist.frame),
            default=marked_frames[-1])
        self.media_player.set_frame(frame)

    def set_playback_start(self):
        frame = self.session.playlist.frame
        _, end = self.session.playlist.get_playback_range()
        self.session.playlist.playback_start = frame
        self.session.playlist.playback_end = max((end, frame))
        self.timeline.update_values()

    def set_playback_end(self):
        frame = self.session.playlist.frame
        self.session.playlist.playback_end = frame
        start, _ = self.session.playlist.get_playback_range()
        self.session.playlist.playback_start = min((start, frame))
        self.timeline.update_values()

    def toggle_loop_mode(self, state):
        self.session.playlist.playback_loop = state

    def prompt_for_video(self):
        filepaths, _ = QtWidgets.QFileDialog.getOpenFileNames(
            self, 'Open videos', os.path.expanduser('~'),
            filter=' '.join(f'*.{e}' for e in EXTENSIONS))
        if filepaths:
            self.load_videos(filepaths)

    def save_as(self):
        filepath, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, 'Save session', os.path.expanduser('~'), filter='*.dwr')
        if not filepath:
            return
        with open(filepath, 'w') as f:
            json.dump(self.canvas.model.serialize(), f, indent=1)

    def open_session(self):
        filepath, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, 'Open session', os.path.expanduser('~'), filter='*.dws')
        if not filepath:
            return
        with open(filepath, 'rb') as f:
            data = msgpack.load(f)

        video_paths = [elt[-1] for elt in data['containers']]
        container_ids = [elt[0] for elt in data['containers']]
        self.load_videos(video_paths=video_paths, container_ids=container_ids)

        self.session.annotations.clear()
        for id_, frame, annotation_data in data['annotations']:
            model = CanvasModel(viewportmapper=self.viewportmapper)
            model.deserialize(annotation_data)
            self.session.annotations[(id_, frame)] = model
        self._actions['ResetCanvas'].trigger()
        self.update()

    def reset_canvas(self):
        self.viewportmapper.zoom = 1.0
        self.viewportmapper.origin = QtCore.QPointF(0, 0)
        self.canvas.panzoom_changed.emit()

    def set_pixel_size(self, pixel_size):
        self.viewportmapper.set_pixel_size(pixel_size)
        self.canvas.panzoom_changed.emit()

    def toggle_fullscreen(self):
        if not self.isFullScreen():
            self.showFullScreen()
        else:
            self.showNormal()

    def drawed(self):
        # Remove annotation if blank
        if not self.canvas.model.is_null():
            self.delete_annotation_at(self.session.playlist.frame)
            self.timeline.update()
            return
        self.timeline.update()
        self.session.add_annotation_at(
            self.session.playlist.frame, self.canvas.model)

    def current_frame_changed(self):
        if self.media_player.is_playing():
            return
        frame = self.session.playlist.frame
        self.canvas.model = self.session.get_annotation_at(
            frame, self.viewportmapper)
        self.layerview.update()
        self.washsettings.update()
        if not self.canvas.model.is_null():
            self.canvas.update()
        for dock in self.plugin_docks:
            dock.update_current_frame()

    def export_current_frame(self):
        filepath, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, 'Export Annotation', filter='Png *.png')
        if not filepath:
            return
        if os.path.exists(filepath):
            reply = QtWidgets.QMessageBox.question(
                self, 'File already exists',
                f'File already exists: \n{filepath}\n\n'
                'Would you like to erase it ?')
            if reply == QtWidgets.QMessageBox.No:
                return

        frame = self.session.playlist.frame
        image = self.session.render_frame(frame).toImage()
        image.save(filepath, 'png')

    def export_annoted_frames(self):
        directory = QtWidgets.QFileDialog.getExistingDirectory(
            self, 'Select export frames directory')
        if not directory:
            return
        for container_id, rel_frame in self.session.annotations:
            f = self.session.playlist.first_frames[container_id] + rel_frame
            container = self.session.playlist.frames_containers[f]
            fp = f'{directory}/{os.path.basename(container.path)}-{f:04d}.png'
            image = self.session.render_frame(f).toImage()
            image.save(fp, 'png')

    def playing_state_changed(self, state):
        import time
        t = time.time()
        if state:
            self.session.cache_annotations()
        print("Bake done in: ", time.time() - t)
        self.canvas.mute = state

    def save_as(self):
        filepath, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, 'Save session', filter='Review Session *.dws')
        if not filepath:
            return
        if os.path.exists(filepath):
            reply = QtWidgets.QMessageBox.question(
                self, 'File already exists',
                f'File already exists: \n{filepath}\n\n'
                'Would you like to erase it ?')
            if reply == QtWidgets.QMessageBox.No:
                return
        data = self.session.serialize()
        with open(filepath, 'wb') as f:
            msgpack.dump(data, f)

    def show_help(self):
        message = ''
        for action in sorted(self._actions.values(), key=lambda a: a.text()):
            seq = action.shortcut().toString()
            text = f'{action.text()} -> {seq or "..."}\n'
            message += text
        QtWidgets.QMessageBox.information(self, 'Help', message)

