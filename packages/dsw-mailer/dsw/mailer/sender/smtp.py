import logging
import smtplib
import ssl

from email.utils import formataddr

import tenacity

from .base import BaseMailSender
from ..config import MailConfig
from ..model import MailMessage


RETRY_SMTP_MULTIPLIER = 0.5
RETRY_SMTP_TRIES = 3
LOG = logging.getLogger(__name__)


class SMTPSender(BaseMailSender):

    @staticmethod
    def validate_config(cfg: MailConfig):
        if not cfg.smtp.host:
            raise ValueError('Missing host for SMTP')
        if not cfg.smtp.port:
            raise ValueError('Missing port for SMTP')

    @tenacity.retry(
        reraise=True,
        wait=tenacity.wait_exponential(multiplier=RETRY_SMTP_MULTIPLIER),
        stop=tenacity.stop_after_attempt(RETRY_SMTP_TRIES),
        before=tenacity.before_log(LOG, logging.DEBUG),
        after=tenacity.after_log(LOG, logging.DEBUG),
    )
    def send(self, message: MailMessage):
        LOG.info('Sending via SMTP (server %s:%s)',
                 self.cfg.smtp.host, self.cfg.smtp.port)
        if self.cfg.smtp.is_ssl:
            self._send_smtp_ssl(mail=message)
        else:
            self._send_smtp(mail=message)

    def _send_smtp_ssl(self, mail: MailMessage):
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(
            host=self.cfg.smtp.host or 'localhost',
            port=self.cfg.smtp.port,
            context=context,
            timeout=self.cfg.smtp.timeout,
        ) as server:
            if self.cfg.smtp.auth:
                server.login(
                    user=self.cfg.smtp.login_user,
                    password=self.cfg.smtp.login_password,
                )
            return server.send_message(
                msg=self._convert_email(mail),
                from_addr=formataddr((mail.from_name, mail.from_mail)),
                to_addrs=mail.recipients,
            )

    def _send_smtp(self, mail: MailMessage):
        context = ssl.create_default_context()
        with smtplib.SMTP(
            host=self.cfg.smtp.host or 'localhost',
            port=self.cfg.smtp.port,
            timeout=self.cfg.smtp.timeout,
        ) as server:
            if self.cfg.smtp.is_tls:
                server.starttls(context=context)
            if self.cfg.smtp.auth:
                server.login(
                    user=self.cfg.smtp.login_user,
                    password=self.cfg.smtp.login_password,
                )
            return server.send_message(
                msg=self._convert_email(mail),
                from_addr=formataddr((mail.from_name, mail.from_mail)),
                to_addrs=mail.recipients,
            )
