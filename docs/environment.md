### Environment Variables

Embarker can be configured using environment variables to customize its behavior and extend its functionality. The following variables are available:

* `EMBARKER_PREFERENCES_FILEPATH`
  Full path to use for storing customized user preferences.

* `EMBARKER_PREFERENCES_FILENAME`
  Filename to override only the name of the preferences file used by the application.

* `EMBARKER_PLUGIN_PATHS`
  A list of `.py` plugin files to be loaded by the application.

> **Note (Frozen/Executable Distribution):**
> When using a packaged (frozen) version of Embarker, a `.env` file placed next to the executable will automatically be loaded into the environment.

The `.env` file must follow this structure:

```
VARIABLE=VALUE
VARIABLE+=VALUE
```

* `=` sets or overrides a variable
* `+=` appends a value to an existing variable

**Example:**

```
PATH+=";c:/ffmpeg"
```

Additionally, the system will automatically resolve the `$HERE` variable inside paths to the directory containing `Embarker.exe`.
