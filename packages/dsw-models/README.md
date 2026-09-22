# Data Stewardship Wizard: Models

[![GitHub release (latest SemVer)](https://img.shields.io/github/v/release/ds-wizard/engine-tools)](https://github.com/ds-wizard/engine-tools/releases)
[![PyPI](https://img.shields.io/pypi/v/dsw-models)](https://pypi.org/project/dsw-models/)
[![LICENSE](https://img.shields.io/github/license/ds-wizard/engine-tools)](LICENSE)
[![CII Best Practices](https://bestpractices.coreinfrastructure.org/projects/4975/badge)](https://bestpractices.coreinfrastructure.org/projects/4975)
[![Python Version](https://img.shields.io/badge/Python-%E2%89%A5%203.12-blue)](https://python.org)

*Models of Data Stewardship Wizard data, their transformations and tooling for scripts*

## Installation

```bash
pip install dsw-models
pip install 'dsw-models[rendering]'  # Markdown helpers of the document context
```

## What is inside

| Module | Purpose |
|---|---|
| `knowledge_model.flat` | Compiled knowledge model (entity maps and UUID lists) |
| `knowledge_model.events` | Knowledge model events |
| `knowledge_model.package` | `.km` bundles and their packages |
| `knowledge_model.tree` | Nested knowledge model for authoring (by hand or by tools) |
| `knowledge_model.graph`, `.visitor` | Read-only navigation and visitors |
| `knowledge_model.compiler`, `.bundle` | Events → knowledge model |
| `knowledge_model.diff`, `.squash` | Knowledge model → events, squashing events |
| `knowledge_model.builder`, `.validation` | Fluent building and semantic validation |
| `knowledge_model.migrations` | Upgrading bundles from older metamodel versions |
| `document_template.metadata`, `.migrations` | `template.json` (local and packaged) |
| `document_context.wire`, `.graph` | Document context and its object model for templates |
| `project.*` | Project events, replies, content, squashing and reports |
| `schemas` | JSON Schemas of the models |

Models use the JSON (camelCase) names of the Data Stewardship Wizard API. They reject unknown
keys unless asked otherwise:

```python
import json

from dsw.models.knowledge_model.package import KnowledgeModelBundle
from dsw.models.strictness import UnknownKeys, load

with open('dsw_root_2.8.1.km') as file:
    bundle = load(KnowledgeModelBundle, json.load(file))            # strict
    # load(KnowledgeModelBundle, data, unknown_keys=UnknownKeys.IGNORE) drops unknown keys

data = bundle.to_json_data()  # JSON-compatible data as the server writes it
```

## Knowledge models

Compile a bundle and navigate the result:

```python
from dsw.models.knowledge_model import graph
from dsw.models.knowledge_model.bundle import compile_bundle

km = compile_bundle(bundle)                   # flat.KnowledgeModel of the bundle's package
km_graph = graph.KnowledgeModel(km)

for chapter in km_graph.chapters:
    for question in chapter.questions:
        print(question.title, [tag.name for tag in question.tags])
```

Every node knows its `parent`, `children`, `ancestors` and resolved references
(`answer.follow_up_questions`, `question.required_phase`, `item_select.list_question` …).
Reverse lookups answer questions such as "which questions use this integration"
(`integration.questions`).

Walk the knowledge model with a visitor; the most specific `visit_<kind>` method wins:

```python
from dsw.models.knowledge_model.visitor import SKIP, KnowledgeModelVisitor, walk


class QuestionsWithoutReferences(KnowledgeModelVisitor):

    def __init__(self):
        self.found = []

    def visit_question(self, question):
        if not question.references:
            self.found.append(question)

    def visit_answer(self, answer):
        if answer.label == 'No':
            return SKIP  # do not descend into follow-up questions


visitor = QuestionsWithoutReferences()
walk(km_graph, visitor)
```

### Building and changing knowledge models

```python
from dsw.models.knowledge_model.builder import KnowledgeModelBuilder

builder = KnowledgeModelBuilder()
phase = builder.phase('Before submitting the proposal')
findability = builder.metric('Findability', abbreviation='F')
chapter = builder.chapter('Data description')
question = chapter.options_question('Will you reuse existing data?', required_phase=phase)
question.answer('Yes', metric_measures=[(findability, 1.0, 1.0)]).value_question('Which data?')
question.answer('No')

km = builder.build()
bundle = builder.to_bundle(organization_id='example', km_id='data', version='1.0.0', name='Data')
```

To change an existing knowledge model, edit a copy of the flat model and let `diff` produce the
events (entities are matched by UUID; the result is verified by replaying it):

```python
from dsw.models.knowledge_model.diff import decompile, diff
from dsw.models.knowledge_model.squash import squash

changed = km.model_copy(deep=True)
changed.entities.chapters[changed.chapter_uuids[0]].title = 'Data'
events = squash(diff(km, changed))   # or decompile(changed) for a new package
```

`validation.validate(km)` reports errors, warnings and infos with a location and a hint, e.g.
`[warning] too-few-answers at Chapter 'Data' › OptionsQuestion 'Reuse?': …`.

`convert.flat_to_tree()` and `convert.tree_to_flat()` convert to and from the nested model;
`schemas.knowledge_model_schema('tree', compact=True)` gives a smaller schema without titles,
defaults and discriminator mappings.

### Older bundles

```python
from dsw.models.knowledge_model.migrations import migrate_bundle

bundle = load(KnowledgeModelBundle, migrate_bundle(old_data), unknown_keys=UnknownKeys.IGNORE)
```

## Projects

```python
from dsw.models.project.content import compile_project_events
from dsw.models.project.report import generate_report
from dsw.models.project.walker import walk_replies

content = compile_project_events(events)                  # replies, labels, phase
report = generate_report(km, content.replies, content.phase_uuid)
for item in walk_replies(km_graph, content.replies):     # questions as the questionnaire shows them
    print(item.path, item.question.title, item.reply)
```

## Document templates and contexts

```python
from dsw.models.document_template.metadata import DocumentTemplateMetadata
from dsw.models.document_template.migrations import migrate_template_json

result = migrate_template_json(old_template_json)   # best effort, with warnings
metadata = load(DocumentTemplateMetadata, result.data)
```

`document_context.wire.DocumentContext` validates the document context sent to the document
worker; `document_context.graph.DocumentContext` is the object model templates get from
`ctx|to_context_obj`.

## JSON Schemas

```python
from dsw.models import schemas

schema = schemas.knowledge_model_bundle_schema(schema_id='https://example.org/km-bundle.json')
```

Available: `knowledge_model_bundle_schema`, `knowledge_model_schema`, `template_json_schema`,
`document_context_schema` and `project_events_schema` (JSON Schema 2020-12).

## Examples

Runnable scripts — validating a `.km` bundle, building one, diffing two knowledge models and
generating JSON Schemas — are in [`examples/`](examples/).

## License

This project is licensed under the Apache License v2.0 - see the
[LICENSE](LICENSE) file for more details.
