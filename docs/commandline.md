# Embarker CLI Reference Guide

**Embarker** is a professional, lightweight video review player designed for pipeline integration. When running the compiled executable, you can use several command-line arguments to automate the loading of assets, plugins, and session states.

---

## Usage
`Embarker.exe [filepaths] [options]`

---

## Positional Arguments

| Argument | Description |
| :--- | :--- |
| `filepaths` | A list of one or more video file paths to open immediately upon launch. Supports standard video extensions defined in the decoder module. |

---

## Optional Flags and Arguments

### Session & Playlist Management
* **`-pl, --playlist_file <path>`**: Loads a specific playlist file into the player.
* **`-s, --session_file <path>`**: Loads a previously saved Embarker session.
* **`-asn, --open_session_file_as_new_file`**: Opens the session data as a new, unsaved file. This is designed for pipelines to prevent users from accidentally overwriting published reviews.

### Plugin & Environment Control
* **`-pp, --python_plugins <paths...>`**: Space-separated list of Python scripts to be injected as plugins.
* **`-env, --environment_files <paths...>`**: Loads additional `.env` files to set or append to system environment variables.
    > **Note:** When frozen, the application automatically searches for a `.env` file and a `/plugins` folder in the executable's directory.

### System & UI Settings
* **`-osn, --os_native_style`**: Forces the application to use the operating system's native UI style instead of the custom dark "Fusion" theme.
* **`-d, --debug`**: Activates debug mode for troubleshooting.

---

## Example Commands

**Open multiple videos:**
```bash
Embarker.exe "C:/Projects/Shot_01.mp4" "C:/Projects/Shot_02.mov"