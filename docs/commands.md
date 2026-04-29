# Commands

Embarker API commands. This module defines all the functions exposed to
control the application externally.

All these functions are available in the `embarker.commands` module.
Exemple:
```python
import embarker.commands as ebc

ebc.set_frame(15)
image = ebc.render_frame(15)
image.save('c:/image.png')
```

## Functions Index

| Return | Function | Arguments |
| :--- | :--- | :--- |
| `CanvasModel` | [`create_new_annotation_model`](#create_new_annotation_model) | - |
| `None` | [`delete_annotation`](#delete_annotation) | `frame=None` |
| `None` | [`export_annotated_frames`](#export_annotated_frames) | `directory=None` |
| `None` | [`export_current_frame`](#export_current_frame) | `filepath=None` |
| `None` | [`export_current_video_session`](#export_current_video_session) | - |
| `None` | [`export_preferences`](#export_preferences) | - |
| `bytes/dict` | [`export_session`](#export_session) | `container_ids, filepath=None, packed=True` |
| `QAction` | [`get_action`](#get_action) | `action_id` |
| `int` | [`get_frame`](#get_frame) | - |
| `QtWidgets.QMainWindow` | [`get_main_window`](#get_main_window) | - |
| `Session` | [`get_session`](#get_session) | - |
| `None` | [`import_preferences`](#import_preferences) | - |
| `None` | [`import_session_annotations`](#import_session_annotations) | `filepath=None, container_id=None` |
| `None` | [`import_session_annotations_prompt`](#import_session_annotations_prompt) | - |
| `bool` | [`is_playing`](#is_playing) | - |
| `None` | [`load_playlist`](#load_playlist) | `filepath=None` |
| `None` | [`load_videos`](#load_videos) | `video_paths, container_ids=None, metadatas=None, index=-1` |
| `None` | [`new_session`](#new_session) | - |
| `None` | [`next_frame`](#next_frame) | - |
| `None` | [`open_session`](#open_session) | `filepath=None, as_new_file=False` |
| `None` | [`open_session_data`](#open_session_data) | `data` |
| `None` | [`play_pause`](#play_pause) | - |
| `None` | [`previous_frame`](#previous_frame) | - |
| `None` | [`prompt_load_videos`](#prompt_load_videos) | `insert=False, after=False` |
| `None` | [`remove_current_video`](#remove_current_video) | - |
| `QtGui.QImage` | [`render_frame`](#render_frame) | `frame` |
| `None` | [`replace_videos`](#replace_videos) | `video_path, container_id, metadata=None` |
| `None` | [`reset_canvas`](#reset_canvas) | - |
| `None` | [`save`](#save) | - |
| `None` | [`save_as`](#save_as) | `data=None` |
| `None` | [`set_canvas_comment`](#set_canvas_comment) | `comment` |
| `None` | [`set_frame`](#set_frame) | `frame` |
| `None` | [`set_next_annotation`](#set_next_annotation) | - |
| `None` | [`set_next_video`](#set_next_video) | - |
| `None` | [`set_playback_end`](#set_playback_end) | `frame=None` |
| `None` | [`set_playback_range`](#set_playback_range) | `start, end` |
| `None` | [`set_playback_start`](#set_playback_start) | `frame=None` |
| `None` | [`set_previous_annotation`](#set_previous_annotation) | - |
| `None` | [`set_previous_video`](#set_previous_video) | - |
| `None` | [`set_recent_session_file`](#set_recent_session_file) | `filepath` |
| `None` | [`set_volume`](#set_volume) | `value` |
| `None` | [`toggle_loop_mode`](#toggle_loop_mode) | - |
| `None` | [`toggle_mute_annotations`](#toggle_mute_annotations) | - |
| `None` | [`toggle_mute_sound`](#toggle_mute_sound) | - |
| `None` | [`toggle_onionskin`](#toggle_onionskin) | `*_` |

---

## Functions Descriptions

### `create_new_annotation_model`
Factory method for creating a new `CanvasModel` using the current viewport mapper.

### `delete_annotation`
Deletes the annotation at the specified frame or current frame if not provided.

### `export_annotated_frames`
Exports all annotated frames as PNG images into the specified directory.

### `export_current_frame`
Exports the current frame (with annotations) as a PNG image.

### `export_current_video_session`
Exports the current video container and its annotations into a new session file.

### `export_preferences`
Exports UI state and tool settings into a YAML file.

### `export_session`
Exports selected containers and their annotations. Can return packed (msgpack) or raw data.

### `get_action`
Returns a `QAction` from the main window action registry.

### `get_frame`
Returns the current frame

### `get_main_window`
Returns the main application window instance.

### `get_session`
Returns the current active `Session` object.

### `import_preferences`
Imports UI and tool configuration from a YAML file.

### `import_session_annotations`
Imports annotations from another session file into a specific container.

### `import_session_annotations_prompt`
Opens a dialog to import annotations from another session.

### `is_playing`
Returns whether the media player is currently playing.

### `load_playlist`
Loads a playlist from a `.playlist` YAML file.

### `load_videos`
Adds videos to the current session.

Supports:
- Optional container IDs
- Metadata injection (e.g. pipeline IDs)
- Custom insertion index

### `new_session`
Resets the application state and starts a new clean session.

### `next_frame`
Moves playback to the next frame, respecting playback range.

### `open_session`
Opens a `.embk` session file. If no filepath is provided, opens a file dialog.

### `open_session_data`
Loads a session from raw data.

### `play_pause`
Toggles playback and updates onion skin cache for current annotation.

### `previous_frame`
Moves playback to the previous frame, respecting playback range.

### `prompt_load_videos`
Opens a file dialog to load video files into the session.

### `remove_current_video`
Removes the currently selected video from the playlist.

### `render_frame`
Renders a specific frame with annotations and returns it as a `QImage`.

### `replace_videos`
Replaces a video in the playlist while keeping the same container ID.

### `reset_canvas`
Resets canvas zoom to default and centers the view.

### `save`
Saves the current session to its associated file.

### `save_as`
Prompts user to save the session to a new file.

### `set_canvas_comment`
Sets a comment string on the current canvas model.

### `set_frame`
Sets the current playback frame and updates onion skin rendering.

### `set_next_annotation`
Jumps to the next annotated frame.

### `set_next_video`
Jumps to the first frame of the next video.

### `set_playback_end`
Sets the playback end frame.

### `set_playback_range`
Defines the playback start and end frames.

### `set_playback_start`
Sets the playback start frame.

### `set_previous_annotation`
Jumps to the previous annotated frame.

### `set_previous_video`
Jumps to the previous video start frame.

### `set_recent_session_file`
Adds a session file path to the recent files list.

### `set_volume`
Sets playback volume (0–100).

### `toggle_loop_mode`
Toggles loop playback mode.

### `toggle_mute_annotations`
Toggles visibility of annotations during playback.

### `toggle_mute_sound`
Toggles audio mute state.

### `toggle_onionskin`
Enables or disables onion skin rendering.
