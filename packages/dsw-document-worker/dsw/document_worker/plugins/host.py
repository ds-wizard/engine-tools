import pluggy

from ..consts import PACKAGE_NAME
from . import hookspecs

hookimpl = pluggy.HookimplMarker(PACKAGE_NAME)

def get_plugin_manager():
    pm = pluggy.PluginManager(PACKAGE_NAME)
    pm.add_hookspecs(hookspecs)
    pm.load_setuptools_entrypoints(PACKAGE_NAME)
    # TODO: load local plugins
    return pm
