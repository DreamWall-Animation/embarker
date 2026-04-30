import os
import yaml
import msgpack
import platform
import datetime
import traceback
from functools import lru_cache

from PySide6 import QtCore, QtGui, QtWidgets
from paintcanvas import CanvasModel

from embarker import callback
from embarker import preferences
from embarker.msgbox import ScrollMessageBox
from embarker.session import Session
from embarker.playlist import Playlist


def catch_error(func):
    def wrap(*args, **kwargs):
        try:
            r = func(*args, **kwargs)
        except BaseException:
            if not os.getenv('EMBARKER_DEBUG'):
                message = f'[ERROR OCCURED]: \n\n {traceback.format_exc()}'
                ScrollMessageBox(message, 'Error').exec_()
            raise
        return r
    return wrap


def log_debug_command(func):
    def wrap(*args, **kwargs):
        if os.getenv('EMBARKER_COMMANDS_VERBOSITY'):
            now = datetime.datetime.now()
            f = f'{func.__name__}({args}, {kwargs})'
            print(f'[COMMAND]: {now:%H:%M:%S} -> {f}')
        return func(*args, **kwargs)
    return wrap


@lru_cache()
def get_main_window():
    for widget in QtWidgets.QApplication.instance().topLevelWidgets():
        if not isinstance(widget, QtWidgets.QMainWindow):
            continue
        if widget.objectName() == 'EMBARKER-MAIN-WINDOW':
            return widget


def busy_cursor(func):
    def wrap(*args, **kwargs):
        QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.BusyCursor)
        try:
            r = func(*args, **kwargs)
        finally:
            QtWidgets.QApplication.restoreOverrideCursor()
        return r
    return wrap


@catch_error
def get_session() -> Session:
    w = get_main_window()
    if w:
        return w.session


@catch_error
def get_action(action_id):
    return get_main_window().actionregistry.get(action_id)


@catch_error
@log_debug_command
def new_session():
    """
    Reset application state and start a clean new session.
    """
    callback.perform(callback.BEFORE_NEW_SESSION)
    get_session().filepath = None
    get_session().annotations.clear()
    get_session().metadata.clear()
    get_session().playlist.clear()
    get_main_window().update_title()
    get_main_window().current_frame_changed()
    get_main_window().autosave.restart_timer()
    set_frame(0)
    callback.perform(callback.AFTER_NEW_SESSION)


@catch_error
@log_debug_command
def open_session_data(data):
    """
    Open a session from data
    """
    callback.perform(callback.BEFORE_OPEN_SESSION, data)

    new_session()
    video_paths = [elt[1] for elt in data['containers']]
    if not all(os.path.exists(os.path.expandvars(p)) for p in video_paths):
        raise FileNotFoundError('Some video does not exists')
    container_ids = [elt[0] for elt in data['containers']]
    metadatas = [elt[2] for elt in data['containers']]
    load_videos(
        video_paths=video_paths,
        metadatas=metadatas,
        container_ids=container_ids)
    get_session().annotations.clear()
    for id_, frame, annotation_data in data['annotations']:
        model = CanvasModel(viewportmapper=get_main_window().viewportmapper)
        model.deserialize(annotation_data)
        get_session().annotations[(id_, frame)] = model

    set_frame(0)
    get_session().metadata = data.get('metadata', {})
    get_main_window().canvas.reset()
    get_main_window().drawed()
    get_main_window().autosave.restart_timer()

    callback.perform(callback.AFTER_OPEN_SESSION)


@catch_error
@log_debug_command
def open_session(filepath=None, as_new_file=False):
    """
    Open a session file ".embk"
    filepath: str | None
        File to open, if None, the application launch a selection file
        dialog.
    """
    if filepath is None:
        directory = preferences.get(
            'last_session_directory',
            os.path.expanduser('~'))
        filepath, _ = QtWidgets.QFileDialog.getOpenFileName(
            get_main_window(),
            'Open session',
            directory,
            filter='*.embk')
        if filepath:
            preferences.set(
                'last_session_directory',
                os.path.dirname(filepath))
    if not filepath:
        return
    with open(filepath, 'rb') as f:
        data = msgpack.load(f)

    new_session()
    callback.perform(
        event=callback.BEFORE_OPEN_SESSION,
        plugin_id=None,
        session_data=data)

    session_folder = os.path.dirname(filepath)
    video_paths = [elt[1] for elt in data['containers']]
    video_paths = _check_session_videos_paths(video_paths, session_folder)
    container_ids = [elt[0] for elt in data['containers']]
    metadatas = [elt[2] for elt in data['containers']]
    load_videos(
        video_paths=video_paths,
        metadatas=metadatas,
        container_ids=container_ids)
    get_session().annotations.clear()
    for id_, frame, annotation_data in data['annotations']:
        model = CanvasModel(viewportmapper=get_main_window().viewportmapper)
        model.deserialize(annotation_data)
        get_session().annotations[(id_, frame)] = model
    get_session().cache_annotations(force=True)

    set_frame(0)
    if not as_new_file:
        get_session().filepath = filepath
    get_session().metadata = data.get('metadata', {})
    get_main_window().update_title()
    get_main_window().canvas.reset()
    get_main_window().drawed()
    get_main_window().autosave.restart_timer()
    set_recent_session_file(filepath)

    callback.perform(callback.AFTER_OPEN_SESSION)


@catch_error
def import_session_annotations_prompt():
    """
    Import only the annotations of the first session container
    """
    directory = preferences.get(
        'last_session_directory',
        os.path.expanduser('~'))
    filepath, _ = QtWidgets.QFileDialog.getOpenFileName(
        get_main_window(),
        'Import session annotation',
        directory,
        filter='*.embk')
    if not filepath:
        return
    with open(filepath, 'rb') as f:
        data = msgpack.load(f)
    data_containers_paths = {
        id_: os.path.expandvars(p).replace('\\', '/')
        for id_, p, _ in data['containers']}
    session_paths_containers = {
        os.path.expandvars(c.path).replace('\\', '/'): c for
        c in get_session().playlist.containers}
    for data_container_id, frame, annotation_data in data['annotations']:
        data_container_path = data_containers_paths[data_container_id]
        session_container = session_paths_containers.get(data_container_path)
        if session_container is None:
            continue
        if (session_container.id, frame) is get_session().annotations:
            continue
        model = CanvasModel(viewportmapper=get_main_window().viewportmapper)
        model.deserialize(annotation_data)
        if model.is_null():
            continue
        get_session().annotations[(session_container.id, frame)] = model
    get_main_window().timeline.update()


@catch_error
@log_debug_command
def import_session_annotations(filepath=None, container_id=None):
    """
    Import only the annotations of the first session container
    """
    container_id = container_id or get_session().get_current_container().id
    container = get_session().get_container(container_id)

    with open(filepath, 'rb') as f:
        data = msgpack.load(f)

    first_id = None
    for id_, frame, annotation_data in data['annotations']:
        if first_id is None:
            first_id = id_
        if id_ != first_id or frame > container.length + 1:
            continue
        if (container_id, frame) in get_session().annotations:
            continue
        model = CanvasModel(viewportmapper=get_main_window().viewportmapper)
        model.deserialize(annotation_data)
        if model.is_null():
            continue
        get_session().annotations[(container_id, frame)] = model
    get_main_window().timeline.update()


@catch_error
@log_debug_command
def export_preferences():
    filepath, _ = QtWidgets.QFileDialog.getSaveFileName(
        get_main_window(), 'Export preferences',
        filter='Embarker Preferences *.yaml')
    if not filepath:
        return
    get_main_window().save_states()
    get_main_window().save_tools_states()
    preferences.export(filepath)


@catch_error
@log_debug_command
def import_preferences():
    filepath, _ = QtWidgets.QFileDialog.getOpenFileName(
        get_main_window(), 'Import preferences',
        os.path.expanduser('~'), filter='Embarker Preferences *.yaml')
    if not filepath:
        return
    geometry = get_main_window().geometry()
    preferences.import_preferences(filepath)
    get_main_window().restore_save_state()
    get_main_window().actionregistry.register_shortcuts()
    QtCore.QTimer.singleShot(
        1, lambda: get_main_window().setGeometry(geometry))


@catch_error
@busy_cursor
@log_debug_command
def load_videos(
        video_paths: list[str],
        container_ids: list[str] | None = None,
        metadatas: list[dict] | None = None,
        index=-1):
    """
    Add video to current session.
    video_paths: list[str]
        list of file path to open
    metadatas: list[dict] | None = None
        List of dict associated to videos. Those are dynamically added to
        meta data. This allow to handle custom pipeline data which can be
        used to write plugins.
        For instance, that can be handy to associate a video to a
        Shotgrid id.
    index: int
        Video insertion index in the timeline.
        -1 is used to add videos at the end.
    metadatas

    """
    if get_main_window().media_player.is_playing():
        get_main_window().media_player.pause()
    metadatas = metadatas or [{} for _ in range(len(video_paths))]
    container_ids = container_ids or [None for _ in range(len(video_paths))]
    iterator = zip(video_paths, container_ids, metadatas)
    for video_path, container_id, metadata in iterator:
        get_session().playlist.add_video(
            video_path=video_path,
            container_id=container_id,
            metadata=metadata,
            index=index,
            build=False)
    get_session().playlist.build_playlist()
    set_frame(get_session().playlist.frame)
    set_playback_start(0)
    set_playback_end(get_session().playlist.frames_count - 1)
    get_main_window().timeline.update_values()


@catch_error
def is_playing():
    return get_main_window().media_player.is_playing()


@catch_error
@log_debug_command
def replace_videos(video_path, container_id, metadata=None):
    playing = get_main_window().media_player.is_playing()
    if playing:
        get_main_window().media_player.pause()
    get_session().playlist.replace_video(
        video_path=video_path,
        container_id=container_id,
        metadata=metadata,
        keep_id=True)
    set_frame(get_session().playlist.frame)
    if playing:
        get_main_window().media_player.play()


@catch_error
def prompt_load_videos(insert=False, after=False):
    filepaths, _ = QtWidgets.QFileDialog.getOpenFileNames(
        get_main_window(), 'Add Open videos',
        filter='Videos (*.mov *.mp4 *.mkv)')
    if not filepaths:
        return
    index = get_session().playlist.get_container_index() if insert else -1
    if after and index != -1:
        index += 1
    load_videos(filepaths, index=index)


@catch_error
@log_debug_command
def set_playback_start(frame=None):
    frame = frame if frame is not None else get_session().playlist.frame
    _, end = get_session().playlist.get_playback_range()
    get_session().playlist.playback_start = frame
    get_session().playlist.playback_end = max((end, frame))
    get_main_window().timeline.update_values()


@catch_error
@log_debug_command
def set_playback_range(start, end):
    if end <= start:
        raise ValueError('Start must be smaller than end: ', start, end)
    get_session().playlist.playback_start = start
    get_session().playlist.playback_end = end
    get_main_window().timeline.update_values()


@catch_error
@log_debug_command
def delete_annotation(frame=None):
    frame = frame if frame is not None else get_session().playlist.frame
    get_session().delete_annotation_at(frame)
    set_frame(frame)


@catch_error
@log_debug_command
def set_playback_end(frame=None):
    frame = frame if frame is not None else get_session().playlist.frame
    get_session().playlist.playback_end = frame
    start, _ = get_session().playlist.get_playback_range()
    get_session().playlist.playback_start = min((start, frame))
    get_session().playlist.playback_end = frame
    get_main_window().timeline.update_values()


@catch_error
@log_debug_command
def set_next_annotation():
    annotated_frames = get_session().get_annotated_frames()
    _set_next_marked_frames(annotated_frames)


@catch_error
@log_debug_command
def set_previous_annotation():
    annotated_frames = get_session().get_annotated_frames()
    _set_previous_marked_frames(annotated_frames)


@catch_error
@log_debug_command
def set_next_video():
    first_frames = get_session().playlist.first_frames.values()
    _set_next_marked_frames(list(first_frames))


@catch_error
@log_debug_command
def set_previous_video():
    first_frames = get_session().playlist.first_frames.values()
    _set_previous_marked_frames(list(first_frames))


def _set_next_marked_frames(marked_frames):
    if not marked_frames:
        return
    frame = min((
        f for f in marked_frames if
        f > get_session().playlist.frame),
        default=marked_frames[0])
    get_main_window().media_player.set_frame(frame)

def _set_previous_marked_frames(marked_frames):
    if not marked_frames:
        return
    frame = max((
        f for f in marked_frames if
        f < get_session().playlist.frame),
        default=marked_frames[-1])
    get_main_window().media_player.set_frame(frame)


@log_debug_command
def play_pause():
    # update onion skin cache
    current_annotation = get_session().get_current_annotation()
    if current_annotation is not None and not current_annotation.is_null():
        f = get_session().playlist.frame
        image_cache = get_session().render_frame(f, background=False)
        current_annotation.image_cache = image_cache
    get_main_window().media_player.play_pause()


@catch_error
@log_debug_command
def create_new_annotation_model():
    return CanvasModel(get_main_window().viewportmapper)


@catch_error
@log_debug_command
def reset_canvas():
    get_main_window().viewportmapper.zoom = 1.0
    get_main_window().viewportmapper.origin = QtCore.QPointF(0, 0)
    get_main_window().canvas.panzoom_changed.emit()


@catch_error
@log_debug_command
def get_frame():
    return get_session().playlist.frame


@catch_error
@log_debug_command
def set_frame(frame: int):
    current_annotation = get_session().get_current_annotation()

    # Update annotation image cache.
    if current_annotation is not None and not current_annotation.is_null():
        f = get_session().playlist.frame
        image_cache = get_session().render_frame(f, background=False)
        current_annotation.image_cache = image_cache

    _update_onionskin(frame)

    state = get_main_window().media_player.is_playing()
    if state:
        get_main_window().media_player.pause()
    get_main_window().media_player.set_frame(frame)
    if not state:
        get_main_window().media_player.play_audio_frame()
    if state:
        get_main_window().media_player.play()


@log_debug_command
def next_frame():
    if get_main_window().media_player.is_playing():
        get_main_window().media_player.pause()
    next_frame = get_session().playlist.frame + 1
    start, end = get_session().playlist.get_playback_range()
    if end < next_frame:
        next_frame = start
    set_frame(next_frame)


@log_debug_command
def previous_frame():
    if get_main_window().media_player.is_playing():
        get_main_window().media_player.pause()
    previous_frame = get_session().playlist.frame - 1
    start, end = get_session().playlist.get_playback_range()
    if previous_frame < start:
        previous_frame = end
    set_frame(previous_frame)


@catch_error
@log_debug_command
def render_frame(frame: int) -> QtGui.QImage:
    return get_session().render_frame(frame).toImage()


@catch_error
@log_debug_command
def export_annotated_frames(directory: str | None = None):
    if not directory:
        directory = QtWidgets.QFileDialog.getExistingDirectory(
            get_main_window(), 'Select export frames directory')
    if not directory:
        return
    for container_id, rel_frame in get_session().annotations:
        f = get_session().playlist.first_frames[container_id] + rel_frame
        container = get_session().playlist.frames_containers[f]
        fp = f'{directory}/{os.path.basename(container.path)}-{f:04d}.png'
        image = render_frame(f)
        image.save(fp, 'png')
    if platform.system() == 'Windows':
        os.startfile(directory)


@catch_error
@log_debug_command
def remove_current_video():
    container = get_session().get_current_container()
    frame = get_session().playlist.first_frames[container.id]
    frame = max((frame - 1, 0))
    get_session().playlist.remove_video()
    set_frame(frame)


@catch_error
@log_debug_command
def export_current_frame(filepath=None):
    if filepath is None:
        filepath, _ = QtWidgets.QFileDialog.getSaveFileName(
            get_main_window(), 'Export Annotation',
            filter='Png *.png')
    if not filepath:
        return
    frame = get_session().playlist.frame
    image = get_session().render_frame(frame).toImage()
    image.save(filepath, 'png')


@catch_error
@log_debug_command
def load_playlist(filepath=None):
    if filepath is None:
        filepath, _ = QtWidgets.QFileDialog.getOpenFileName(
            get_main_window(), 'Import Playlist',
            filter='Embarker Playlist *.playlist')
    if not filepath:
        return
    with open(filepath, 'r') as f:
        data = yaml.safe_load(f)
    filepaths = [e[0] for e in data]
    metadatas = [e[1] for e in data]
    get_session().filepath = None
    load_videos(video_paths=filepaths, metadatas=metadatas)
    get_main_window().update_title()


@catch_error
@log_debug_command
def save():
    if get_session().filepath is None:
        return save_as()
    data = get_session().serialize()
    with open(get_session().filepath, 'wb') as f:
        msgpack.dump(data, f)
    get_main_window().autosave.restart_timer()


@catch_error
@log_debug_command
def save_as(data=None):
    directory = preferences.get(
        'last_session_directory',
        os.path.expanduser('~'))
    filepath, _ = QtWidgets.QFileDialog.getSaveFileName(
        get_main_window(), 'Save session', dir=directory,
        filter='Review Session *.embk')
    if not filepath:
        return
    preferences.set(
        'last_session_directory',
        os.path.dirname(filepath))
    data = data or get_session().serialize()
    with open(filepath, 'wb') as f:
        msgpack.dump(data, f)
    get_session().filepath = filepath
    get_main_window().update_title()
    set_recent_session_file(filepath)
    preferences.set(
        'last_session_directory', os.path.dirname(filepath))


@catch_error
@log_debug_command
def export_session(container_ids, filepath=None, packed=True):
    playlist = Playlist()
    containers = [get_session().get_container(i) for i in container_ids]
    playlist.set_containters(containers)
    annotations = {
        (id_, frame): model
        for (id_, frame), model in get_session().annotations.items()
        if id_ in container_ids}
    session = Session(playlist=playlist)
    session.annotations = annotations
    data = session.serialize()
    if filepath is not None:
        with open(filepath, 'wb') as f:
            msgpack.dump(data, f)
            return
    if not packed:
        return data
    return msgpack.dumps(data)


@catch_error
@log_debug_command
def export_current_video_session():
    directory = preferences.get(
        'last_session_directory',
        os.path.expanduser('~'))
    filepath, _ = QtWidgets.QFileDialog.getSaveFileName(
        get_main_window(), 'Save session', dir=directory,
        filter='Review Session *.embk')
    if not filepath:
        return
    preferences.set(
        'last_session_directory',
        os.path.dirname(filepath))
    export_session(
        get_session().get_current_container().id, filepath)


@catch_error
@log_debug_command
def toggle_mute_annotations():
    playing = get_main_window().media_player.is_playing()
    if playing:
        get_main_window().media_player.pause()
    state = not get_main_window().media_player.playlist.mute_annotations
    get_main_window().media_player.playlist.mute_annotations = state
    get_main_window().canvas.mute = state
    get_main_window().canvas.update()
    preferences.set('mute_annotations', state)
    if playing:
        get_main_window().media_player.play()


@catch_error
@log_debug_command
def toggle_mute_sound():
    main_window = get_main_window()
    session = get_session()
    state = get_action('ToggleMute').isChecked()
    session.playlist.set_mute(state)
    main_window.media_player.load_audio()
    preferences.set('mute', state)


@catch_error
@log_debug_command
def toggle_loop_mode():
    state = not get_session().playlist.playback_loop
    get_session().playlist.playback_loop = state
    preferences.set('loopmode', state)


@catch_error
@log_debug_command
def set_volume(value=int):
    """
    value: int -> [0 - 100]
    """
    get_main_window().media_player.set_volume(value / 100)


def _update_onionskin(frame):
    onionskin = []
    if get_session().onionskin.enabled is False:
        get_main_window().canvas.onionskin = onionskin
        return

    for f, opacity in get_session().onionskin.iter_from_frame(frame):
        annotation = get_session().get_annotation_at(f)
        if annotation is None or annotation.is_null():
            onionskin.append((None, opacity))
            continue
        if getattr(annotation, 'image_cache') is None:
            image_cache = get_session().render_frame(f, background=False)
            annotation.image_cache = image_cache
        onionskin.append((annotation.image_cache, opacity))
    get_main_window().canvas.onionskin = onionskin


@catch_error
@log_debug_command
def toggle_onionskin(*_):
    action = get_main_window().actionregistry.get('ToggleOnionSkin')
    state = action.isChecked()
    get_session().onionskin.enabled = state
    set_frame(get_session().playlist.frame)


@catch_error
@log_debug_command
def set_recent_session_file(filepath):
    filepath = os.path.normpath(filepath)
    recent_sessions = preferences.get('recent_sessions_files', [])
    if filepath in recent_sessions:
        recent_sessions.remove(filepath)
    recent_sessions.insert(0, filepath)
    recent_sessions = recent_sessions[:10]
    preferences.set('recent_sessions_files', recent_sessions)


def set_canvas_comment(comment):
    get_main_window().canvas.model.comment = comment
    get_main_window().drawed()


def _check_session_videos_paths(video_paths, session_folder):
    result = []
    for video_path in video_paths:
        if os.path.exists(os.path.expandvars(video_path)):
            result.append(video_path)
            continue
        alternate_path = f'{session_folder}/{os.path.basename(video_path)}'
        if os.path.exists(alternate_path):
            print(f'Video file repath: {video_path} -> {alternate_path}')
            result.append(alternate_path)
            continue
        raise FileNotFoundError(f'{video_path}: not found')
    return result
