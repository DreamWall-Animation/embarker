

BEFORE_NEW_SESSION = 'before_new_session'
BEFORE_OPEN_SESSION = 'before_open_session'
AFTER_NEW_SESSION = 'after_new_session'
AFTER_OPEN_SESSION = 'after_open_session'
ON_APPLICATION_EXIT = 'on_application_exit'
ON_PLUGIN_STARTUP = 'on_plugin_startup'


_event_callbacks = {
    BEFORE_NEW_SESSION: [],
    BEFORE_OPEN_SESSION: [],
    AFTER_NEW_SESSION: [],
    AFTER_OPEN_SESSION: [],
    ON_APPLICATION_EXIT: [],
    ON_PLUGIN_STARTUP: [],
}


def register_callback(event, plugin_id, function):
    if event not in _event_callbacks:
        raise ValueError(
            f'Unknown callback event: {event}. '
            f'Supported values: {list(_event_callbacks.keys())}')
    print(f'Register callback: {event}|{plugin_id} -> {function.__name__}')
    _event_callbacks[event].append((plugin_id, function))


def unregister_callbacks(plugin_id):
    for callbacks in _event_callbacks.values():
        for callback_plugin_id, callback in callbacks[:]:
            if callback_plugin_id == plugin_id:
                callbacks.remove((callback_plugin_id, callback))


def perform(event, plugin_id=None, *args, **kwargs):
    functions = _event_callbacks.get(event, [])
    for id_, function in functions:
        if plugin_id is not None and id_ != plugin_id:
            continue
        print(f'Perform callback: {event}| -> {function.__name__}')
        function(*args, **kwargs)