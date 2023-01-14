from .events import _KMEvent, Event

from typing import Optional


class Package:

    def __init__(self, km_id: str, org_id: str, version: str, name: str,
                 metamodel_version: int, description: str, license: str,
                 readme: str, created_at: str, fork_pkg_id: Optional[str],
                 merge_pkg_id: Optional[str], prev_pkg_id: Optional[str]):
        self.km_id = km_id
        self.org_id = org_id
        self.version = version
        self.name = name
        self.metamodel_version = metamodel_version
        self.description = description
        self.license = license
        self.readme = readme
        self.created_at = created_at
        self.fork_pkg_id = fork_pkg_id
        self.merge_pkg_id = merge_pkg_id
        self.prev_pkg_id = prev_pkg_id
        self.events = list()  # type: list[_KMEvent]

    @property
    def id(self):
        return f'{self.org_id}:{self.km_id}:{self.version}'

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'organizationId': self.org_id,
            'kmId': self.km_id,
            'version': self.version,
            'metamodelVersion': self.metamodel_version,
            'name': self.name,
            'description': self.description,
            'license': self.license,
            'readme': self.readme,
            'createdAt': self.created_at,
            'forkOfPackageId': self.fork_pkg_id,
            'mergeCheckpointPackageId': self.merge_pkg_id,
            'previousPackageId': self.prev_pkg_id,
            'events': [e.to_dict() for e in self.events],
        }

    @staticmethod
    def from_dict(data: dict) -> 'Package':
        package = Package(
            org_id=data['organizationId'],
            km_id=data['kmId'],
            version=data['version'],
            metamodel_version=data['metamodelVersion'],
            name=data['name'],
            description=data['description'],
            license=data['license'],
            readme=data['readme'],
            created_at=data['createdAt'],
            fork_pkg_id=data['forkOfPackageId'],
            merge_pkg_id=data['mergeCheckpointPackageId'],
            prev_pkg_id=data['previousPackageId'],
        )
        for event_data in data.get('events', []):
            package.events.append(Event.from_dict(event_data))
        return package


class PackageBundle:

    def __init__(self, km_id: str, org_id: str, version: str, name: str,
                 metamodel_version: int):
        self.km_id = km_id
        self.org_id = org_id
        self.version = version
        self.name = name
        self.metamodel_version = metamodel_version
        self.packages = list()  # type: list[Package]

    @property
    def id(self):
        return f'{self.org_id}:{self.km_id}:{self.version}'

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'organizationId': self.org_id,
            'kmId': self.km_id,
            'version': self.version,
            'metamodelVersion': self.metamodel_version,
            'name': self.name,
            'packages': [pkg.to_dict() for pkg in self.packages],
        }

    @staticmethod
    def from_dict(data: dict) -> 'PackageBundle':
        bundle = PackageBundle(
            org_id=data['organizationId'],
            km_id=data['kmId'],
            version=data['version'],
            metamodel_version=data['metamodelVersion'],
            name=data['name'],
        )
        for package_data in data.get('packages', []):
            bundle.packages.append(Package.from_dict(package_data))
        return bundle
