import logging

from .base import BaseMailSender, NoProviderSender
from .amazon_ses import AmazonSESSender
from .smtp import SMTPSender

from ..config import MailConfig, MailProvider
from ..model import MailMessage


LOG = logging.getLogger(__name__)


SENDERS = {
    MailProvider.SMTP: SMTPSender(),
    MailProvider.AMAZON_SES: AmazonSESSender(),
    MailProvider.NONE: NoProviderSender(),
}  # type: dict[MailProvider, BaseMailSender]


def get_sender(cfg: MailConfig) -> BaseMailSender:
    if cfg.provider not in SENDERS:
        raise ValueError(f'Unsupported mail provider '
                         f'(no sender available): {cfg.provider}')
    return SENDERS[cfg.provider]


def send(message: MailMessage, cfg: MailConfig):
    if cfg.enabled is False:
        LOG.info('Mail sending is disabled, skipping...')
        return
    sender = get_sender(cfg)
    sender.prepare(cfg)
    sender.send(message)


__all__ = ['get_sender', 'send', 'SENDERS', 'BaseMailSender']
