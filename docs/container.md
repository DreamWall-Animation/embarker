# VideoContainer

## Method Index

| Return | Method | Arguments |
| :--- | :--- | :--- |
| `np.ndarray` | [`decode_frame`](#decode_frame) | `frame` |
| `np.ndarray` | [`decode_next_frame`](#decode_next_frame) | `self` |
| `dict` | [`metadata`](#metadata) | `(property) self` |
| `None` | [`set_metadata`](#set_metadata) | `key, value` |

---

## Method Descriptions

### `__init__`
Initializes the video container by opening the file path. It automatically detects the video stream, sets the decoder to multi-threaded mode (`AUTO`) for performance, and calculates duration, length, and FPS.

### `decode_frame`
Returns the requested frame as an RGB24 NumPy array. If the requested frame index is lower than the current decoder position.
It is possible to convert the result to a QPixmap using
```python
from embarker.decoder import numpy_to_qpixmap
pixmap: QtGui.QPixmap = numpy_to_qpixmap(container.decode_frame())
```

### `decode_next_frame`
Advances the internal decoder by one step and returns the immediate next frame in the stream as a NumPy array.

### `metadata`
**Property.** Returns a merged dictionary containing both the custom user-defined metadata and the original technical metadata extracted directly from the video file container.

### `set_metadata`
Updates or adds a specific key-value pair to the internal custom metadata dictionary.
