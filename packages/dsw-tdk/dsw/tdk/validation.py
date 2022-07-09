import re

from typing import List, Dict

from .consts import REGEX_SEMVER, REGEX_ORGANIZATION_ID, \
    REGEX_TEMPLATE_ID, REGEX_MIME_TYPE, REGEX_KM_ID
from .model import PackageFilter, Format, Step


class ValidationError(BaseException):
    def __init__(self, field_name: str, message: str):
        self.field_name = field_name
        self.message = message


def _validate_required(field_name: str, value) -> List[ValidationError]:
    if value is None:
        return [ValidationError(field_name, 'Missing but it is required')]
    return []


def _validate_non_empty(field_name: str, value) -> List[ValidationError]:
    if value is not None and len(value.strip()) == 0:
        return [ValidationError(field_name, 'Cannot be empty or only-whitespace')]
    return []


def _validate_content_type(field_name: str, value) -> List[ValidationError]:
    if value is not None and re.match(REGEX_MIME_TYPE, value) is None:
        return [ValidationError(field_name, 'Content type should be valid IANA media type')]
    return []


def _validate_extension(field_name: str, value) -> List[ValidationError]:
    if value is not None and re.match(REGEX_ORGANIZATION_ID, value) is None:
        return [ValidationError(field_name, 'File extension should contain only letters, numbers and dots (inside-only)')]
    return []


def _validate_organization_id(field_name: str, value) -> List[ValidationError]:
    if value is not None and re.match(REGEX_ORGANIZATION_ID, value) is None:
        return [ValidationError(field_name, 'Organization ID may contain only letters, numbers, and period (inside-only)')]
    return []


def _validate_template_id(field_name: str, value) -> List[ValidationError]:
    if value is not None and re.match(REGEX_TEMPLATE_ID, value) is None:
        return [ValidationError(field_name, 'Template ID may contain only letters, numbers, and dash (inside-only)')]
    return []


def _validate_km_id(field_name: str, value) -> List[ValidationError]:
    if value is not None and re.match(REGEX_KM_ID, value) is None:
        return [ValidationError(field_name, 'KM ID may contain only letters, numbers, and dash (inside-only)')]
    return []


def _validate_version(field_name: str, value) -> List[ValidationError]:
    if value is not None and re.match(REGEX_SEMVER, value) is None:
        return [ValidationError(field_name, 'Version must be in semver format <NUM>.<NUM>.<NUM>')]
    return []


def _validate_natural(field_name: str, value) -> List[ValidationError]:
    if value is not None and (not isinstance(value, int) or value < 1):
        return [ValidationError(field_name, 'Field {field_name} must be positive integer')]
    return []


def _validate_package_id(field_name: str, value: str) -> List[ValidationError]:
    res = []
    if value is None:
        return res
    if not isinstance(value, str):
        return [ValidationError(field_name, 'Package ID is not a string')]
    parts = value.split(':')
    if len(parts) != 3:
        res.append(ValidationError(field_name, 'Package ID is not valid (only {len(parts)} parts)'))
    if re.match(REGEX_ORGANIZATION_ID, parts[0]) is None:
        res.append(ValidationError(field_name, 'Package ID contains invalid organization id'))
    if re.match(REGEX_KM_ID, parts[1]) is None:
        res.append(ValidationError(field_name, 'Package ID contains invalid KM id'))
    if re.match(REGEX_SEMVER, parts[2]) is None:
        res.append(ValidationError(field_name, 'Package ID contains invalid version'))
    return res


def _validate_jinja_options(field_name: str, value: Dict[str, str]) -> List[ValidationError]:
    res = []
    if value is None:
        return res
    for k in ('template', 'content-type', 'extension'):
        if k not in value.keys():
            res.append(ValidationError(field_name, 'Jinja option cannot be left out'))
        elif value[k] is None or not isinstance(value[k], str) or len(value[k]) == 0:
            res.append(ValidationError(field_name, 'Jinja option cannot be empty'))
    if 'content-type' in value.keys():
        res.extend(_validate_content_type(f'{field_name}.content-type', value['content-type']))
    return res


class GenericValidator:

    def __init__(self, rules):
        self.rules = rules

    def validate_field(self, entity, field_name: str):
        for validator in self.rules.get(field_name, []):
            err = validator(field_name, getattr(entity, field_name))
            if len(err) != 0:
                raise err[0]

    def validate(self, entity, field_name_prefix: str = ''):
        for field_name, validators in self.rules.items():
            if field_name.startswith('__'):
                continue
            for validator in validators:
                err = validator(field_name_prefix + field_name, getattr(entity, field_name))
                if len(err) != 0:
                    raise err[0]
        if '__all' in self.rules.keys():
            err = self.rules['__all'](field_name_prefix, entity)
            if len(err) != 0:
                raise err[0]

    def collect_errors(self, entity, field_name_prefix: str = '') -> List[ValidationError]:
        result = []
        for field_name, validators in self.rules.items():
            if field_name.startswith('__'):
                continue
            for validator in validators:
                result.extend(validator(field_name_prefix + field_name, getattr(entity, field_name)))
        if '__all' in self.rules.keys():
            result.extend(self.rules['__all'](field_name_prefix, entity))
        return result


PackageFilterValidator = GenericValidator({
    'organization_id': [_validate_organization_id],
    'km_id': [_validate_km_id],
    'min_version': [_validate_version],
    'max_version': [_validate_version],
})


def _validate_package_filters(field_name: str, value: List[PackageFilter]) -> List[ValidationError]:
    res = []
    for v in value:
        res.extend(PackageFilterValidator.collect_errors(v, field_name_prefix=f'{field_name}.'))
    return res


def _validate_step(field_name_prefix: str, value: Step) -> List[ValidationError]:
    if value.name == 'jinja':
        return _validate_jinja_options(f'{field_name_prefix}options', value.options)
    return []


StepValidator = GenericValidator({
    'name': [_validate_non_empty],
    'options': [],
    '__all': _validate_step
})


def _validate_steps(field_name: str, value: List[Step]) -> List[ValidationError]:
    res = []
    for v in value:
        res.extend(StepValidator.collect_errors(v, field_name_prefix=f'{field_name}.'))
    return res


FormatValidator = GenericValidator({
    'uuid': [_validate_required, _validate_non_empty],
    'name': [_validate_required, _validate_non_empty],
    'short_name': [_validate_required, _validate_non_empty],
    'icon': [_validate_required, _validate_non_empty],
    'color': [_validate_required, _validate_non_empty],
    'steps': [_validate_required, _validate_steps],
})


def _validate_formats(field_name: str, value: List[Format]) -> List[ValidationError]:
    res = []
    uuids = set()
    for v in value:
        if v.uuid in uuids:
            res.append(ValidationError(field_name, f'Duplicate format UUID {v.uuid}'))
        uuids.add(v.uuid)
        res.extend(FormatValidator.collect_errors(v, field_name_prefix=f'{field_name}.'))
    return res


TemplateValidator = GenericValidator({
    'template_id': [_validate_required, _validate_template_id],
    'organization_id': [_validate_required, _validate_organization_id],
    'version': [_validate_required, _validate_version],
    'name': [_validate_required, _validate_non_empty],
    'description': [_validate_required, _validate_non_empty],
    'readme': [_validate_required, _validate_non_empty],
    'recommended_package_id': [_validate_package_id],
    'license': [_validate_required, _validate_non_empty],
    'metamodel_version': [_validate_natural],
    'allowed_packages': [_validate_package_filters],
    'formats': [_validate_required, _validate_formats],
})
