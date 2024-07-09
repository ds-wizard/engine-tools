import logging

import boto3

from .base import BaseMailSender
from ..config import MailConfig
from ..model import MailMessage


LOG = logging.getLogger(__name__)


class AmazonSESSender(BaseMailSender):

    @staticmethod
    def validate_config(cfg: MailConfig):
        if not cfg.amazon_ses.has_credentials():
            raise ValueError('Missing credentials for Amazon SES')
        if not cfg.amazon_ses.region:
            raise ValueError('Missing region for Amazon SES')

    def send(self, message: MailMessage):
        LOG.info('Sending via Amazon SES (region %s)',
                 self.cfg.amazon_ses.region)
        self._send(message, self.cfg)

    def _send(self, mail: MailMessage, cfg: MailConfig):
        ses = boto3.client(
            'ses',
            region_name=cfg.amazon_ses.region,
            aws_access_key_id=cfg.amazon_ses.access_key_id,
            aws_secret_access_key=cfg.amazon_ses.secret_access_key,
        )
        msg = self._convert_email(mail)
        return ses.send_raw_email(
            Source=mail.from_mail,
            Destinations=mail.recipients,
            RawMessage={
                'Data': msg.as_string().encode('us-ascii'),
            },
        )
