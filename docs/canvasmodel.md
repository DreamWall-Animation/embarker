# CanvasModel

Core data model representing a drawable canvas with layers, images, annotations,
and undo/redo capabilities.

This class is responsible for managing:
- Layer stack and shapes
- Image overlays
- Selection system
- Undo/redo history
- Serialization/deserialization

⚠️ Manipulate this class with caution. Misuse may break the application.

---

## Method Index

| Return | Method | Arguments |
| :--- | :--- | :--- |
| `list` | [`copy_selection`](#copy_selection) | - |
| `None` | [`paste`](#paste) | `shapes` |
| `None` | [`duplicate_selection`](#duplicate_selection) | - |
| `list` | [`texts`](#texts) | *(property)* |
| `None` | [`append_image`](#append_image) | `image` |
| `None` | [`delete_image`](#delete_image) | `index` |
| `None` | [`duplicate_layer`](#duplicate_layer) | - |
| `None` | [`set_baseimage`](#set_baseimage) | `image` |
| `None` | [`add_layer`](#add_layer) | `undo=True, name=None, locked=False, blend_mode=None, index=None` |
| `None` | [`add_layer_image`](#add_layer_image) | `path, blend_mode=None, undo=True` |
| `None` | [`add_image`](#add_image) | `image` |
| `None` | [`move_layer`](#move_layer) | `old_index, new_index` |
| `None` | [`add_shape`](#add_shape) | `shape` |
| `None` | [`set_current_blend_mode_name`](#set_current_blend_mode_name) | `name` |
| `None` | [`add_undo_state`](#add_undo_state) | - |
| `None` | [`restore_state`](#restore_state) | `state` |
| `None` | [`undo`](#undo) | - |
| `None` | [`redo`](#redo) | - |
| `dict` | [`default_state`](#default_state) | - |
| `dict` | [`serialize`](#serialize) | - |
| `None` | [`deserialize`](#deserialize) | `data` |
| `bool` | [`is_null`](#is_null) | - |

---

## Method Descriptions

### `copy_selection`
Copies the current selection.

- Returns full shapes if entirely selected
- Splits strokes if partially selected

### `paste`
Pastes shapes into the current layer and updates selection.

### `duplicate_selection`
Duplicates the current selection by copying and pasting it.

### `texts`
Returns all text elements from the layer stack.

### `append_image`
Adds an image to the image stack and registers undo state.

### `delete_image`
Removes an image from the image stack by index.

### `duplicate_layer`
Duplicates the currently active layer.

### `set_baseimage`
Sets the base image of the canvas and updates its bounds.

### `add_layer`
Adds a new layer to the layer stack.

Supports:
- Custom name (auto-unique)
- Lock state
- Blend mode
- Insert index

### `add_layer_image`
Creates a new layer and loads an image into it.

### `add_image`
Adds an image as a drawable `Bitmap` shape using viewport coordinates.

### `move_layer`
Moves a layer from one index to another.

### `add_shape`
Adds a shape to the current layer.

### `set_current_blend_mode_name`
Sets the blend mode of the current layer.

### `add_undo_state`
Pushes the current state into the undo stack.

- Clears redo stack
- Stores full snapshot of:
  - layers
  - images
  - properties

### `restore_state`
Restores the canvas from a saved state.

### `undo`
Reverts to the previous state.

- Pops from undo stack
- Pushes to redo stack

### `redo`
Restores the next state from redo stack.

### `default_state`
Returns a default empty canvas state.

### `serialize`
Serializes the canvas model into a dictionary.

Includes:
- Layer stack
- Metadata
- Wash settings
- Comment

### `deserialize`
Loads the canvas state from serialized data.

- Resets undo/redo stacks
- Restores layer stack and properties

### `is_null`
Checks whether the canvas is empty.

Returns `True` if:
- No base image
- No layers
- No meaningful comment