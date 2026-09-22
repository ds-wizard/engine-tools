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
    package_id: str | None = None,
) -> list[KnowledgeModelBundlePackage]:
    """Packages from the first one to ``package_id`` (default: the bundle's), oldest first."""
    packages = {package.id: package for package in bundle.packages}
    current = packages.get(package_id or bundle.id)
    if current is None:
        raise PackageChainError(f'Package {package_id or bundle.id} is not in the bundle')
    chain = [current]
    while current.previous_package_id is not None:
        previous = packages.get(current.previous_package_id)
        if previous is None:
            raise PackageChainError(
                f'Package {current.id} follows {current.previous_package_id}, '
                'which is not in the bundle')
        if previous in chain:
            raise PackageChainError(f'Packages form a cycle at {previous.id}')
        chain.append(previous)
        current = previous
    chain.reverse()
    return chain


def events_of_chain(bundle: KnowledgeModelBundle, package_id: str | None = None) -> list[Event]:
    return [event for package in package_chain(bundle, package_id) for event in package.events]


def compile_bundle(
    bundle: KnowledgeModelBundle,
    package_id: str | None = None,
    *,
    on_ignored: OnIgnored | None = None,
) -> flat.KnowledgeModel:
    """Compile the knowledge model of ``package_id`` (default: the bundle's package)."""
    return compile_events(events_of_chain(bundle, package_id), on_ignored=on_ignored)
