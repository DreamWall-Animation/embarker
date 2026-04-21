

# Available callback events

List of all callback event available from the callback namespace:
```python
from embarker import callback
```

Constant | Value | Function positional arguments
--- | --- | ---
callback.BEFORE_NEW_SESSION | `'before_new_session'` | (Session, Command)
callback.BEFORE_OPEN_SESSION | `'before_open_session'` | (Session, Command, session_data:dict)
callback.AFTER_NEW_SESSION | `'after_new_session'` | (Session, Command)
callback.AFTER_OPEN_SESSION | `'after_open_session'` | (Session, Command)
callback.ON_APPLICATION_EXIT | `'on_application_exit'` | (Session, Command)
callback.ON_PLUGIN_STARTUP | `'on_plugin_startup'` | (Session, Command)


