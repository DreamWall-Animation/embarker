import importlib.util
import inspect
import sys
from dwramplayer.api import DwRamPlayerDockWidget


def extract_module_available_dock(module_filepath):
    try:
        spec = importlib.util.spec_from_file_location(
            "UserPlugin", module_filepath)
        if spec is None or spec.loader is None:
            raise ImportError()
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        required = DwRamPlayerDockWidget.__annotations__.keys()
        subclasses = []
        for _, obj in inspect.getmembers(module):
            conditions = (
                inspect.isclass(obj) and
                issubclass(obj, DwRamPlayerDockWidget) and
                obj is not DwRamPlayerDockWidget)
            if not conditions:
                continue
            missing = []
            for const in required:
                if not hasattr(obj, const):
                    missing.append(const)
            if missing:
                print(f'Error: {missing} variable are not defined to {obj}')
                raise ValueError()
            subclasses.append(obj)
        return subclasses
    except BaseException:
        print(f'ERROR: fail to load plugins: {module_filepath}')
        return []