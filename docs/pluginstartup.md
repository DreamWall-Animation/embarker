
# Customize startup

Embarker offers multiple ways to customize startup, as some studios need to
configure it per project. The same installation can be used in different contexts.

## Place Python module in the Plug-ins folder

The simplest way to add a Python plugin is to place the module in the "plugins" folder next to the Embarker executable. This only works if you are using a build and not running the software directly in a Python interpreter. This method is straightforward; however, it is **not recommended** if you want to configure the plugins dynamically depending on the project you are working on.

## Use launcher command argument

The executable can be run with an argument: `--plugins`, allowing you to define a list of Python modules.

```command
embarker.exe --python_plugins c:/my_plugins/plugin1.py c:/my_plugins/plugin2.py
```

## Use environment variable

You can use the environment variable `EMBARKER_PLUGIN_PATHS` to add plugins.
The value must be a list of paths separated by a `;`.

