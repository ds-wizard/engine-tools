# Document Context

This document describes the document context (metamodel **19.0**) that the document worker provides to Jinja templates. The raw JSON is available as `ctx`; the object model described here is created like this:

```jinja
{%- set x = ctx|to_context_obj -%}
```

* All data types are using Python, e.g., `str` is textual string, `Optional[str]` is a string or `None`, `list[str]` is a list of strings.
* We use `snake_case` for naming of attributes and variables, `PascalCase` is used for class names.
* `datetime` is the standard [`datetime.datetime`](https://docs.python.org/3/library/datetime.html#datetime-objects).
* You can investigate the [`graph`](../../dsw-models/dsw/models/document_context/graph.py) module of `dsw-models`; however, constructs that are not documented here may change in any version without an explicit notice.
* A context comes either from a **project** or from a **knowledge model editor** (its preview). Exactly one of `project` and `km_editor` is set, so guard with `{% if x.project %}` / `{% if x.km_editor %}`. The content (replies, phase, files, report) is in `questionnaire` in both cases.

## Migrating from 18.x

| 18.x | 19.0 |
|---|---|
| `x.e` | `x.km.entities` (`x.km.e` stays) |
| `x.cfg` | `x.config` |
| `x.pkg` | `x.km_package` |
| `x.doc` | `x.document` |
| `x.org`, `x.organization` | removed; `x.workspace` or `x.config.app_title` are the closest |
| `x.replies` | `x.questionnaire.replies` |
| `x.current_phase` | `x.questionnaire.phase` |
| `x.report` | `x.questionnaire.report` (without `uuid`, `created_at`, `updated_at`) |
| `x.users`, `x.groups` | `x.project.users`, `x.project.groups` |
| `x.project.replies`, `phase`, `phase_uuid`, `version`, `versions`, `files`, `language`, `todos` | `x.questionnaire.…` |
| `x.pkg.id` (`org:km:version`) | `x.km_package.id` — the id alone, **without the version** |
| `x.pkg.org_id`, `organization_id`, `km_id`, `versions` | removed |
| `x.doc.document_template_uuid`, `format_uuid` | `x.document.document_template.uuid`, `x.document.format.uuid` |
| `x.config.app_title_short`, `illustrations_color` | removed |

## Diagram

The class diagram predates metamodel 19.0; the entity list below is authoritative: [SVG](./diagrams/dsw-document-context.svg).

## Entities

Here is an interlinked description of each entity and its attributes and links. There are also *aliases* that are convenient shorthands to make template more concise.

### DocumentContext

* `hash` (`str`) - `sha256:…` of the context content; the same data always gives the same hash
* `workspace` ([`Workspace`](#workspace))
* `project` (`Optional[`[`Project`](#project)`]`) - set for a project, `None` for a KM editor
* `km_editor` (`Optional[`[`KnowledgeModelEditor`](#knowledgemodeleditor)`]`) - set for a KM editor, `None` for a project
* `questionnaire` ([`Questionnaire`](#questionnaire))
* `km` ([`KnowledgeModel`](#knowledgemodel))
* `km_package` (`Optional[`[`KnowledgeModelPackage`](#knowledgemodelpackage)`]`) - `None` for a KM editor without a previous package
* `document` (`Optional[`[`Document`](#document)`]`) - always set when the document worker renders
* `config` ([`ContextConfig`](#contextconfig))

### Workspace

* `uuid` (`str`)
* `name` (`str`)
* `description` (`Optional[str]`)

### ContextConfig

The effective look and feel of the workspace, and values of the document worker deployment.

* `client_url` (`str`) - base URL of the client app
* `app_title` (`str`)
* `primary_color` ([`Color`](#color))
* `logo_url` (`str`)
* `service_name`, `service_name_short`, `service_url`, `service_domain_name` (`str`) - set by the document worker

### Color

* `red`, `green`, `blue` (`int`)
* `hex` (`str`) - e.g. `#0033aa`
* `luminance` (`float`)
* `is_dark`, `is_light` (`bool`)
* `contrast_color` ([`Color`](#color)) - white when its contrast ratio with this color is above 3, otherwise black

The string value of a color is its `hex`.

### Document

* `uuid` (`str`)
* `name` (`str`)
* `document_template` ([`DocumentDocumentTemplate`](#documentdocumenttemplate))
* `format` ([`DocumentFormat`](#documentformat))
* `language` (`Optional[str]`) - language requested for the document, `None` when none was selected
* `locale` (`Optional[`[`DocumentTemplateLocale`](#documenttemplatelocale)`]`) - locale used for the translations, see [Translations](./Translations.md)
* `preview` (`bool`) - a temporary document (preview), not a stored one
* `event_uuid` (`Optional[str]`) - the project event the document was generated at
* `created_by` (`Optional[`[`User`](#user)`]`)
* `created_at` (`datetime`)

### DocumentDocumentTemplate

* `uuid` (`str`)
* `id` (`str`)
* `version` (`str`)
* `workspace_uuid` (`Optional[str]`) - `None` for a template shared by the whole organization

### DocumentFormat

* `uuid` (`str`)
* `name` (`str`)

### DocumentTemplateLocale

* `uuid` (`str`)
* `name` (`str`)
* `code` (`str`) - language code from the `Language` header of the locale PO file
* `created_at` (`datetime`)
* `updated_at` (`datetime`)

### Project

Metadata of the project; its content is in [`Questionnaire`](#questionnaire).

* `uuid` (`str`)
* `name` (`str`)
* `description` (`str`)
* `created_by` (`Optional[`[`User`](#user)`]`)
* `created_at` (`datetime`)
* `updated_at` (`datetime`)
* `visibility` (`str`) - e.g. `PrivateProjectVisibility`
* `sharing` (`str`) - e.g. `RestrictedProjectSharing`
* `is_template` (`bool`)
* `knowledge_model_package_uuid` (`str`)
* `selected_question_tag_uuids` (`list[str]`)
* `project_tags` (`list[str]`)
* `document_template_uuid` (`Optional[str]`) - default template of the project
* `format_uuid` (`Optional[str]`) - default format of the project
* `users` (`list[`[`UserPermission`](#userpermission)`]`) - sorted by user UUID
* `groups` (`list[`[`UserGroupPermission`](#usergrouppermission)`]`) - sorted by group UUID

### KnowledgeModelEditor

* `uuid`, `name`, `description` (`str`)
* `created_by` (`Optional[`[`User`](#user)`]`)
* `created_at`, `updated_at` (`datetime`)
* `id` (`str`), `version` (`str`) - of the knowledge model being edited
* `license`, `readme` (`str`)
* `previous_package_uuid`, `previous_package_id`, `previous_package_version` (`Optional[str]`)
* `knowledge_model_metamodel_version` (`int`)

### Questionnaire

* `replies` ([`RepliesContainer`](#repliescontainer))
* `phase` ([`Phase`](#phase)) - the current phase; a phase titled `never` when none is set
* `phase_uuid` (`Optional[str]`)
* `version` (`Optional[`[`QuestionnaireVersion`](#questionnaireversion)`]`) - the version the document was generated at
* `versions` (`list[`[`QuestionnaireVersion`](#questionnaireversion)`]`) - sorted by creation
* `files` (`dict[str,`[`ProjectFile`](#projectfile)`]`) - by UUID
* `labels` (`dict[str, list[str]]`) - label UUIDs by reply path
* `todos` (`list[str]`) - reply paths marked as TODO
* `report` ([`Report`](#report))
* `language` (`Optional[str]`) - of the project, or of the editor for a KM editor

### QuestionnaireVersion

* `uuid` (`str`)
* `event_uuid` (`str`)
* `name` (`str`)
* `description` (`Optional[str]`)
* `created_by` ([`SimpleAuthor`](#simpleauthor))
* `created_at` (`datetime`)
* `updated_at` (`datetime`)

### ProjectFile

* `uuid` (`str`)
* `name` (`str`)
* `size` (`int`) - in bytes
* `content_type` (`str`)
* `reply` (`Optional[FileReply]`)
* `download_url` (`str`)

### KnowledgeModelPackage

* `uuid` (`str`)
* `id` (`str`) - the id alone, e.g. `dsw.root`; use `x.km_package.id ~ ':' ~ x.km_package.version` for the full reference
* `version` (`str`)
* `name` (`str`)
* `description` (`str`)
* `language` (`str`)
* `created_at` (`datetime`)
* `workspace_uuid` (`Optional[str]`) - `None` for a package shared by the whole organization

### User

* `uuid` (`str`)
* `first_name` (`str`)
* `last_name` (`str`)
* `email` (`str`)
* `image_url` (`Optional[str]`)
* `affiliation` (`Optional[str]`)
* `created_at` (`datetime`)
* `updated_at` (`datetime`)

### UserPermission

* `user` ([`User`](#user))
* `permissions` (`list[str]`) - of `VIEW`, `COMMENT`, `EDIT`, `ADMIN`

Aliases: `is_viewer`, `is_commenter`, `is_editor`, `is_owner` (`bool`)

### UserGroupPermission

* `group` ([`UserGroup`](#usergroup))
* `permissions` (`list[str]`) - of `VIEW`, `COMMENT`, `EDIT`, `ADMIN`

Aliases: `is_viewer`, `is_commenter`, `is_editor`, `is_owner` (`bool`)

### UserGroup

* `uuid`, `name` (`str`)
* `description` (`Optional[str]`)
* `private` (`bool`)
* `members` (`list[`[`UserGroupMember`](#usergroupmember)`]`)
* `created_at`, `updated_at` (`datetime`)

### UserGroupMember

* `uuid`, `first_name`, `last_name`, `gravatar_hash` (`str`)
* `image_url` (`Optional[str]`)
* `membership_type` (`str`) - `owner` or `member`

### SimpleAuthor

* `uuid` (`str`)
* `first_name` (`str`)
* `last_name` (`str`)
* `image_url` (`Optional[str]`)
* `gravatar_hash` (`Optional[str]`)

### Report

* `total_report` ([`ReportItem`](#reportitem))
* `chapter_reports` (`list[`[`ReportItem`](#reportitem)`]`)

#### ReportItem

* `indications` (`list[`[`ReportIndication`](#reportindication)`]`)
* `metrics` (`list[`[`ReportMetric`](#reportmetric)`]`)
* `chapter` (`Optional[`[`Chapter`](#chapter)`]`) - set if it is a chapter report

#### ReportIndication

* `indication_type` (`str`) - one of: `PhasesAnsweredIndication`, `AnsweredIndication` (use alias)
* `answered` (`int`) - number of answered questions
* `unanswered` (`int`) - number of unanswered questions

Aliases:

* `total` (`int`) - `answered` + `unanswered`
* `percentage` (`float`) - `answered` / `total` (handles zero division, number between `0.0` and `1.0`)
* `is_for_phase` (`bool`) - if it is a phase-related indication
* `is_overall` (`bool`) - if it is an overall indication (not phase-related)

#### ReportMetric

* `measure` (`Optional[float]`) - number between `0.0` and `1.0`, `None` when nothing answered contributes to it
* `metric` ([`Metric`](#metric))

### KnowledgeModel

* `uuid` (`str`)
* `annotations` (`dict[str,str]`)
* `entities` ([`KnowledgeModelEntities`](#knowledgemodelentities))
* `chapters` (`list[`[`Chapter`](#chapter)`]`)
* `integrations` (`list[`[`Integration`](#integration)`]`)
* `metrics` (`list[`[`Metric`](#metric)`]`)
* `phases` (`list[`[`Phase`](#phase)`]`)
* `tags` (`list[`[`Tag`](#tag)`]`)

Aliases:

* `e` ([`KnowledgeModelEntities`](#knowledgemodelentities)) - same as `entities`
* `a` (`dict[str,str]`) - same as `annotations`

:bulb: Equality of all KM entities is being done using the `uuid` comparison under the hood.

:bulb: All KM entities that have `annotations` have also the `a` alias.

#### KnowledgeModelEntities

Container holding all types of Knowledge Model entities within UUID-key dictionaries:

* `answers` (`dict[str,`[`Answer`](#answer)`]`)
* `chapter` (`dict[str,`[`Chapter`](#chapter)`]`)
* `choices` (`dict[str,`[`Choice`](#choice)`]`)
* `experts` (`dict[str,`[`Expert`](#expert)`]`)
* `integrations` (`dict[str,`[`Integration`](#integration)`]`)
* `metrics` (`dict[str,`[`Metric`](#metric)`]`)
* `phases` (`dict[str,`[`Phase`](#phase)`]`)
* `questions` (`dict[str,`[`Question`](#question)`]`)
* `references` (`dict[str,`[`Reference`](#reference)`]`)
* `tags` (`dict[str,`[`Tag`](#tag)`]`)

#### Chapter

* `uuid` (`str`)
* `title` (`str`)
* `text` (`Optional[str]`) - possibly Markdown text
* `questions` (`list[`[`Question`](#question)`]`)
* `reports` (`list[`[`ReportItem`](#reportitem)`]`)
* `annotations` (`dict[str,str]`)

#### Question

Superclass with common attributes for all types of questions. You always get a more specific one and never just a `Question`.

* `uuid` (`str`)
* `type` (`str`)
* `title` (`str`)
* `text` (`Optional[str]`)
* `required_phase` (`Optional[`[`Phase`](#phase)`]`)
* `is_required` (`bool`) - if the question is required in the current phase
* `replies` (`dict[str,`[`Reply`](#reply)`]`) - path-key dictionary of replies to the question
* `experts` (`list[`[`Expert`](#expert)`]`)
* `references` (`list[`[`Reference`](#reference)`]`)
* `tags` (`list[`[`Tag`](#tag)`]`)
* `parent` (`Union[`[`Chapter`](#chapter)`,`[`ListQuestion`](#listquestion)`,`[`Answer`](#answer)`]`)
* `annotations` (`dict[str,str]`)

Aliases:

* `url_references` (`list[`[`URLReference`](#urlreference)`]`)
* `resource_page_references` (`list[`[`ResourcePageReference`](#resourcepagereference)`]`)

:bulb: Parent of a question can be of multiple kinds, you may use the `of_type` test to check what it is if needed.

##### ValueQuestion

* `value_type` (`str`) - type of value, use alias

Aliases:

* `is_string` (`bool`)
* `is_text` (`bool`)
* `is_number` (`bool`)
* `is_date` (`bool`)

##### IntegrationQuestion

* `integration` ([`Integration`](#integration))
* `props` (`dict[str,str]`)

##### OptionsQuestion

* `answers` (`list[`[`Answer`](#answer)`]`)

##### MultiChoiceQuestion

* `choices` (`list[`[`Choice`](#choice)`]`)

##### ListQuestion

* `followups` (`list[`[`Question`](#question)`]`)

#### Answer

* `uuid` (`str`)
* `label` (`str`)
* `advice` (`Optional[str]`) - possibly Markdown text
* `metric_measures` (`list[`[`MetricMeasure`](#metricmeasure)`]`)
* `followups` (`list[`[`Question`](#question)`]`)
* `parent` ([`OptionsQuestion`](#optionsquestion))
* `annotations` (`dict[str,str]`)

##### MetricMeasure

Indication of how an answer affects a certain metric.

* `measure` (`float`) - value between `0.0` and `1.0` (inclusive)
* `weight` (`float`) - value between `0.0` and `1.0` (inclusive)
* `metric` ([`Metric`](#metric))

#### Choice

* `uuid` (`str`)
* `label` (`str`)
* `parent` ([`MultiChoiceQuestion`](#multichoicequestion))
* `annotations` (`dict[str,str]`)

#### Expert

* `uuid` (`str`)
* `name` (`str`)
* `email` (`str`)
* `annotations` (`dict[str,str]`)

#### Reference

As for the [`Question`](#question) class, `Reference` is also a superclass and you will always get an object of its subclass.

* `uuid` (`str`)
* `type` (`str`)
* `annotations` (`dict[str,str]`)

##### URLReference

* `label` (`str`)
* `url` (`str`)

##### ResourcePageReference

* `short_uuid` (`str`)
* `url` (`str`) - URL composed using `client_url` from [`ContextConfig`](#contextconfig)

#### Metric

* `uuid` (`str`)
* `title` (`str`)
* `abbreviation` (`str`)
* `description` (`Optional[str]`) - possibly Markdown text
* `annotations` (`dict[str,str]`)

#### Phase

* `uuid` (`str`)
* `title` (`str`)
* `description` (`Optional[str]`) - possibly Markdown text
* `order` (`int`) - order of the phase within the KM
* `annotations` (`dict[str,str]`)

#### Integration

* `uuid` (`str`)
* `id` (`str`)
* `name` (`str`)
* `item_url` (`str`)
* `logo` (`str`)
* `props` (`dict[str,str]`)
* `rq_method` (`str`)
* `rq_url` (`str`)
* `rq_headers` (`dict[str,str]`)
* `rq_body` (`str`)
* `rs_list_field` (`str`)
* `rs_item_id` (`str`)
* `rs_item_template` (`str`)
* `annotations` (`dict[str,str]`)

Operations:

* `item(item_id: str) -> str` - URL of an item identified by string ID

#### Tag

* `uuid` (`str`)
* `name` (`str`)
* `description` (`Optional[str]`) - possibly Markdown text
* `color` (`str`)
* `annotations` (`dict[str,str]`)

### RepliesContainer

Wrapper around a path-key dictionary of replies.

* `replies` (`dict[str,`[`Reply`](#reply)`]`)

Operations:

* `X[path: str]` (`Optional[`[`Reply`](#reply)`]`) - you can get a reply using square brackets
* `len(X)` (`int`) - number of replies in the container
* `get(path: str) -> Optional[`[`Reply`](#reply)`]`
* `iterate_by_prefix(path_prefix: str) -> Iterable[`[`Reply`](#reply)`]` - *O(n)* iteration with filter
* `iterate_by_suffix(path_suffix: str) -> Iterable[`[`Reply`](#reply)`]` - *O(n)* iteration with filter
* `values() -> Iterable[`[`Reply`](#reply)`]`
* `keys() -> Iterable[str]`
* `items() -> ItemsView[str,`[`Reply`](#reply)`]`

### Reply

Superclass with common attributes for all types of replies. You always get a more specific one and never just a `Reply`.

* `path` (`str`)
* `fragments` (`list[str]`) - UUIDs of the path (starting with chapter)
* `type` (`str`)
* `created_at` (`datetime`)
* `created_by` ([`SimpleAuthor`](#simpleauthor))
* `question` ([`Question`](#question)) - you can assume more specific type of `Question` based on a type of `Reply`

#### AnswerReply

* `answer` ([`Answer`](#answer)) - selected answer as the option

Aliases:

* `value` (`str`) - UUID of the answer (`answer.uuid`)

:bulb: `question` is always [`OptionsQuestion`](#optionsquestion)

#### MultiChoiceReply

* `choices` (`list[`[`Choice`](#choice)`]`) - selected answer as the option

Aliases:

* `value` (`list[str]`) - list of UUIDs of the choices

:bulb: `question` is always [`OptionsQuestion`](#optionsquestion)

:bulb: You can iterate directly over reply object (`for choice in reply`)

#### StringReply

* `value` (`str`)

Aliases:

* `as_number` (`Optional[float]`) - tries to cast the value to a number
* `as_datetime` (`Optional[datetime]`) - tries to cast the value to a timestamp

:bulb: `question` is always [`ValueQuestion`](#valuequestion)

#### ItemListReply

* `items` (`list[str]`) - list of item UUIDs (used in reply paths)

Aliases:

* `value` (`list[str]`) - same as `items`

:bulb: `question` is always [`ListQuestion`](#listquestion)

:bulb: You can iterate directly over reply object (`for item in reply`)

#### IntegrationReply

* `value` (`str`)
* `item_id` (`item_id`) - ID of item if selected using [`Integration`](#integration)

Aliases:

* `id` (`str`) - same as `item_id`
* `is_plain` (`bool`) - entered by user ignoring the integration
* `is_integration` (`bool`) - selected by user using the integration
* `url` (`Optional[str]`) - item URL based [`Integration`](#integration) if selected from it

## Examples

*TBD*

## Important Notes

* The variable `ctx` is the raw JSON document context; its shape is the `DocumentContext` model in [`dsw-models`](../../dsw-models/dsw/models/document_context/wire.py).
* If you think that something useful is missing in the context or its documentation, please let us know.

This document has been last revised for **document context metamodel 19.0**.
