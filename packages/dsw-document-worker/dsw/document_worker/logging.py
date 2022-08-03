import logging

from typing import Any, Dict

from .consts import LOGGER_NAME


class DocWorkerLogFilter(logging.Filter):
    def filter(self, record):
        if not hasattr(record, 'traceId'):
            record.traceId = '-'
        if not hasattr(record, 'documentId'):
            record.traceId = '-'
        return True


class DocWorkerLogger(logging.Logger):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.addFilter(DocWorkerLogFilter())


class _DocWorkerLoggerWrapper(logging.Logger):

    ATTR_MAP = {
        'trace_id': 'traceId',
        'document_id': 'documentId',
    }

    def __init__(self, trace_id: str, document_id: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._extra = dict()  # type: Dict[str, Any]
        self._logger = logging.getLogger(LOGGER_NAME)
        self.trace_id = trace_id
        self.document_id = document_id

    def __setattr__(self, name: str, value: Any):
        if name in self.ATTR_MAP.keys():
            self._extra[self.ATTR_MAP[name]] = value
        else:
            super().__setattr__(name, value)

    def __getattr__(self, name: str):
        if name in self.ATTR_MAP.keys():
            return self._extra[self.ATTR_MAP[name]]
        else:
            return super().__getattribute__(name)

    def _xlog(self, level: int, message: object, **kwargs):
        self._logger.log(level=level, msg=message, extra=self._extra, **kwargs)

    def log(self, *args, **kwargs):
        self._logger.log(*args, extra=self._extra, **kwargs)

    def debug(self, msg: object, *args, **kwargs):
        self._xlog(level=logging.DEBUG, message=msg, **kwargs)

    def info(self, msg: object, *args, **kwargs):
        self._xlog(level=logging.INFO, message=msg, **kwargs)

    def warning(self, msg: object, *args, **kwargs):
        self._xlog(level=logging.WARNING, message=msg, **kwargs)

    def error(self, msg: object, *args, **kwargs):
        self._xlog(level=logging.ERROR, message=msg, **kwargs)

    def set_level(self, level: str):
        self._logger.setLevel(level)


LOGGER = _DocWorkerLoggerWrapper(
    trace_id='-',
    document_id='-',
    name=f'{LOGGER_NAME}_WRAP',
)
