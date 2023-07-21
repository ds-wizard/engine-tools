import jinja2
import json
import logging
import pathlib

from typing import Optional

from .config import MailerConfig, MailConfig
from .consts import DEFAULT_ENCODING
from .model import MailMessage, MailAttachment, MessageRequest,\
    TemplateDescriptor, TemplateDescriptorPart


LOG = logging.getLogger(__name__)


class MailTemplate:

    def __init__(self, name: str, descriptor: TemplateDescriptor,
                 html_template: Optional[jinja2.Template],
                 plain_template: Optional[jinja2.Template]):
        self.name = name
        self.descriptor = descriptor
        self.html_template = html_template
        self.plain_template = plain_template
        self.attachments = list()  # type: list[MailAttachment]
        self.html_images = list()  # type: list[MailAttachment]

    def render(self, rq: MessageRequest, mail_name: Optional[str], mail_from: str) -> MailMessage:
        ctx = rq.ctx
        msg = MailMessage()
        msg.recipients = rq.recipients
        if self.descriptor.use_subject_prefix:
            subject_prefix = ctx.get('appTitle', None) or mail_name
            if subject_prefix is None:
                subject_prefix = self.descriptor.default_sender_name
            ctx['appTitle'] = subject_prefix
            msg.subject = f'{subject_prefix}: {self.descriptor.subject}'
        else:
            msg.subject = self.descriptor.subject
        msg.msg_id = rq.id
        msg.msg_domain = rq.domain
        msg.language = self.descriptor.language
        msg.importance = self.descriptor.importance
        msg.priority = self.descriptor.priority
        ctx['_meta']['subject'] = msg.subject
        msg.from_mail = mail_from
        msg.from_name = mail_name or self.descriptor.default_sender_name
        if self.html_template is not None:
            msg.html_body = self.html_template.render(ctx=ctx)
        if self.plain_template is not None:
            msg.plain_body = self.plain_template.render(ctx=ctx)
        msg.attachments = self.attachments
        msg.html_images = self.html_images
        return msg


class TemplateRegistry:

    DESCRIPTOR_FILENAME = 'message.json'
    DESCRIPTOR_PATTERN = f'./**/{DESCRIPTOR_FILENAME}'

    def __init__(self, cfg: MailerConfig, workdir: pathlib.Path):
        self.cfg = cfg
        self.workdir = workdir
        self.j2_env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(searchpath=workdir),
            extensions=['jinja2.ext.do'],
        )
        self.templates = dict()  # type: dict[str, MailTemplate]
        self._load_templates()

    def _load_jinja2(self, file_path: pathlib.Path) -> Optional[jinja2.Template]:
        if file_path.exists() and file_path.is_file():
            return self.j2_env.get_template(
                name=str(file_path.relative_to(self.workdir).as_posix()),
            )
        return None

    @staticmethod
    def _load_attachment(template_path: pathlib.Path,
                         part: TemplateDescriptorPart) -> Optional[MailAttachment]:
        file_path = template_path / part.file
        if file_path.exists() and file_path.is_file():
            binary_data = file_path.read_bytes()
            return MailAttachment(
                name=part.name,
                content_type=part.content_type,
                data=binary_data,
            )
        return None

    @staticmethod
    def _load_descriptor(path: pathlib.Path) -> Optional[TemplateDescriptor]:
        if not path.exists() or not path.is_file():
            return None
        try:
            data = json.loads(path.read_text(encoding=DEFAULT_ENCODING))
            return TemplateDescriptor.load_from_file(data)
        except Exception as e:
            LOG.warning(f'Cannot load template descriptor at {str(path)}'
                        f'due to: {str(e)}')
            return None

    def _load_template(self, path: pathlib.Path,
                       descriptor: TemplateDescriptor) -> Optional[MailTemplate]:
        html_template = None
        plain_template = None
        attachments = list()
        html_images = list()
        for part in descriptor.parts:
            if part.type == 'html':
                html_template = self._load_jinja2(path / part.file)
            elif part.type == 'plain':
                plain_template = self._load_jinja2(path / part.file)
            elif part.type == 'attachment':
                attachments.append(self._load_attachment(path, part))
            elif part.type == 'html_image':
                html_images.append(self._load_attachment(path, part))
        if html_template is None and plain_template is None:
            LOG.warning(f'Template "{descriptor.id}" from {str(path)}'
                        f'does not have HTML nor Plain part - skipping')
            return None
        template = MailTemplate(
            name=path.name,
            html_template=html_template,
            plain_template=plain_template,
            descriptor=descriptor,
        )
        template.attachments = [a for a in attachments if a is not None]
        template.html_images = [a for a in html_images if a is not None]
        return template

    def _load_templates(self):
        for descriptor_filename in self.workdir.glob(self.DESCRIPTOR_PATTERN):
            path = descriptor_filename.parent
            descriptor = self._load_descriptor(descriptor_filename)
            if descriptor is None:
                continue
            template = self._load_template(path, descriptor)
            if template is None:
                continue
            LOG.info(f'Loaded template "{descriptor.id}" from {str(path)}')
            self.templates[descriptor.id] = template

    def has_template_for(self, rq: MessageRequest) -> bool:
        return rq.template_name in self.templates.keys()

    def render(self, rq: MessageRequest, cfg: MailConfig) -> MailMessage:
        used_cfg = cfg or self.cfg.mail
        return self.templates[rq.template_name].render(
            rq=rq,
            mail_name=used_cfg.name,
            mail_from=used_cfg.email,
        )
