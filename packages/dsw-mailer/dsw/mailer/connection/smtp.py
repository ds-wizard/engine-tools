import logging
import pathvalidate
import smtplib
import ssl
import tenacity

from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr

from dsw.config.model import MailConfig

from ..context import Context
from ..model import MailMessage, MailAttachment


RETRY_SMTP_MULTIPLIER = 0.5
RETRY_SMTP_TRIES = 3
EMAIL_ENCODING = 'utf-8'


class SMTPSender:

    def __init__(self, cfg: MailConfig):
        self.cfg = cfg

    @tenacity.retry(
        reraise=True,
        wait=tenacity.wait_exponential(multiplier=RETRY_SMTP_MULTIPLIER),
        stop=tenacity.stop_after_attempt(RETRY_SMTP_TRIES),
        before=tenacity.before_log(Context.logger, logging.DEBUG),
        after=tenacity.after_log(Context.logger, logging.DEBUG),
    )
    def send(self, message: MailMessage):
        self._send(message)

    def _send(self, mail: MailMessage):
        if self.cfg.is_ssl:
            return self._send_smtp_ssl(mail=mail)
        return self._send_smtp(mail=mail)

    def _send_smtp_ssl(self, mail: MailMessage):
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(
            host=self.cfg.host,
            port=self.cfg.port,
            context=context,
            timeout=self.cfg.timeout,
        ) as server:
            if self.cfg.auth:
                server.login(
                    user=self.cfg.login_user,
                    password=self.cfg.login_password,
                )
            return server.send_message(
                msg=self._convert_email(mail),
                from_addr=formataddr((mail.from_name, mail.from_mail)),
                to_addrs=mail.recipients,
            )

    def _send_smtp(self, mail: MailMessage):
        context = ssl.create_default_context()
        with smtplib.SMTP(
            host=self.cfg.host,
            port=self.cfg.port,
            timeout=self.cfg.timeout,
        ) as server:
            if self.cfg.is_tls:
                server.starttls(context=context)
            if self.cfg.auth:
                server.login(
                    user=self.cfg.login_user,
                    password=self.cfg.login_password,
                )
            return server.send_message(
                msg=self._convert_email(mail),
                from_addr=formataddr((mail.from_name, mail.from_mail)),
                to_addrs=mail.recipients,
            )

    def _convert_inline_image(self, image: MailAttachment) -> MIMEBase:
        mtype, msubtype = image.content_type.split('/', maxsplit=1)
        part = MIMEBase(mtype, msubtype)
        part.set_payload(image.data)
        encoders.encode_base64(part)
        filename = pathvalidate.sanitize_filename(image.name)
        part.add_header('Content-ID', f'<{filename}>')
        part.add_header('Content-Disposition', f'inline; filename={filename}')
        return part

    def _convert_html_part(self, mail: MailMessage) -> MIMEBase:
        if mail.html_body is None:
            raise RuntimeError('Requested HTML body but there is none')
        txt_part = MIMEText(mail.html_body, 'html', EMAIL_ENCODING)
        txt_part.set_charset(EMAIL_ENCODING)
        if len(mail.html_images) > 0:
            part = MIMEMultipart('related')
            part.attach(txt_part)
            for image in mail.html_images:
                part.attach(self._convert_inline_image(image))
            return part
        return txt_part

    def _convert_plain_part(self, mail: MailMessage) -> MIMEText:
        if mail.plain_body is None:
            raise RuntimeError('Requested plain body but there is none')
        return MIMEText(mail.plain_body, 'plain', EMAIL_ENCODING)

    def _convert_txt_parts(self, mail: MailMessage) -> MIMEBase:
        if mail.plain_body is None:
            return self._convert_html_part(mail)
        if mail.html_body is None:
            return self._convert_plain_part(mail)
        part = MIMEMultipart('alternative')
        part.set_charset(EMAIL_ENCODING)
        part.attach(self._convert_plain_part(mail))
        part.attach(self._convert_html_part(mail))
        return part

    def _convert_attachment(self, attachment: MailAttachment) -> MIMEBase:
        mtype, msubtype = attachment.content_type.split('/', maxsplit=1)
        part = MIMEBase(mtype, msubtype)
        part.set_payload(attachment.data)
        encoders.encode_base64(part)
        filename = pathvalidate.sanitize_filename(attachment.name)
        part.add_header('Content-Disposition', f'attachment; filename={filename}')
        return part

    def _convert_email(self, mail: MailMessage) -> MIMEBase:
        msg = self._convert_txt_parts(mail)
        if len(mail.attachments) > 0:
            txt = msg
            msg = MIMEMultipart('mixed')
            msg.attach(txt)
            for attachment in mail.attachments:
                msg.attach(self._convert_attachment(attachment))
        msg['From'] = formataddr((mail.from_name, mail.from_mail))
        msg['To'] = ', '.join(mail.recipients)
        msg['Subject'] = mail.subject
        return msg
