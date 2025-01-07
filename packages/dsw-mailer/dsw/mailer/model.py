import dataclasses
import os
import re


class Color:
    DEFAULT_PRIMARY_HEX = os.getenv('DEFAULT_PRIMARY_COLOR', '#0033aa')
    DEFAULT_ILLUSTRATIONS_HEX = os.getenv('DEFAULT_ILLUSTRATIONS_COLOR', '#4285f4')

    @staticmethod
    def contrast_ratio(color1: 'Color', color2: 'Color') -> float:
        # https://www.w3.org/TR/WCAG20/#contrast-ratiodef

        l1 = color1.luminance + 0.05
        l2 = color2.luminance + 0.05
        if l1 > l2:
            return l1 / l2
        return l2 / l1

    def __init__(self, color_hex: str = '#000000', default: str = '#000000'):
        color_hex = self.parse_color_to_hex(color_hex) or default
        h = color_hex.lstrip('#')
        self.red, self.green, self.blue = tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

    @staticmethod
    def parse_color_to_hex(color: str) -> str | None:
        color = color.strip()
        if re.match(r'^#[0-9a-fA-F]{6}$', color):
            return color
        if re.match(r'^#[0-9a-fA-F]{3}$', color):
            r = color[1]
            g = color[2]
            b = color[3]
            return f'#{r}{r}{g}{g}{b}{b}'
        return None

    @property
    def hex(self):
        return f'#{self.red:02x}{self.green:02x}{self.blue:02x}'

    @property
    def luminance(self):
        # https://www.w3.org/WAI/GL/wiki/Relative_luminance

        def _luminance_component(component: int):
            c = component / 255
            if c <= 0.03928:
                return c / 12.92
            return ((c + 0.055) / 1.055) ** 2.4

        r = _luminance_component(self.red)
        g = _luminance_component(self.green)
        b = _luminance_component(self.blue)
        return 0.2126 * r + 0.7152 * g + 0.0722 * b

    @property
    def is_dark(self):
        return self.luminance < 0.5

    @property
    def is_light(self):
        return not self.is_dark

    @property
    def contrast_color(self) -> 'Color':
        if self.contrast_ratio(self, Color('#ffffff')) > 3:
            return Color('#ffffff')
        return Color('#000000')

    def __str__(self):
        return self.hex


class StyleConfig:
    _DEFAULT = None

    def __init__(self, logo_url: str | None, primary_color: str,
                 illustrations_color: str):
        self.logo_url = logo_url
        self.primary_color = Color(primary_color, Color.DEFAULT_PRIMARY_HEX)
        self.illustrations_color = Color(illustrations_color, Color.DEFAULT_ILLUSTRATIONS_HEX)

    def from_dict(self, data: dict | None):
        data = data or {}
        if data.get('logoUrl', None) is not None:
            self.logo_url = data.get('logoUrl')
        if data.get('primaryColor', None) is not None:
            self.primary_color = Color(data.get(
                'primaryColor',
                self.default().primary_color.hex
            ), Color.DEFAULT_PRIMARY_HEX)
        if data.get('illustrationsColor', None) is not None:
            self.illustrations_color = Color(data.get(
                'illustrationsColor',
                self.default().illustrations_color.hex,
            ), Color.DEFAULT_ILLUSTRATIONS_HEX)

    @classmethod
    def default(cls):
        if cls._DEFAULT is None:
            cls._DEFAULT = StyleConfig(
                logo_url=None,
                primary_color=Color.DEFAULT_PRIMARY_HEX,
                illustrations_color=Color.DEFAULT_ILLUSTRATIONS_HEX,
            )
        return cls._DEFAULT


class TemplateDescriptorPart:

    DEFAULTS = {
        'html': {
            'name': 'text',
            'content-type': 'text/html',
        },
        'plain': {
            'name': 'text',
            'content-type': 'text/plain'
        },
        '': {
            'name': '',
            'content-type': 'application/octet-stream',
            'encoding': 'utf-8',
        },
    }
    FIELDS = ('name', 'content-type', 'encoding')

    def __init__(self, part_type: str, file: str):
        self.type = part_type
        self.file = file
        self.name = ''
        self.content_type = ''
        self.encoding = ''

    def update_from_data(self, data: dict):
        for field in self.FIELDS:
            target_field = field.replace('-', '_')
            if field in data.keys():
                setattr(self, target_field, data[field])
            elif field in self.DEFAULTS.get(self.type, {}).keys():
                setattr(self, target_field, self.DEFAULTS[self.type][field])
            else:
                setattr(self, target_field, self.DEFAULTS[''][field])

    @staticmethod
    def load_from_file(data: dict) -> 'TemplateDescriptorPart':
        part = TemplateDescriptorPart(
            part_type=data.get('type', 'unknown'),
            file=data.get('file', ''),
        )
        part.update_from_data(data)
        return part


class TemplateDescriptor:

    def __init__(self, *, message_id: str, subject: str, subject_prefix: bool,
                 default_sender_name: str | None, language: str,
                 importance: str, sensitivity: str | None,
                 priority: str | None):
        self.id = message_id
        self.subject = subject
        self.use_subject_prefix = subject_prefix
        self.default_sender_name = default_sender_name
        self.language = language
        self.importance = importance
        self.sensitivity = sensitivity
        self.priority = priority
        self.parts = []  # type: list[TemplateDescriptorPart]
        self.modes = []  # type: list[str]

    @staticmethod
    def load_from_file(data: dict) -> 'TemplateDescriptor':
        result = TemplateDescriptor(
            message_id=data.get('id', ''),
            subject=data.get('subject', ''),
            subject_prefix=data.get('subjectPrefix', True),
            default_sender_name=data.get('defaultSenderName', None),
            language=data.get('language', 'en'),
            importance=data.get('importance', 'normal'),
            sensitivity=data.get('sensitivity', None),
            priority=data.get('priority', None),
        )
        result.parts = [TemplateDescriptorPart.load_from_file(d)
                        for d in data.get('parts', [])]
        result.modes = data.get('modes', [])
        return result


class MessageRequest:

    def __init__(self, *, message_id: str, template_name: str, trigger: str,
                 ctx: dict, recipients: list[str], style: StyleConfig | None = None):
        self.id = message_id
        self.template_name = template_name
        self.trigger = trigger
        self.ctx = ctx
        self.recipients = recipients
        self.domain = None  # type: str | None
        self.client_url = ''  # type: str
        self.style = style or StyleConfig.default()
        self.ctx['style'] = self.style

    @staticmethod
    def load_from_file(data: dict) -> 'MessageRequest':
        return MessageRequest(
            message_id=data['id'],
            template_name=data['type'],
            trigger=data.get('trigger', 'input_file'),
            ctx=data.get('ctx', {}),
            recipients=data.get('recipients', []),
            style=StyleConfig(
                logo_url=data.get('styleLogoUrl', None),
                primary_color=data.get('stylePrimaryColor',
                                       Color.DEFAULT_PRIMARY_HEX),
                illustrations_color=data.get('styleIllustrationsColor',
                                             Color.DEFAULT_ILLUSTRATIONS_HEX),
            ),
        )


@dataclasses.dataclass
class MailMessage:
    from_mail: str = ''
    from_name: str | None = None
    recipients: list[str] = dataclasses.field(default_factory=list)
    subject: str = ''
    plain_body: str | None = None
    html_body: str | None = None
    html_images: list['MailAttachment'] = dataclasses.field(default_factory=list)
    attachments: list['MailAttachment'] = dataclasses.field(default_factory=list)
    msg_id: str | None = None
    msg_domain: str | None = None
    language: str = 'en'
    importance: str = 'normal'
    sensitivity: str | None = None
    priority: str | None = None
    client_url: str = ''


@dataclasses.dataclass
class MailAttachment:
    name: str
    content_type: str
    data: bytes
