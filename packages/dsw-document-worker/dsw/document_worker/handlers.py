import os
import pathlib
import tempfile

from . import consts
from .cli import load_config_str
from .worker import DocumentWorker, SentryReporter


def lambda_handler(event, context):
    config_path = pathlib.Path(os.getenv(consts.VAR_APP_CONFIG_PATH, '/var/task/application.yml'))
    workdir_path = pathlib.Path(os.getenv(consts.VAR_WORKDIR_PATH, '/var/task/templates'))

    with tempfile.TemporaryDirectory() as tmpdir:
        cache_dir = pathlib.Path(tmpdir) / '.cache'
        fontconfig_tmp = cache_dir / 'fontconfig'
        os.environ['XDG_CACHE_HOME'] = cache_dir.as_posix()
        fontconfig_tmp.mkdir(parents=True, exist_ok=True)

        config = load_config_str(config_path.read_text(encoding=consts.DEFAULT_ENCODING))
        try:
            doc_worker = DocumentWorker(config, workdir_path)
            doc_worker.run_once()
        except Exception as e:
            SentryReporter.capture_exception(e)
            raise
