# Containers

A container wraps a media source and exposes a unified decoding interface.
All containers share `id`, `path`, `length`, `fps`, `duration`, `metadata`,
`audio_samples`, and `thumbnail()`.

Decoded frames are returned as RGB24 (or RGBA) NumPy arrays.
Use `numpy_to_qpixmap` from `embarker.decoder` to convert them to `QPixmap`.

```python
from embarker.decoder import numpy_to_qpixmap
pixmap = numpy_to_qpixmap(container.decode_frame(0))
```

---

## `VideoContainer`

Wraps a video file (mp4, mov, avi, mkv) using `PyAV`. Automatically detects
the video stream and uses multi-threaded decoding for performance.

| Method | Arguments | Description |
| :--- | :--- | :--- |
| `decode_frame` | `frame` | Returns the frame at the given index as a NumPy array. Seeks automatically when needed. |
| `decode_next_frame` | - | Advances the decoder by one step and returns the next frame. |
| `metadata` *(property)* | - | Merged dict of user-defined metadata and the file's technical metadata. |
| `set_metadata` | `key, value` | Adds or updates a key in the custom metadata dict. |

---

## `ImageSequenceContainer`

Wraps a sequence of image files matched by a glob pattern (EXR, PNG, JPG,
TIFF, WebP). Each file maps to one frame. FPS defaults to 25.

| Method | Arguments | Description |
| :--- | :--- | :--- |
| `decode_frame` | `frame` | Reads and returns the image at the given index as a NumPy array. |
| `set_metadata` | `key, value` | Adds or updates a key in the metadata dict. |

---

## `MultiContainer`

Composite container that renders several containers together into a single
frame. Supports `"horizontal"`, `"vertical"`, and `"grid"` layouts. Frames
are decoded in parallel. Output resolution is capped at `max_pixels`
(default 1920×1080) to keep performance predictable.

| Method | Arguments | Description |
| :--- | :--- | :--- |
| `decode_frame` | `frame` | Decodes all sub-containers in parallel and composites the result. |
| `add_side_container` | `container` | Appends a container to the layout and rebuilds the thread pool. |
| `metadata` *(property)* | - | Delegates to the first sub-container. |
