### Playlist Files (`.pl`)

Embarker supports playlist files (`.pl`) to load large numbers of media files efficiently. This is especially useful to bypass operating system command-line length limitations when opening many files at once.

In addition to listing media files, playlist files also allow attaching metadata to each entry.

Playlist files can be written in either **YAML** or **JSON** format.

---

### Structure

Each entry in the playlist is defined as:

* A file path (string)
* An associated metadata object (dictionary)

---

### YAML Example

```yaml
- - c:/movie.001.mov  # Video path
  - key1: value1      # Meta-data as dict
    key2: value2
    key3: value3

- - c:/movie.002.mov
  - key1: value1
    key2: value2
    key3: value3

- - c:/movie.003.mov
  - key1: value1
    key2: value2
    key3: value3
```

---

### JSON Equivalent

```json
[
  [
    "c:/movie.001.mov",
    {
      "key1": "value1",
      "key2": "value2",
      "key3": "value3"
    }
  ],
  [
    "c:/movie.002.mov",
    {
      "key1": "value1",
      "key2": "value2",
      "key3": "value3"
    }
  ],
  [
    "c:/movie.003.mov",
    {
      "key1": "value1",
      "key2": "value2",
      "key3": "value3"
    }
  ]
]
```

---

### Notes

* Playlist files help avoid command-line length limits when opening many files.
* Metadata can be used by Embarker or plugins for custom behavior.
* File paths should be absolute or resolvable by the application environment.
