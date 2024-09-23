import pluggy

from ..consts import PACKAGE_NAME
from ..templates.steps import Step


hookspec = pluggy.HookspecMarker(PACKAGE_NAME)


class PluginInfo:

    def __init__(self, name, version):
        self.name = name
        self.version = version


@hookspec
def document_worker_steps() -> list[Step]:
    pass

@hookspec
def document_worker_jinja_tests() -> dict:
    pass

@hookspec
def document_worker_jinja_filters() -> dict:
    pass

@hookspec
def document_worker_plugin_info() -> PluginInfo:
    pass
