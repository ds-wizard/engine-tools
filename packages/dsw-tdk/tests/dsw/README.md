# DSW for DSW-TDK integration tests

Create API Key from admin and export as `DSW_API_KEY` before running the tests.

## `test_cmd_get`

- Add `questionnaire-report` (2.16.1) template via import
- Create editor from the `questionnaire-report` (2.17.0) template (use `organization` as org ID)

```
pytest --record-mode=rewrite -s tests/test_cmd_get.py
```

## `test_cmd_list`

- Add `questionnaire-report` template via import
- Create editor from the `questionnaire-report` (increase minor version)
- Create editor `test-template-x` with version `0.1.0`

```
pytest --record-mode=rewrite -s tests/test_cmd_list.py
```

## `test_cmd_put`

- Create published template `test-template-y` with version `0.1.0`

```
pytest --record-mode=rewrite -s tests/test_cmd_put.py
```
