import pluggy

from .. import consts


def create_manager():
    import dsw.document_worker.plugins.specs as hookspecs

    pm = pluggy.PluginManager(consts.PACKAGE_NAME)
    pm.load_setuptools_entrypoints(consts.PLUGINS_ENTRYPOINT)
    pm.add_hookspecs(hookspecs)
    return pm
