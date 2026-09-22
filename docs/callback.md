

# Callback

The `embarker.callback` module is a small event system used to hook plugin
code into application lifecycle events.

```python
from embarker import callback
```

## Registering callbacks

A plugin module usually declares a module-level `CALLBACKS` dict mapping an
event constant to a list of functions:

```python
def on_session_opened():
    print('Session opened')

CALLBACKS = {
    callback.AFTER_OPEN_SESSION: [on_session_opened],
}
```

When the plugin is loaded, `PluginRegistry` registers each function under
the plugin's own id automatically, calling `register_callback` internally.

### `register_callback(event, plugin_id, function)`
Registers `function` to be called when `event` is performed. Raises
`ValueError` if `event` is not one of the constants below.

### `unregister_callbacks(plugin_id)`
Removes every callback registered by `plugin_id`, for every event. Called
automatically when a plugin is unloaded.

### `perform(event, plugin_id=None, *args, **kwargs)`
Calls every function registered for `event`. If `plugin_id` is provided,
only the callback(s) registered under that exact `plugin_id` are called.
Any extra `args`/`kwargs` are forwarded to the callback function(s).

## Available callback events

Constant | Value | Triggered by | Arguments passed to the callback
--- | --- | --- | ---
`BEFORE_NEW_SESSION` | `'before_new_session'` | `commands.new_session()`, before the session state is cleared | none
`AFTER_NEW_SESSION` | `'after_new_session'` | `commands.new_session()`, after the session state is cleared | none
`BEFORE_OPEN_SESSION` | `'before_open_session'` | `commands.open_session()`, before the session file is loaded | `session_data` (dict), as keyword argument
`AFTER_OPEN_SESSION` | `'after_open_session'` | `commands.open_session()` / `commands.open_session_data()`, once the session has finished loading | none
`AFTER_PLAYLIST_CHANGED` | `'after_playlist_changed'` | `commands.load_videos()`, `commands.replace_video()`, `commands.remove_current_video()`, after the playlist content changed | none
`ON_APPLICATION_EXIT` | `'on_application_exit'` | `MainWindow.closeEvent()`, when the application is closing | none
`ON_PLUGIN_STARTUP` | `'on_plugin_startup'` | `PluginRegistry`, once a given plugin has finished loading | none — only the callback(s) registered by that specific plugin are called

Notes:
- `commands.open_session_data()` also performs `BEFORE_OPEN_SESSION`, but
  passes its `data` argument positionally as `plugin_id` instead of as
  `session_data`, so on that code path no callback is currently invoked.
- `MainWindow.closeEvent()` performs `ON_APPLICATION_EXIT` with the current
  `Session` instance as `plugin_id`, which never matches a plugin's own id,
  so in practice no callback is currently invoked for this event either.
- `ON_PLUGIN_STARTUP` is always performed with a specific `plugin_id`, so it
  behaves as a per-plugin "I just finished loading" notification rather
  than a broadcast to every registered plugin.
