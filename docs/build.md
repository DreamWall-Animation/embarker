# Embarker Build Guide

This document explains how to build **Embarker** using the provided `build.py` script.

---

## 1. Requirements

- Python **3.11**
- Windows OS (script is Windows-oriented)
- Git
- pip

---

## 2. Install Python

Download Python 3.11:

https://www.python.org/downloads/

During installation:
- ✔ Add Python to PATH
- ✔ Install for all users

Verify installation:

```bash
python --version
```

---

## 3. Install Global Dependencies

```bash
pip install --upgrade pip
pip install cx_Freeze pyyaml requests
```

---

## 4. Install / Prepare FFmpeg

### Option A — Clone a prebuilt repository (recommended)

```bash
git clone https://github.com/BtbN/FFmpeg-Builds.git
```

Locate:

```
bin/ffmpeg.exe
bin/ffprobe.exe
```

Copy them into:

```
ffmpeg/
 ├── ffmpeg.exe
 └── ffprobe.exe
```

---

### Option B — Use your own FFmpeg

You can specify the path directly:

```bash
python build.py -ffmpeg path/to/ffmpeg.exe
```

---

## 5. Project Structure

```
project/
 ├── build.py
 ├── setup.py
 ├── requirements.txt
 ├── embarker/
 ├── plugins/
 ├── ffmpeg/
 │   ├── ffmpeg.exe
 │   └── ffprobe.exe
```

---

## 6. Run the Build

### Simple build:

```bash
python build.py
```

---

### Advanced build:

```bash
python build.py ^
  -d build ^
  -z ^
  -ffmpeg ffmpeg/ffmpeg.exe ^
  -i embarker ^
  -pm plugins/my_plugin.py ^
  -l external_libs ^
  -r extra_requirements.txt ^
  -e .env
```

---

## 7. Build Output

After building:

```
build/
 └── embarker-<version>.b<build_number>/
     ├── embarker.exe
     ├── lib/
     ├── plugins/
     ├── ffmpeg.exe
     ├── ffprobe.exe
     └── .env (optional)
```

---

## 8. Create Archive

```bash
python build.py -z
```

This will generate:

```
embarker-<version>.zip
```

---

## 9. Key Options

| Option | (Long) | Description |
|------|-|------------|
| `-d`      | `--build_directory`           | Build directory |
| `-p`      | `--preserve_venv`             | Preserve virtual environment |
| `-z`      | `--create_archive`            | Create archive |
| `-r`      | `--additional_requirements`   | Additional requirements |
| `-pm`     | `--plugin_modules`            | Plugin modules |
| `-l`      | `--local_library_paths`       | Local libraries |
| `-i`      | `--additional_includes`       | Additional includes |
| `-e`      | `--environment_file`          | Environment file |
| `-ffmpeg` | `--ffmpeg_path`               | FFmpeg path to include |



### 🔹 Build Directory
**Short:** `-d`
**Long:** `--build_directory`

Defines where the build process will output all generated files.

**Example:**
```bash
python build.py --build_directory build_output
```

If not specified, the script uses the current working directory.

---

### 🔹 Preserve Virtual Environment
**Short:** `-p`
**Long:** `--preserve_venv`

By default, the virtual environment created for the build is deleted after completion.
This flag prevents deletion so you can reuse or debug the environment.

**Example:**
```bash
python build.py --preserve_venv
```

---

### 🔹 Create Archive
**Short:** `-z`
**Long:** `--create_archive`

Creates a `.zip` archive of the final build output.

**Example:**
```bash
python build.py --create_archive
```

---

### 🔹 Additional Requirements
**Short:** `-r`
**Long:** `--additional_requirements`

Install extra Python dependencies in the temporary virtual environment.

**Example:**
```bash
python build.py --additional_requirements extra_requirements.txt
```

Multiple files:
```bash
python build.py -r requirements1.txt requirements2.txt
```

---

### 🔹 Plugin Modules
**Short:** `-pm`
**Long:** `--plugin_modules`

Specifies additional Python plugin files to include in the build.

**Example:**
```bash
python build.py --plugin_modules plugins/my_plugin.py
```

---

### 🔹 Local Library Paths
**Short:** `-l`
**Long:** `--local_library_paths`

Includes external or local Python packages not automatically bundled.

**Example:**
```bash
python build.py --local_library_paths path/to/my_lib
```

---

### 🔹 Additional Includes
**Short:** `-i`
**Long:** `--additional_includes`

Adds extra Python modules to force inclusion in the build.

**Example:**
```bash
python build.py --additional_includes numpy scipy
```

---

### 🔹 Environment File
**Short:** `-e`
**Long:** `--environment_file`

Includes a `.env` file in the final build.

**Example:**
```bash
python build.py --environment_file .env
```

---

### 🔹 FFmpeg Path
**Short:** `-ffmpeg`
**Long:** `--ffmpeg_path`

Specifies the path to `ffmpeg.exe`.

**Example:**
```bash
python build.py --ffmpeg_path ffmpeg/ffmpeg.exe
```

---

### 🔹 Full Example

```bash
python build.py ^
  -d build ^
  -z ^
  -r extra_requirements.txt ^
  -pm plugins/plugin1.py ^
  -l libs/custom ^
  -i numpy scipy ^
  -e .env ^
  -ffmpeg ffmpeg/ffmpeg.exe
```


---

## 10. Troubleshooting

### Missing FFmpeg
```
FileNotFoundError: FFMPEG not found
```
→ Provide correct path or place executables in `ffmpeg/`

---

### Python version issues
Ensure Python 3.11 is used:

```bash
py -3.11 -m venv
```

---

### Build fails
- Check dependencies
- Check `setup.py`
- Ensure correct paths

---

## 11. Notes

- The script is **Windows-specific**
- cx_Freeze is used for packaging
- Some libraries are manually copied due to limitations
