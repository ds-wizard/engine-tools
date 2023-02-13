from typing import Optional


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

    def __init__(self, message_id: str, subject: str, language: str,
                 importance: str, sensitivity: Optional[str],
                 priority: Optional[str]):
        self.id = message_id
        self.subject = subject
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
                 ctx: dict, recipients: list[str]):
        self.id = message_id
        self.template_name = template_name
        self.trigger = trigger
        self.ctx = ctx
        self.recipients = recipients
        self.domain = None  # type: Optional[str]
        self.client_url = ''  # type: str

    @staticmethod
    def load_from_file(data: dict) -> 'MessageRequest':
        return MessageRequest(
            message_id=data['id'],
            template_name=data['type'],
            trigger=data.get('trigger', 'input_file'),
            ctx=data.get('ctx', {}),
            recipients=data.get('recipients', []),
        )


class MailMessage:

    def __init__(self):
        self.from_mail = ''
        self.from_name = ''
        self.recipients = list()
        self.subject = ''
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
