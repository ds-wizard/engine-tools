"""JSON Schemas of the wire models.

The schema files themselves live in the separate schemas repository; this module generates them::

    from dsw.models import schemas

    schemas.knowledge_model_bundle_schema(schema_id='https://…/kmp_schema_v20.json')

Every schema is JSON Schema 2020-12, uses the JSON (camelCase) field names, forbids unknown keys
and names the metamodel version in ``$comment``. ``mode='validation'`` (default) describes what
the models accept; ``mode='serialization'`` what they produce (fields with defaults required).
"""
from __future__ import annotations

import copy
import typing
import warnings

import pydantic
from pydantic.json_schema import GenerateJsonSchema, PydanticJsonSchemaWarning

from .document_context.wire import DocumentContext
from .document_template.metadata import DocumentTemplateBundle, DocumentTemplateMetadata
from .errors import ModelsError
from .knowledge_model import flat, tree
from .knowledge_model.package import KnowledgeModelBundle
from .project.events import AnyProjectEvent
from .versions import DOCUMENT_TEMPLATE_METAMODEL_VERSION, KM_METAMODEL_VERSION


JsonSchema = dict[str, typing.Any]
Mode = typing.Literal['validation', 'serialization']

DIALECT = 'https://json-schema.org/draft/2020-12/schema'

#: definitions inlined at every use instead of being named (generic helper types)
_INLINED_DEFINITIONS = ('EditEventField',)


class SchemaError(ModelsError):
    """A schema cannot be generated cleanly."""


class _Generator(GenerateJsonSchema):

    def model_schema(self, schema: typing.Any) -> JsonSchema:
        json_schema = super().model_schema(schema)
        if json_schema.get('additionalProperties') is True:
            # models accept unknown keys only to drop them when asked to; they are not allowed
            json_schema['additionalProperties'] = False
        return json_schema

    def field_title_should_be_set(self, schema: typing.Any) -> bool:
        return False


def knowledge_model_bundle_schema(*, schema_id: str | None = None,
                                  mode: Mode = 'validation') -> JsonSchema:
    """``.km`` bundle with packages and events."""
    return _generate(KnowledgeModelBundle, title='Knowledge Model Bundle',
                     comment=f'Knowledge model metamodel version {KM_METAMODEL_VERSION}',
                     schema_id=schema_id, mode=mode)


def knowledge_model_schema(representation: typing.Literal['flat', 'tree'] = 'flat', *,
                           compact: bool = False, schema_id: str | None = None,
                           mode: Mode = 'validation') -> JsonSchema:
    """Compiled knowledge model (``flat``) or the nested authoring model (``tree``).

    ``compact=True`` leaves out titles, defaults and discriminator mappings: a smaller schema
    that stays valid for the same documents. Tree documents convert to the flat model with
    :func:`dsw.models.knowledge_model.convert.tree_to_flat`.
    """
    model = flat.KnowledgeModel if representation == 'flat' else tree.KnowledgeModel
    schema = _generate(model, title=f'Knowledge Model ({representation})',
                       comment=f'Knowledge model metamodel version {KM_METAMODEL_VERSION}',
                       schema_id=schema_id, mode=mode)
    return _compact(schema) if compact else schema


def template_json_schema(kind: typing.Literal['local', 'bundle'] = 'local', *,
                         schema_id: str | None = None, mode: Mode = 'validation') -> JsonSchema:
    """``template.json`` as maintained with the TDK (``local``) or inside a package (``bundle``)."""
    model = DocumentTemplateMetadata if kind == 'local' else DocumentTemplateBundle
    return _generate(model, title=f'Document Template Descriptor ({kind})',
                     comment='Document template metamodel version '
                             f'{DOCUMENT_TEMPLATE_METAMODEL_VERSION}',
                     schema_id=schema_id, mode=mode)


def document_context_schema(*, schema_id: str | None = None,
                            mode: Mode = 'validation') -> JsonSchema:
    """Document context the backend sends to the document worker."""
    return _generate(DocumentContext, title='Document Context',
                     comment='Document template metamodel version '
                             f'{DOCUMENT_TEMPLATE_METAMODEL_VERSION}',
                     schema_id=schema_id, mode=mode)


def project_events_schema(*, schema_id: str | None = None,
                          mode: Mode = 'validation') -> JsonSchema:
    """A list of project events as the backend sends them."""
    return _generate(list[AnyProjectEvent], title='Project Events', comment=None,
                     schema_id=schema_id, mode=mode)


def _generate(model: typing.Any, *, title: str, comment: str | None, schema_id: str | None,
              mode: Mode) -> JsonSchema:
    with warnings.catch_warnings():
        # recursive discriminated unions (tree questions) keep oneOf but lose the mapping hint
        warnings.filterwarnings('ignore', category=PydanticJsonSchemaWarning,
                                message='.*skipped-discriminator.*')
        generated = pydantic.TypeAdapter(model).json_schema(
            by_alias=True, mode=mode, schema_generator=_Generator)
    body = _inline_definitions(generated)
    for name in body.get('$defs', {}):
        if '__' in name:
            raise SchemaError(f'Ambiguous definition name {name!r}; two models share a name')
    header: JsonSchema = {'$schema': DIALECT}
    if schema_id is not None:
        header['$id'] = schema_id
    header['title'] = title
    if comment is not None:
        header['$comment'] = comment
    body.pop('title', None)
    return {**header, **body}


def _inline_definitions(schema: JsonSchema) -> JsonSchema:
    definitions = schema.get('$defs', {})
    inlined = {name: definition for name, definition in definitions.items()
               if name.startswith(_INLINED_DEFINITIONS)}

    def replace(node: typing.Any) -> typing.Any:
        if isinstance(node, dict):
            ref = node.get('$ref')
            if isinstance(ref, str) and ref.startswith('#/$defs/'):
                name = ref.removeprefix('#/$defs/')
                if name in inlined:
                    return replace(copy.deepcopy(inlined[name]))
            return {key: replace(value) for key, value in node.items()}
        if isinstance(node, list):
            return [replace(item) for item in node]
        return node

    result = replace({key: value for key, value in schema.items() if key != '$defs'})
    remaining = {name: replace(definition) for name, definition in definitions.items()
                 if name not in inlined}
    if remaining:
        result['$defs'] = remaining
    return result


def _compact(schema: JsonSchema) -> JsonSchema:
    def strip(node: typing.Any, *, in_properties: bool = False) -> typing.Any:
        if isinstance(node, dict):
            return {
                key: strip(value, in_properties=key in ('properties', '$defs'))
                for key, value in node.items()
                if in_properties or key not in ('title', 'default', 'discriminator')
            }
        if isinstance(node, list):
            return [strip(item) for item in node]
        return node

    # the schema's own title stays, in place
    return {
        key: value if key == 'title' else strip(value, in_properties=key in ('properties', '$defs'))
        for key, value in schema.items()
    }
