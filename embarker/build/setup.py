
import os
import json
from cx_Freeze import setup, Executable


HERE = os.path.dirname(__file__)
with open(f'{HERE}/build_config.json', 'r') as f:
    config = json.load(f)
print(f'Build: {config["executable"]}')

import pprint
print("CONFIG ---")
pprint.pprint(config)


build_options = {
    'includes': config['includes'],
    'include_files': config['include_files']}

executable = Executable(
    config["executable"],
    target_name='Embarker.exe',
    # base='Win32GUI',
    icon=config['icon'])

setup(
    name='Embarker',
    version="0.1",
    description="Embarker",
    options={"build_exe": build_options},
    executables=[executable],
)