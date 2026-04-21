import os
import json
import yaml
import shutil
import argparse
import datetime
import subprocess


parser = argparse.ArgumentParser()
parser.add_argument(
    '-d', '--build_directory',
    help='Build Directory')

help_ = """\
Preserve venv created by the build.
This must be manually deleted before trigger another build."""
parser.add_argument(
    '-p', '--preserve_venv',
    action='store_true',
    default=False,
    help=help_)

parser.add_argument(
    '-z', '--create_archive',
    action='store_true',
    default=False,
    help='Package the build as an archive file.')

help_ = """
Additional requirements.txt to install in the temporary venv.
This is required when it is build with plugins."""
parser.add_argument(
    '-r', '--additional_requirements',
    nargs='*',
    help=help_)

help_ = """
Plugins modules to includes."""
parser.add_argument(
    '-pm', '--plugin_modules',
    nargs='*',
    default=None,
    help=help_)

help_ = """
Local python library paths. This is required when it is build with plugins."""
parser.add_argument(
    '-l', '--local_library_paths',
    nargs='*',
    help=help_)

help_ = 'Package to includes. This is required when it is build with plugins.'
parser.add_argument(
    '-i', '--additional_includes',
    nargs='*',
    help=help_)

help_ = 'Additional environment file to include with executable.'
parser.add_argument(
    '-e', '--environment_file',
    type=str, default=False,
    help=help_)

parser.add_argument(
    '-ffmpeg', '--ffmpeg_path',
    type=str, default=False,
    help=help_)

args = parser.parse_args()


# Setup build directory
if args.build_directory:
    ROOT = args.build_directory
    os.makedirs(ROOT, exist_ok=True)
    os.chdir(ROOT)
else:
    ROOT = os.getcwd()

venv_name = 'embarker_build'
HERE = os.path.dirname(__file__)

# Build venv and install/copy dependencies
requirement_paths = [f'{HERE}/requirements.txt']
if args.additional_requirements:
    requirement_paths.extend(args.additional_requirements)
ps1_script = f"""py -3.11 -m venv {venv_name}
{venv_name}/Scripts/activate
"""
for requirement_path in requirement_paths:
    ps1_script += f'pip install --index-url https://pypi.org/simple --no-cache-dir -r {requirement_path}\n'
ps1_path = f'{ROOT}/setup.ps1'
with open(ps1_path, 'w') as f:
    f.write(ps1_script)

subprocess.run(['powershell', ps1_path])

build_number = f'{datetime.datetime.now():%y%m%d-%H%M}'


# Config cx_Freeze includes.
includes = [
    'msgpack',
    'yaml',
    'numpy',
    'OpenImageIO',
    'uuid',
    'PySide6.QtOpenGL',
    'PySide6.QtOpenGLWidgets',
    'wave',
    'sounddevice']
if args.additional_includes:
    includes.extend(args.additional_includes)


# Launch CX_Freeze script
setup_source = os.path.expandvars(f'{HERE}/setup.py')
executable_file = os.path.expandvars(f'{HERE}/../embarker/__main__.py')
icon_file = os.path.expandvars(f'{HERE}/../embarker/icons/milo.ico')

setup_file = f'{ROOT}/setup.py'
shutil.copy(setup_source, setup_file)
python_path = f'{ROOT}/{venv_name}/Scripts/python.exe'


with open(f'{os.getcwd()}/build_config.json', 'w') as f:
    json.dump({
        'include_files': [
            f'{ROOT}/{venv_name}/Lib\site-packages\PySide6\plugins'],
        'includes': includes,
        'executable': executable_file,
        'icon': icon_file}, f)

try:
    cmd = [python_path, setup_file, 'build']
    subprocess.check_call(cmd, shell=True)

    # Gather version and build infos
    info_file = f'{HERE}/../embarker/info.yaml'
    with open(info_file, 'r') as f:
        data = yaml.safe_load(f)
    data['build'] = build_number
    data['build_datetime'] = datetime.datetime.now()
    data['build_user'] = os.getenv('USERNAME')

    major, minor, fix = data['version']
    name = f'embarker-{major}.{minor}.{fix}.b{data["build"]}'
    os.rename(
        f'{ROOT}/build/exe.win-amd64-3.11',
        f'{ROOT}/build/{name}')

    # Savagely append the local packages because that son of a b**** of cx freeze
    # does not understand anything
    packages_path = f'{ROOT}/build/{name}/lib'
    local_library_paths = [
        f'{ROOT}/{venv_name}/Lib/site-packages/av',
        f'{ROOT}/{venv_name}/Lib/site-packages/av.libs',
        f'{ROOT}/{venv_name}/Lib/site-packages/pydub',
        f'{ROOT}/{venv_name}/Lib/site-packages/OpenGL',
        f'{HERE}/../embarker',
        f'{HERE}/../../viewportmapper',
        f'{HERE}/../../paintcanvas']
    if args.local_library_paths:
        local_library_paths.extend(args.local_library_paths)
    for library_path in local_library_paths:
        base = os.path.basename(library_path)
        dst = f'{packages_path}/{base}'
        print(f'Copy library: {library_path} -> {dst}')
        shutil.copytree(library_path, dst, dirs_exist_ok=True)

finally:
    if not args.preserve_venv:
        shutil.rmtree(f'{ROOT}/{venv_name}')
        os.remove('setup.py')
        os.remove('setup.ps1')
        os.remove('build_config.json')

# Replace savagely the info.yaml
build_info_file = f'{packages_path}/embarker/info.yaml'
with open(build_info_file, 'w') as f:
    yaml.dump(data, f)


plugin_modules = args.plugin_modules or []
plugin_dir = f'{os.path.dirname(HERE)}/plugins'  # build in plugins dir
plugin_modules.extend([
    f'{plugin_dir}/{f}'
    for f in os.listdir(plugin_dir)
    if f.endswith('.py')])
plugin_dest = f'{ROOT}/build/{name}/plugins'
os.makedirs(plugin_dest, exist_ok=True)
for plugin_module in plugin_modules:
    dst = f'{plugin_dest}/{os.path.basename(plugin_module)}'
    shutil.copy(plugin_module, dst)


if args.environment_file:
    dst = f'{ROOT}/build/{name}/.env'
    shutil.copy(args.environment_file, dst)


# Include FFMPEG
ffmpeg_path = args.ffmpeg_path or f'{HERE}/../ffmpeg/ffmpeg.exe'
if not os.path.exists(ffmpeg_path):
    raise FileNotFoundError('FFMPEG not found')
directory = f'{ROOT}/build/{name}/lib'
os.makedirs(directory, exist_ok=True)
shutil.copy(ffmpeg_path, f'{directory}/ffmpeg.exe')
ffprobe = f'{os.path.dirname(ffmpeg_path)}/ffprobe.exe'
shutil.copy(ffprobe, f'{directory}/ffprobe.exe')


destination = f'{ROOT}/build/{name}'
if args.create_archive:
    shutil.make_archive(
        destination,
        'zip',
        f'{ROOT}/build/{name}')

print("build is done !")