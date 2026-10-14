"""Package chains of a knowledge model bundle."""
from __future__ import annotations

import typing

from ..errors import ModelsError
from .compiler import OnIgnored, compile_events


if typing.TYPE_CHECKING:
    from . import flat
    from .events import Event
    from .package import KnowledgeModelBundle, KnowledgeModelBundlePackage


class PackageChainError(ModelsError):
    """The packages do not form a chain ending with the requested package."""


def package_chain(
    bundle: KnowledgeModelBundle,
    reference: str | None = None,
) -> list[KnowledgeModelBundlePackage]:
    """Packages from the first one to ``reference`` (default: the bundle's), oldest first.

    ``reference`` is ``<id>:<version>``, see :mod:`dsw.models.coordinate`.
    """
    packages = {package.reference: package for package in bundle.packages}
    reference = reference or bundle.reference
    current = packages.get(reference)
    if current is None:
        raise PackageChainError(f'Package {reference} is not in the bundle')
    chain = [current]
    while (previous_reference := current.previous_package_reference) is not None:
        previous = packages.get(previous_reference)
        if previous is None:
            raise PackageChainError(
                f'Package {current.reference} follows {previous_reference}, '
                'which is not in the bundle')
        if previous in chain:
            raise PackageChainError(f'Packages form a cycle at {previous.reference}')
        chain.append(previous)
        current = previous
    chain.reverse()
    return chain


def events_of_chain(bundle: KnowledgeModelBundle, reference: str | None = None) -> list[Event]:
    return [event for package in package_chain(bundle, reference) for event in package.events]


def compile_bundle(
    bundle: KnowledgeModelBundle,
    reference: str | None = None,
    *,
    on_ignored: OnIgnored | None = None,
) -> flat.KnowledgeModel:
    """Compile the knowledge model of ``reference`` (default: the bundle's package)."""
    return compile_events(events_of_chain(bundle, reference), on_ignored=on_ignored)
