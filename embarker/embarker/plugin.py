import os
import re
import sys
import uuid
import inspect
import traceback
import importlib.util
from embarker.api import EmbarkerDockWidget, EmbarkerToolBar, EmbarkerMenu


PLUGIN_CLASSES = (EmbarkerToolBar, EmbarkerDockWidget, EmbarkerMenu)


def get_plugin_unique_id(path):
    name = os.path.splitext(os.path.basename(path))[0]
    name = re.sub(r'\W|^(?=\d)', '_', name)
    return f"{name}_{uuid.uuid4().hex}"


def extract_module_available_ui_classes(module_filepath):
    try:
        unique_id = get_plugin_unique_id(module_filepath)
        spec = importlib.util.spec_from_file_location(
            unique_id, module_filepath)
        if spec is None or spec.loader is None:
            raise ImportError()
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        if not hasattr(module, 'PLUGIN_NAME'):
            raise ValueError(
                'PLUGIN_NAME is not defined for '
                f'{os.path.basename(module_filepath)}')

        classes_filter = getattr(module, 'UI_CLASSES', None)
        subclasses = []
        for _, obj in inspect.getmembers(module):
            conditions = (
                inspect.isclass(obj) and
                issubclass(obj, PLUGIN_CLASSES) and
                obj not in PLUGIN_CLASSES)
            conditions = conditions and (
                not classes_filter or obj in classes_filter)
            if not conditions:
                continue
            # Check the constant are implemented
            missing = []
            requirements = get_requirements(obj)
            for const in requirements:
                if not hasattr(obj, const):
                    missing.append(const)
            if missing:
                print(f'Error: {missing} variable are not defined to {obj}')
                raise ValueError()
            subclasses.append(obj)
        return unique_id, module, subclasses
    except BaseException:
        print(f'ERROR: fail to load plugins: {module_filepath}')
        if os.getenv('EMBARKER_DEBUG'):
            print(traceback.format_exc())
        raise


def get_requirements(subcls):
    for cls in PLUGIN_CLASSES:
        if issubclass(subcls, cls):
            return cls.__annotations__.keys()


def unload_plugin(plugin_id):
    for module in sys.modules.copy():
        if plugin_id in module:
            del sys.modules[module]
