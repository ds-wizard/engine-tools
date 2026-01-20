import datetime
import gettext
import json
import logging
import pathlib
import re
import tempfile

import dateutil.parser
import jinja2
import jinja2.sandbox
import markdown
import markupsafe
import polib

from .config import MailerConfig, MailConfig
from .consts import DEFAULT_ENCODING
from .model import MailMessage, MailAttachment, MessageRequest, \
    TemplateDescriptor, TemplateDescriptorPart


LOG = logging.getLogger(__name__)


class MailTemplate:

    def __init__(self, *, name: str, descriptor: TemplateDescriptor,
                 subject_template: jinja2.Template,
                 html_template: jinja2.Template | None,
                 plain_template: jinja2.Template | None):
        self.name = name
        self.descriptor = descriptor
        self.html_template = html_template
        self.plain_template = plain_template
        self.subject_template = subject_template
        self.attachments: list[MailAttachment] = []
        self.html_images: list[MailAttachment] = []

    def render(self, rq: MessageRequest, mail_name: str | None, mail_from: str) -> MailMessage:
        ctx = rq.ctx
        msg = MailMessage()
        msg.recipients = [r.email for r in rq.recipients]

        subject = self.subject_template.render()

        if self.descriptor.use_subject_prefix:
            subject_prefix = ctx.get('appTitle', None) or mail_name
            if subject_prefix is None:
                subject_prefix = self.descriptor.default_sender_name
            ctx['appTitle'] = subject_prefix
            msg.subject = f'{subject_prefix}: {subject}'
        else:
            msg.subject = subject
        msg.msg_id = rq.id
        msg.msg_domain = rq.domain
        msg.language = self.descriptor.language
        msg.importance = self.descriptor.importance
        msg.priority = self.descriptor.priority
        ctx = self._enhance_contxt(ctx, msg)
        msg.from_mail = mail_from
        msg.from_name = mail_name or self.descriptor.default_sender_name
        if self.html_template is not None:
            msg.html_body = self.html_template.render(ctx=ctx)
        if self.plain_template is not None:
            msg.plain_body = self.plain_template.render(ctx=ctx)
        msg.attachments = self.attachments
        msg.html_images = self.html_images
        return msg

    @staticmethod
    def _enhance_contxt(ctx: dict, msg: MailMessage) -> dict:
        if '_meta' not in ctx:
            ctx['_meta'] = {}
        ctx['_meta']['subject'] = msg.subject
        if 'clientUrl' in ctx:
            # Remove trailing slash if any
            ctx['clientUrl'] = ctx['clientUrl'].rstrip('/')
        return ctx


class TemplateRegistry:

    DESCRIPTOR_FILENAME = 'message.json'
    DESCRIPTOR_PATTERN = f'./**/{DESCRIPTOR_FILENAME}'
    DEFAULT_LOCALE = '~:default:1.0.0'

    def __init__(self, cfg: MailerConfig, workdir: pathlib.Path):
        self.cfg = cfg
        self.workdir = workdir
        self.j2_env = jinja2.sandbox.SandboxedEnvironment(
            loader=jinja2.FileSystemLoader(searchpath=workdir),
            extensions=[
                'jinja2.ext.do',
                'jinja2.ext.i18n',
            ],
        )
        self.templates: dict[str, MailTemplate] = {}
        self._set_filters()
        self._load_templates()

    def _set_filters(self):
        self.j2_env.filters.update({
            'datetime_format': datetime_format,
            'markdown': render_markdown,
            'no_markdown': remove_markdown,
        })

    def _load_jinja2(self, file_path: pathlib.Path) -> jinja2.Template | None:
        if file_path.exists() and file_path.is_file():
            return self.j2_env.get_template(
                name=str(file_path.relative_to(self.workdir).as_posix()),
            )
        return None

    def _make_str_jinja2(self, str_template: str) -> jinja2.Template:
        return self.j2_env.from_string(str_template)

    @staticmethod
    def _load_attachment(template_path: pathlib.Path,
                         part: TemplateDescriptorPart) -> MailAttachment | None:
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
    def _load_descriptor(path: pathlib.Path) -> TemplateDescriptor | None:
        if not path.exists() or not path.is_file():
            return None
        try:
            data = json.loads(path.read_text(encoding=DEFAULT_ENCODING))
            return TemplateDescriptor.load_from_file(data)
        except Exception as e:
            LOG.warning('Cannot load template descriptor at %s: %s',
                        path.as_posix(), str(e))
            return None

    def _load_template(self, path: pathlib.Path,
                       descriptor: TemplateDescriptor) -> MailTemplate | None:
        html_template = None
        plain_template = None
        subject_template = self._make_str_jinja2(
            str_template='{% trans %}' + descriptor.subject + '{% endtrans %}'
        )
        attachments = []
        html_images = []
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
            LOG.warning('Template "%s" from %s has no HTML nor Plain part - skipping',
                        descriptor.id, path.as_posix())
            return None
        template = MailTemplate(
            name=path.name,
            html_template=html_template,
            plain_template=plain_template,
            subject_template=subject_template,
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
            LOG.info('Loaded template "%s" from %s',
                     descriptor.id, path.as_posix())
            self.templates[descriptor.id] = template

    def _uninstall_translations(self):
        if hasattr(self.j2_env, 'uninstall_gettext_translations'):
            # pylint: disable-next=no-member
            self.j2_env.uninstall_gettext_translations('default')

    def _install_null_translations(self):
        if hasattr(self.j2_env, 'install_null_translations'):
            # pylint: disable-next=no-member
            self.j2_env.install_null_translations()

    def _install_translations(self, translations: gettext.GNUTranslations):
        if hasattr(self.j2_env, 'install_gettext_translations'):
            # pylint: disable-next=no-member
            self.j2_env.install_gettext_translations(translations)

    def _load_locale(self, tenant_uuid: str, locale_uuid: str | None, app_ctx,
                     locale_root_dir: pathlib.Path):
        LOG.info('Loading locale: %s (for tenant %s)', locale_uuid, tenant_uuid)
        self._uninstall_translations()
        if locale_uuid is None:
            LOG.info('No locale specified - using null translations')
            self._install_null_translations()
        else:
            # fetch locale from DB
            locale = app_ctx.db.get_locale(
                tenant_uuid=tenant_uuid,
                locale_uuid=locale_uuid,
            )
            if locale.id == self.DEFAULT_LOCALE:
                LOG.info('Locale is default locale - using null translations')
                self._install_null_translations()
                return
            if locale is None:
                LOG.error('Could not find locale for tenant %s', tenant_uuid)
                raise RuntimeError(f'Locale not found in DB: {locale_uuid}')
            # fetch locale from S3
            locale_dir = locale_root_dir / locale.code / 'LC_MESSAGES'
            locale_dir.mkdir(parents=True, exist_ok=True)
            locale_po_path = locale_dir / 'default.po'
            locale_mo_path = locale_dir / 'default.mo'
            downloaded = app_ctx.s3.download_locale(
                tenant_uuid=tenant_uuid,
                locale_uuid=locale_uuid,
                file_name='mail.po',
                target_path=locale_po_path,
            )
            if not downloaded:
                LOG.error('Cannot download locale file (mail.po) from %s to %s',
                          locale_uuid, locale_po_path)
                raise RuntimeError(f'Failed to download locale file (mail.po) from {locale_uuid}')
            LOG.debug('Saved PO file to %s', locale_po_path)
            # convert po to mo
            po = polib.pofile(locale_po_path.absolute().as_posix())
            po.save_as_mofile(locale_mo_path.absolute().as_posix())
            LOG.debug('Converted PO file to MO file: %s', locale_mo_path)
            # load translations
            translations = gettext.translation(
                domain='default',
                localedir=locale_root_dir,
                languages=[locale.code],
            )
            self._install_translations(translations)

    def has_template_for(self, rq: MessageRequest) -> bool:
        return rq.template_name in self.templates

    def render(self, rq: MessageRequest, cfg: MailConfig, app_ctx) -> MailMessage:
        used_cfg = cfg or self.cfg.mail
        with tempfile.TemporaryDirectory() as tmpdir:
            try:
                locale_root_dir = pathlib.Path(tmpdir) / 'locale'
                self._load_locale(rq.tenant_uuid, rq.locale_uuid, app_ctx, locale_root_dir)
            except Exception as e:
                LOG.warning('Cannot load locale for tenant %s: %s', rq.tenant_uuid, str(e))
                LOG.warning('Rendering without locale')
                self._uninstall_translations()
                self._install_null_translations()
            return self.templates[rq.template_name].render(
                rq=rq,
                mail_name=used_cfg.name,
                mail_from=used_cfg.email,
            )


def datetime_format(iso_timestamp: None | datetime.datetime | str, fmt: str):
    if iso_timestamp is None:
        return ''
    if not isinstance(iso_timestamp, datetime.datetime):
        iso_timestamp = dateutil.parser.isoparse(iso_timestamp)
    return iso_timestamp.strftime(fmt)


class DSWMarkdownExt(markdown.extensions.Extension):
    def extendMarkdown(self, md):
        md.preprocessors.register(DSWMarkdownProcessor(md), 'dsw_markdown', 27)
        md.registerExtension(self)


class DSWMarkdownProcessor(markdown.preprocessors.Preprocessor):

    LI_RE = re.compile(r'^[ ]*((\d+\.)|[*+-])[ ]+.*')

    def __init__(self, md):
        super().__init__(md)

    def run(self, lines):
        prev_li = False
        new_lines = []

        for line in lines:
            # Add line break before the first list item
            if self.LI_RE.match(line):
                if not prev_li:
                    new_lines.append('')
                prev_li = True
            elif line == '':
                prev_li = False

            # Replace trailing un-escaped backslash with (supported) two spaces
            _line = line.rstrip('\\')
            if line[-1:] == '\\' and (len(line) - len(_line)) % 2 == 1:
                new_lines.append(f'{line[:-1]}  ')
                continue

            new_lines.append(line)

        return new_lines


def render_markdown(md_text: str):
    if md_text is None:
        return ''
    return markupsafe.Markup(markdown.markdown(
        text=md_text,
        extensions=[
            DSWMarkdownExt(),
        ]
    ))


def remove_markdown(md_text: str):
    if md_text is None:
        return ''
    return re.sub(r'<[^>]*>', '', markdown.markdown(
        text=md_text,
        extensions=[
            DSWMarkdownExt(),
        ]
    ))
