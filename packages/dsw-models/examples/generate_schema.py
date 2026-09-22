"""Generate a JSON Schema (2020-12) from the dsw-models models.

    python generate_schema.py km-bundle > kmp_schema.json
    python generate_schema.py km-tree --compact -o km_tree.json
    python generate_schema.py template-json --id https://example.org/template.json --mode serialization

Kinds: km-bundle, km-flat, km-tree, template-json, template-bundle, document-context,
project-events.
"""
import argparse
import json
import pathlib
import sys

from dsw.models import schemas


GENERATORS = {
    'km-bundle': lambda **kw: schemas.knowledge_model_bundle_schema(**kw),
    'km-flat': lambda **kw: schemas.knowledge_model_schema('flat', **kw),
    'km-tree': lambda **kw: schemas.knowledge_model_schema('tree', **kw),
    'template-json': lambda **kw: schemas.template_json_schema('local', **kw),
    'template-bundle': lambda **kw: schemas.template_json_schema('bundle', **kw),
    'document-context': lambda **kw: schemas.document_context_schema(**kw),
    'project-events': lambda **kw: schemas.project_events_schema(**kw),
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('kind', choices=GENERATORS)
    parser.add_argument('-o', '--output', type=pathlib.Path, help='output file (default: stdout)')
    parser.add_argument('--id', dest='schema_id', help='$id of the schema')
    parser.add_argument('--mode', choices=('validation', 'serialization'), default='validation',
                        help='what the models accept (default) or what they produce')
    parser.add_argument('--compact', action='store_true',
                        help='leave out titles, defaults and discriminator mappings '
                             '(km-flat and km-tree only)')
    args = parser.parse_args()

    kwargs = {'schema_id': args.schema_id, 'mode': args.mode}
    if args.compact:
        if args.kind not in ('km-flat', 'km-tree'):
            parser.error('--compact is available for km-flat and km-tree only')
        kwargs['compact'] = True
    schema = GENERATORS[args.kind](**kwargs)

    text = json.dumps(schema, indent=2, ensure_ascii=False) + '\n'
    if args.output is None:
        sys.stdout.write(text)
    else:
        args.output.write_text(text, encoding='utf-8')
        print(f'Wrote {args.output} ({len(schema.get("$defs", {}))} definitions)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
