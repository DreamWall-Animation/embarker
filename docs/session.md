# Session

A Session is an abstract representation of the currently opened document. It links annotations, preferences, and media containers.

To get the current application session object:

```python
from embarker.session import get_session
session = get_session()
```

## Variable Index
| Value type | Variable | Variable type |
| :--- | :--- | :--- |
| `Preferences` | [preferences](#preferences) | property |
| `None | str` | filepath | variable |
| `Playlist` | playlist | variable |
| `dict({(id: str, frame: int) : CanvasModel})` | annotations | variable
| `OnionSkin` | onionskin | variable |
| `dict` | [metadata](#meta-data) | variable |

## Variables Descriptions

### Preferences

A handler for persistent preferences, allowing custom user settings to be saved and accessed globally.
```python
self.session.preferences.set('My custom pref', value)
self.session.preferences.get('My custom pref', value, default)
```

### Meta-data
Free dictionnary to store custom user data.

## Method Index

| Return | Method | Arguments |
| :--- | :--- | :--- |
| `None` | [`add_annotation_at`](#add_annotation_at) | `frame: int, annotation: CanvasModel` |
| `None` | [`cache_annotations`](#cache_annotations) | `force=True` |
| `None` | [`cache_current_annotation`](#cache_current_annotation) | - |
| `None` | [`clear_empty_annotations`](#clear_empty_annotations) | - |
| `None` | [`delete_annotation_at`](#delete_annotation_at) | `frame: int` |
| `CanvasModel | None` | [`get_annotation_at`](#get_annotation_at) | `frame: int, viewportmapper: NDCViewportMapper = None` |
| `list[int]` | [`get_annotated_frames`](#get_annotated_frames) | - |
| `VideoContainer | ImageSequenceContainer` | [`get_container`](#get_container) | `container_id` |
| `dict` | [`get_container_annotations`](#get_container_annotations) | `container_id, include_empty_current_frame=False, exportable_only=False` |
| `list` | [`get_containers_in_range`](#get_containers_in_range) | `start_frame, end_frame` |
| `CanvasModel` | [`get_current_annotation`](#get_current_annotation) | - |
| `VideoContainer | ImageSequenceContainer` | [`get_current_container`](#get_current_container) | - |
| `int` | [`get_current_container_index`](#get_current_container_index) | - |
| `bool` | [`is_empty`](#is_empty) | - |
| `QtGui.QPixmap` | [`render_frame`](#render_frame) | `frame, background=True` |
| `dict[int, QtGui.QPixmap]` | [`render_container_annotated_frames`](#render_container_annotated_frames) | `container_id` |
| `dict` | [`serialize`](#serialize) | - |

---

## Method Descriptions

### `add_annotation_at`
Adds a `CanvasModel` at a specific absolute timeline frame. The internal dictionary is re-sorted based on the playlist order to maintain chronological consistency.

### `cache_annotations`
Renders and stores all session annotations as ndarrays in the playlist's image override cache. Useful for performance during playback.

### `cache_current_annotation`
Caches the annotation of the current frame. If the annotation is null, it removes any existing image override for this specific frame.

### `clear_empty_annotations`
Filters the internal annotations dictionary to remove all entries where the `CanvasModel` is considered null or empty.

### `delete_annotation_at`
Deletes the `CanvasModel` and removes any associated image override at the specified absolute timeline frame.

### `get_annotation_at`
Returns the `CanvasModel` located at the absolute timeline frame. If no annotation exists at that position, it returns a new `CanvasModel` (if a `viewportmapper` is provided).

### `get_annotated_frames`
Returns a sorted list of all absolute frames across the entire timeline that currently contain an annotation.

### `get_container`
Returns the media container instance (Video or Image Sequence) associated with the given `container_id`.

### `get_container_annotations`
Returns a dictionary of all annotations belonging to a specific container ID. Can optionally include the current frame even if empty, or filter by 'exportable' metadata.

### `get_containers_in_range`
Returns a list of all unique media containers that are present between the specified `start_frame` and `end_frame` on the global timeline.

### `get_current_annotation`
Convenience method to return the `CanvasModel` at the current playlist frame. Returns `None` if the frame is not yet annotated.

### `get_current_container`
Returns the media container currently active at the player's current frame.

### `get_current_container_index`
Returns the integer index of the currently active container within the playlist's sequence.

### `is_empty`
Returns `True` if the session has no associated filepath and the playlist contains no media containers.

### `render_frame`
Renders a specific frame to a `QPixmap`. If `background` is `True`, the video frame is drawn under the annotation. If `False`, the annotation is rendered on a transparent background.

### `render_container_annotated_frames`
Renders all exportable annotated frames belonging to a specific container and returns them as a dictionary mapping relative frames to `QPixmap` objects.

### `serialize`
Converts the full session state (version, containers, annotations, and metadata) into a dictionary suitable for binary serialization (msgpack).