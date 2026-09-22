# dsw-models examples

Small command-line scripts showing typical uses of `dsw-models`. Each one runs with nothing but
the package installed (`pip install dsw-models`) and prints its options with `--help`.

| Script | What it does |
|---|---|
| [`validate_km.py`](validate_km.py) | Loads a `.km` bundle (migrating older ones), compiles its events and reports validation issues; exits with 1 on errors |
| [`create_km.py`](create_km.py) | Builds a small knowledge model with `KnowledgeModelBuilder` and writes it as an importable `.km` bundle |
| [`diff_kms.py`](diff_kms.py) | Prints the events changing one knowledge model into another — two built-in versions, or two packages of a bundle |
| [`generate_schema.py`](generate_schema.py) | Generates a JSON Schema: knowledge model bundle, flat or tree knowledge model, `template.json`, document context, project events |

```bash
python create_km.py -o example.km
python validate_km.py example.km
python diff_kms.py
python diff_kms.py dsw_root_2.8.1.km --from dsw:root:2.7.0
python generate_schema.py km-bundle -o kmp_schema.json
```
