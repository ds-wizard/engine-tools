"""Load a knowledge model bundle (``.km``), compile its events and validate the result.

    python validate_km.py dsw_root_2.8.1.km
    python validate_km.py bundle.km --package example:my-km:1.0.0 --lenient --verbose

Bundles of older metamodel versions are migrated first. The exit status is 1 when the knowledge
model has errors, so the script can guard a CI pipeline.
"""
import argparse
import gzip
import json
import pathlib
import sys

from dsw.models.knowledge_model import graph
from dsw.models.knowledge_model.bundle import compile_bundle
from dsw.models.knowledge_model.migrations import migrate_bundle
from dsw.models.knowledge_model.package import KnowledgeModelBundle
from dsw.models.knowledge_model.validation import validate
from dsw.models.strictness import UnknownKeys, load
from dsw.models.versions import KM_METAMODEL_VERSION


def read_json(path: pathlib.Path):
    opener = gzip.open if path.suffix == '.gz' else open
    with opener(path, 'rt', encoding='utf-8') as file:
        return json.load(file)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('bundle', type=pathlib.Path, help='.km file (optionally gzipped)')
    parser.add_argument('--package', help='package ID to compile (default: the bundle one)')
    parser.add_argument('--lenient', action='store_true', help='drop unknown keys')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='list ignored events and info-level issues too')
    args = parser.parse_args()

    data = read_json(args.bundle)
    version = data.get('metamodelVersion')
    if version != KM_METAMODEL_VERSION:
        print(f'Migrating from metamodel version {version} to {KM_METAMODEL_VERSION}')
        data = migrate_bundle(data)

    unknown_keys = UnknownKeys.IGNORE if args.lenient else UnknownKeys.FORBID
    bundle = load(KnowledgeModelBundle, data, unknown_keys=unknown_keys)
    events = sum(len(package.events) for package in bundle.packages)
    print(f'{bundle.id}: {len(bundle.packages)} package(s), {events} event(s)')

    ignored = []
    km = compile_bundle(bundle, args.package,
                        on_ignored=lambda event, reason: ignored.append((event, reason)))
    km_graph = graph.KnowledgeModel(km)
    print(f'Compiled: {len(km_graph.chapters)} chapter(s), {len(km_graph.questions)} '
          f'question(s), {len(km_graph.answers)} answer(s)')
    if ignored:
        print(f'{len(ignored)} event(s) ignored while compiling, as the server does')
    if args.verbose:
        for event, reason in ignored:
            print(f'  {event.content.event_type} {event.entity_uuid}: {reason}')

    issues = validate(km_graph)
    for issue in issues:
        if args.verbose or issue.severity != 'info':
            print(issue)
    counts = {severity: sum(issue.severity == severity for issue in issues)
              for severity in ('error', 'warning', 'info')}
    print(', '.join(f'{count} {severity}(s)' for severity, count in counts.items()))
    return 1 if counts['error'] else 0


if __name__ == '__main__':
    sys.exit(main())
