import abc
import datetime
import logging

from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr, format_datetime, make_msgid

import pathvalidate

from ..config import MailConfig
from ..consts import DEFAULT_ENCODING
from ..model import MailMessage, MailAttachment


LOG = logging.getLogger(__name__)


class BaseMailSender(abc.ABC):

    def __init__(self):
        self._cfg = None  # type: MailConfig | None

    @property
    def cfg(self) -> MailConfig:
        if self._cfg is None:
            raise RuntimeError('Mail sender not prepared')
        return self._cfg

    def prepare(self, cfg: MailConfig):
        self.validate_config(cfg)
        self._cfg = cfg

    @staticmethod
    @abc.abstractmethod
    def validate_config(cfg: MailConfig):
        pass

    @abc.abstractmethod
    def send(self, message: MailMessage):
        ...

    def _convert_email(self, mail: MailMessage) -> MIMEBase:
        msg = self._convert_txt_parts(mail)
        if len(mail.attachments) > 0:
            txt = msg
            msg = MIMEMultipart('mixed')
            msg.attach(txt)
            for attachment in mail.attachments:
                msg.attach(self._convert_attachment(attachment))

        headers = []  # type: list[bytes]

        def add_header(name: str, value: str):
            msg.add_header(name, value)
            headers.append(name.encode(encoding=DEFAULT_ENCODING))

        add_header('From', formataddr((mail.from_name, mail.from_mail)))
        add_header('To', ', '.join(mail.recipients))
        add_header('Subject', mail.subject)
        add_header('Date', format_datetime(dt=datetime.datetime.now(tz=datetime.UTC)))
        add_header('Message-ID', make_msgid(idstring=mail.msg_id, domain=mail.msg_domain))
        add_header('Language', mail.language)
        add_header('Importance', mail.importance)
        add_header('List-Unsubscribe', f'{mail.client_url}/users/edit/current')
        if mail.sensitivity is not None:
            add_header('Sensitivity', mail.sensitivity)
        if mail.priority is not None:
            add_header('Priority', mail.priority)

        if self.cfg.dkim_selector and self.cfg.dkim_privkey:
            # pylint: disable=import-outside-toplevel
            import dkim  # type: ignore

            sender_domain = mail.from_mail.split('@')[-1]
            signature = dkim.sign(
                message=msg.as_bytes(),
                selector=self.cfg.dkim_selector.encode(),
                domain=sender_domain.encode(),
                privkey=self.cfg.dkim_privkey,
                include_headers=headers,
            ).decode()
            if signature.startswith('DKIM-Signature: '):
                signature = signature[len('DKIM-Signature: '):]
            msg.add_header('DKIM-Signature', signature)

        return msg

    @staticmethod
    def _convert_inline_image(image: MailAttachment) -> MIMEBase:
        mime_type, mime_subtype = image.content_type.split('/', maxsplit=1)
        part = MIMEBase(mime_type, mime_subtype)
        part.set_payload(image.data)
        encoders.encode_base64(part)
        filename = pathvalidate.sanitize_filename(image.name)
        part.add_header('Content-ID', f'<{filename}>')
        part.add_header('Content-Disposition', f'inline; filename={filename}')
        return part

    @classmethod
    def _convert_html_part(cls, mail: MailMessage) -> MIMEBase:
        if mail.html_body is None:
            raise RuntimeError('Requested HTML body but there is none')
        txt_part = MIMEText(mail.html_body, 'html', DEFAULT_ENCODING)
        txt_part.set_charset(DEFAULT_ENCODING)
        if len(mail.html_images) > 0:
            part = MIMEMultipart('related')
            part.attach(txt_part)
            for image in mail.html_images:
                part.attach(cls._convert_inline_image(image))
            return part
        return txt_part

    @staticmethod
    def _convert_plain_part(mail: MailMessage) -> MIMEText:
        if mail.plain_body is None:
            raise RuntimeError('Requested plain body but there is none')
        return MIMEText(mail.plain_body, 'plain', DEFAULT_ENCODING)

    @classmethod
    def _convert_txt_parts(cls, mail: MailMessage) -> MIMEBase:
        if mail.plain_body is None:
            return cls._convert_html_part(mail)
        if mail.html_body is None:
            return cls._convert_plain_part(mail)
        part = MIMEMultipart('alternative')
        part.set_charset(DEFAULT_ENCODING)
        part.attach(cls._convert_plain_part(mail))
        part.attach(cls._convert_html_part(mail))
        return part

    @staticmethod
    def _convert_attachment(attachment: MailAttachment) -> MIMEBase:
        mime_type, mime_subtype = attachment.content_type.split('/', maxsplit=1)
        part = MIMEBase(mime_type, mime_subtype)
        part.set_payload(attachment.data)
        encoders.encode_base64(part)
        filename = pathvalidate.sanitize_filename(attachment.name)
        part.add_header('Content-Disposition', f'attachment; filename={filename}')
        return part


class NoProviderSender(BaseMailSender):

    @staticmethod
    def validate_config(cfg: MailConfig):
        pass

    def send(self, message: MailMessage):
        LOG.info('No provider configured, not sending anything')
