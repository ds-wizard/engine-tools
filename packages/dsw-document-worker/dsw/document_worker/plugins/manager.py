import pluggy

from ..consts import PACKAGE_NAME, PLUGINS_ENTRYPOINT


def create_manager():
    # pylint: disable-next=import-outside-toplevel
    import dsw.document_worker.plugins.specs as hookspecs

    pm = pluggy.PluginManager(PACKAGE_NAME)
    pm.load_setuptools_entrypoints(PLUGINS_ENTRYPOINT)
    pm.add_hookspecs(hookspecs)
    return pm
