from dsw.config import DSWConfigParser
from dsw.config.keys import ConfigKeys
from dsw.config.model import GeneralConfig, SentryConfig, \
    DatabaseConfig, LoggingConfig, MailConfig


class MailerConfig:

    def __init__(self, db: DatabaseConfig, log: LoggingConfig,
                 mail: MailConfig, sentry: SentryConfig,
                 general: GeneralConfig):
        self.db = db
        self.log = log
        self.mail = mail
        self.sentry = sentry
        self.general = general

    def __str__(self):
        return f'MailerConfig\n' \
               f'====================\n' \
               f'{self.db}' \
               f'{self.log}' \
               f'{self.mail}' \
               f'{self.sentry}' \
               f'{self.general}' \
               f'====================\n'


class MailerConfigParser(DSWConfigParser):

    def __init__(self):
        ConfigKeys.mail.email.required = True
        ConfigKeys.mail.host.required = True
        ConfigKeys.mail.port.required = True
        super().__init__(keys=ConfigKeys)

    @property
    def config(self) -> MailerConfig:
        cfg = MailerConfig(
            db=self.db,
            log=self.logging,
            mail=self.mail,
            sentry=self.sentry,
            general=self.general,
        )
        cfg.mail.load_dkim_privkey()
        return cfg
