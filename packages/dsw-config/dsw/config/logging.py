import logging
import logging.config
import sys


class DSWLogFilter(logging.Filter):

    def __init__(self, extras=None):
        super().__init__()
        self.extras = extras or {'traceId': ''}

    def set_extra(self, key: str, value: str):
        self.extras[key] = value

    def filter(self, record: logging.LogRecord):
        record.__dict__.update(self.extras)
        return True


LOG_FILTER = DSWLogFilter()


class DSWLogger(logging.Logger):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.addFilter(LOG_FILTER)


def prepare_logging(logging_cfg):
    # pylint: disable-next=no-member
    logger_dict = logging.root.manager.loggerDict
    if logging_cfg.dict_config is not None:
        logging.config.dictConfig(logging_cfg.dict_config)
    else:
        logging.basicConfig(
            stream=sys.stdout,
            level=logging_cfg.global_level,
            format=logging_cfg.message_format
        )
        dsw_loggers = (logging.getLogger(name) for name in logger_dict
                       if name.lower().startswith('dsw'))
        for logger in dsw_loggers:
            logger.setLevel(logging_cfg.level)
    # Set for all existing loggers
    logging.getLogger().addFilter(filter=LOG_FILTER)
    loggers = (logging.getLogger(name) for name in logger_dict)
    for logger in loggers:
        logger.addFilter(filter=LOG_FILTER)
    # Set for any future loggers
    logging.setLoggerClass(DSWLogger)
