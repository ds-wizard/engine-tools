"""Knowledge model inputs of `generate-context`: a bundle file, the sample KM, a server package."""
from __future__ import annotations

import gzip
import json
import typing

from dsw.models.knowledge_model.bundle import compile_bundle
from dsw.models.knowledge_model.migrations import migrate_bundle
from dsw.models.knowledge_model.package import KnowledgeModelBundle
from dsw.models.strictness import load
from dsw.models.versions import KM_METAMODEL_VERSION

from .generate import KnowledgeModelInput, input_from_bundle
from .sample_km import SAMPLE_KM_PATH


if typing.TYPE_CHECKING:
    import pathlib


def parse_bundle(data: typing.Any) -> KnowledgeModelBundle:
    """A bundle from parsed JSON, upgraded first when it has an older metamodel version."""
    if isinstance(data, dict) and data.get('metamodelVersion') != KM_METAMODEL_VERSION:
        data = migrate_bundle(data)
    return load(KnowledgeModelBundle, data)


def read_bundle_file(path: pathlib.Path) -> KnowledgeModelBundle:
    """A `.km` file: plain JSON, gzipped when the name ends with `.gz`."""
    if path.suffix == '.gz':
        with gzip.open(path, 'rt', encoding='utf-8') as file:
            return parse_bundle(json.load(file))
    return parse_bundle(json.loads(path.read_text(encoding='utf-8')))


def input_from_bundle_data(bundle: KnowledgeModelBundle, seed: int,
                           package_uuid: str | None = None) -> KnowledgeModelInput:
    return input_from_bundle(bundle, compile_bundle(bundle), package_uuid, seed)


def sample_input(seed: int) -> KnowledgeModelInput:
    return input_from_bundle_data(read_bundle_file(SAMPLE_KM_PATH), seed)
