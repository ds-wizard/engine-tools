"""Print the events that change one knowledge model into another.

    python diff_kms.py                                        # two small built-in versions
    python diff_kms.py bundle.km --from dsw:root:2.7.0        # a package vs the bundle's one
    python diff_kms.py bundle.km --from dsw:root:2.7.0 --to dsw:root:2.8.0 --json

Entities are matched by UUID, so both knowledge models must descend from the same one.
"""
import argparse
import gzip
import json
import pathlib
import sys
import uuid

from dsw.models.common import BaseModel
from dsw.models.knowledge_model import flat, graph
from dsw.models.knowledge_model.builder import KnowledgeModelBuilder
from dsw.models.knowledge_model.bundle import compile_bundle
from dsw.models.knowledge_model.convert import prune_unreachable
from dsw.models.knowledge_model.diff import diff
from dsw.models.knowledge_model.events import EditEventField, Event
from dsw.models.knowledge_model.package import KnowledgeModelBundle
from dsw.models.knowledge_model.squash import squash
from dsw.models.knowledge_model.validation import location
from dsw.models.strictness import UnknownKeys, load


def built_in_versions() -> tuple[flat.KnowledgeModel, flat.KnowledgeModel]:
    """Version 1, then version 2 made by continuing to work with the same builder."""
    builder = KnowledgeModelBuilder()
    chapter = builder.chapter('Data description')
    reuse = chapter.options_question('Will you reuse existing data?')
    reuse.answer('Yes').value_question('Which data?')
    maybe = reuse.answer('Maybe')
    reuse.answer('No')
    builder.chapter('Storage').value_question('Where will you store the data?')
    old = builder.build()

    chapter.entity.title = 'Data'                               # edit
    reuse.entity.text = 'Existing data saves time and money.'   # edit
    reuse.answer('Not decided yet')                             # add
    new = builder.build()
    question = new.entities.questions[reuse.uuid]               # delete
    question.answer_uuids.remove(maybe.uuid)
    del new.entities.answers[maybe.uuid]
    new.chapter_uuids.reverse()                                 # reorder
    return old, new


def bundle_versions(path: pathlib.Path, old_id: str,
                    new_id: str | None) -> tuple[flat.KnowledgeModel, flat.KnowledgeModel]:
    opener = gzip.open if path.suffix == '.gz' else open
    with opener(path, 'rt', encoding='utf-8') as file:
        bundle = load(KnowledgeModelBundle, json.load(file), unknown_keys=UnknownKeys.IGNORE)
    # compiled knowledge models keep entities orphaned by deletions, as the server does; they
    # are not part of either version, so leave them out rather than diff them away
    return (prune_unreachable(compile_bundle(bundle, old_id)),
            prune_unreachable(compile_bundle(bundle, new_id)))


def changes(event: Event) -> dict[str, object]:
    """Fields an event sets: all of an add event, the changed ones of an edit event."""
    result = {}
    for name in type(event.content).model_fields:
        if name in ('event_type', 'entity_type', 'question_type', 'reference_type',
                    'integration_type'):
            continue
        value = getattr(event.content, name)
        if isinstance(value, EditEventField):
            if value.changed:
                result[name] = value.value
        elif value not in (None, [], {}):
            result[name] = value
    return result


def show(value: object, graphs: tuple[graph.KnowledgeModel, ...], limit: int = 70) -> str:
    """Short JSON-like text of a value; UUIDs of entities are shown as their names."""
    def name(item: object) -> object:
        if isinstance(item, uuid.UUID):
            node = next((g.get(item) for g in graphs if item in g), None)
            if node is not None:
                return next((getattr(node, attr) for attr in ('title', 'label', 'name', 'url')
                             if isinstance(getattr(node, attr, None), str)), str(item))
            return str(item)
        return item.to_json_data() if isinstance(item, BaseModel) else item

    value = [name(item) for item in value] if isinstance(value, list) else name(value)
    text = json.dumps(value, default=str, ensure_ascii=False)
    return text if len(text) <= limit else f'{text[:limit - 1]}…'


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('bundle', nargs='?', type=pathlib.Path, help='.km file with both versions')
    parser.add_argument('--from', dest='old', help='package ID of the old version')
    parser.add_argument('--to', dest='new', help='package ID of the new version (default: bundle)')
    parser.add_argument('--no-squash', action='store_true', help='keep the raw diff events')
    parser.add_argument('--json', action='store_true', help='print the events as JSON')
    args = parser.parse_args()

    if args.bundle is None:
        old, new = built_in_versions()
    elif args.old is None:
        parser.error('--from is required with a bundle')
    else:
        old, new = bundle_versions(args.bundle, args.old, args.new)

    events = diff(old, new)
    if not args.no_squash:
        events = squash(events)
    if args.json:
        print(json.dumps([event.to_json_data() for event in events], indent=2))
        return 0

    graphs = (graph.KnowledgeModel(new), graph.KnowledgeModel(old))
    for event in events:
        node = next((g.get(event.entity_uuid) for g in graphs if event.entity_uuid in g), None)
        print(f'{event.content.event_type:<28} {location(node)}')
        for name, value in changes(event).items():
            print(f'    {name}: {show(value, graphs)}')
    print(f'{len(events)} event(s)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
