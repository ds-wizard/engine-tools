from typing import Optional


class Color:

    def __init__(self, color_hex: str = '#000000'):
        h = color_hex.lstrip('#')
        self.red, self.green, self.blue = tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

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
            else:
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
        return Color('#ffffff') if self.is_dark else Color('#000000')

    def __str__(self):
        return self.hex


class StyleConfig:
    _DEFAULT = None

    def __init__(self, logo_url: Optional[str], primary_color: str,
                 illustration_color: str):
        self.logo_url = logo_url
        self.primary_color = Color(primary_color)
        self.illustration_color = Color(illustration_color)

    def from_dict(self, data: dict):
        if data.get('logoUrl', None) is not None:
            self.logo_url = data.get('logoUrl')
        if data.get('primaryColor', None) is not None:
            self.primary_color = Color(data.get(
                'primaryColor',
                self.default().primary_color.hex
            ))
        if data.get('illustrationColor', None) is not None:
            self.illustration_color = Color(data.get(
                'illustrationColor',
                self.default().illustration_color.hex,
            ))

    @classmethod
    def default(cls):
        if cls._DEFAULT is None:
            cls._DEFAULT = StyleConfig(
                logo_url=None,
                primary_color='#0033aa',
                illustration_color='#4285f4',
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

    def _update_from_data(self, data: dict):
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
        part._update_from_data(data)
        return part


class TemplateDescriptor:

    def __init__(self, message_id: str, subject: str, subject_prefix: bool,
                 default_sender_name: Optional[str], language: str,
                 importance: str, sensitivity: Optional[str],
                 priority: Optional[str]):
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

    def __init__(self, message_id: str, template_name: str, trigger: str,
                 ctx: dict, recipients: list[str], style: Optional[StyleConfig] = None):
        self.id = message_id
        self.template_name = template_name
        self.trigger = trigger
        self.ctx = ctx
        self.recipients = recipients
        self.domain = None  # type: Optional[str]
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
                primary_color=data.get('stylePrimaryColor', '#019AD6'),
                illustration_color=data.get('styleIllustrationColor', '#019AD6'),
            ),
        )


class MailMessage:

    def __init__(self):
        self.from_mail = ''  # type: str
        self.from_name = None  # type: Optional[str]
        self.recipients = list()  # type: list[str]
        self.subject = ''  # type: str
        self.plain_body = None  # type: Optional[str]
        self.html_body = None  # type: Optional[str]
        self.html_images = list()  # type: list[MailAttachment]
        self.attachments = list()  # type: list[MailAttachment]
        self.msg_id = None  # type: Optional[str]
        self.msg_domain = None  # type: Optional[str]
        self.language = 'en'  # type: str
        self.importance = 'normal'  # type: str
        self.sensitivity = None  # type: Optional[str]
        self.priority = None  # type: Optional[str]
        self.client_url = ''  # type: str


class MailAttachment:

    def __init__(self, name='', content_type='', data=''):
        self.name = name
        self.content_type = content_type
        self.data = data
